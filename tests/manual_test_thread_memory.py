import os
import unittest
from uuid import uuid4
from unittest.mock import patch

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from langchain_core.messages import AIMessage

from app import create_app
import agent.nodes.workflow_nodes as workflow_nodes
from agent.nodes import advance_state


class ThreadMemoryTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = create_app()
        cls.client = cls.app.test_client()

    def build_patches(self, observations):

        def fake_supervisor(state):

            messages = state.get("messages") or []

            observations.append({
                "node": "supervisor",
                "contents": [
                    getattr(message, "content", "")
                    for message in messages
                ],
            })

            return {
                "task_plan": "回答问题",
                "next_agents": ["qa"],
                "current_agent_index": 0,
                "completed_agents": [],
            }

        def fake_qa(state):

            observations.append({
                "node": "qa",
                "question": state.get("user_query"),
            })

            return advance_state(
                state,
                "qa",
                {"qa_result": {"answer": "qa"}},
            )

        def fake_synthesis(state):

            messages = state.get("messages") or []
            answer = f"history_count={len(messages)}"

            observations.append({
                "node": "synthesis",
                "contents": [
                    getattr(message, "content", "")
                    for message in messages
                ],
            })

            return {
                "final_answer": answer,
                "messages": [
                    AIMessage(content=answer)
                ],
            }

        return (
            patch.object(
                workflow_nodes,
                "supervisor_agent",
                side_effect=fake_supervisor,
            ),
            patch.object(
                workflow_nodes,
                "qa_agent",
                side_effect=fake_qa,
            ),
            patch.object(
                workflow_nodes,
                "supervisor_synthesis_agent",
                side_effect=fake_synthesis,
            ),
        )

    def test_same_thread_keeps_history(self):

        thread_id = f"test-{uuid4()}"
        observations = []

        supervisor_patch, qa_patch, synthesis_patch = (
            self.build_patches(observations)
        )

        with supervisor_patch, qa_patch, synthesis_patch:
            first = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "这篇论文提出了什么框架？",
                    "paper_id": 6,
                    "thread_id": thread_id,
                },
            )

            second = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "它的核心流程是什么？",
                    "paper_id": 6,
                    "thread_id": thread_id,
                },
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        first_data = first.get_json()["data"]
        second_data = second.get_json()["data"]

        self.assertEqual(first_data["thread_id"], thread_id)
        self.assertEqual(second_data["thread_id"], thread_id)
        self.assertEqual(
            first_data["final_answer"],
            "history_count=1"
        )
        self.assertEqual(
            second_data["final_answer"],
            "history_count=3"
        )

        second_supervisor = next(
            item
            for item in observations
            if item["node"] == "supervisor"
            and item["contents"][-1] == "它的核心流程是什么？"
        )

        self.assertEqual(
            second_supervisor["contents"],
            [
                "这篇论文提出了什么框架？",
                "history_count=1",
                "它的核心流程是什么？",
            ]
        )

    def test_new_thread_has_no_old_history(self):

        first_thread = f"test-{uuid4()}"
        second_thread = f"test-{uuid4()}"
        observations = []

        supervisor_patch, qa_patch, synthesis_patch = (
            self.build_patches(observations)
        )

        with supervisor_patch, qa_patch, synthesis_patch:
            first = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "第一段会话的问题",
                    "paper_id": 6,
                    "thread_id": first_thread,
                },
            )

            second = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "新会话的问题",
                    "paper_id": 6,
                    "thread_id": second_thread,
                },
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        second_data = second.get_json()["data"]

        self.assertEqual(
            second_data["thread_id"],
            second_thread
        )
        self.assertEqual(
            second_data["final_answer"],
            "history_count=1"
        )

        second_supervisor = next(
            item
            for item in observations
            if item["node"] == "supervisor"
            and item["contents"][-1] == "新会话的问题"
        )

        self.assertEqual(
            second_supervisor["contents"],
            ["新会话的问题"]
        )

    def test_missing_thread_id_creates_new_session(self):

        observations = []

        supervisor_patch, qa_patch, synthesis_patch = (
            self.build_patches(observations)
        )

        with supervisor_patch, qa_patch, synthesis_patch:
            first = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "没有线程 ID 的问题一",
                    "paper_id": 6,
                },
            )

            second = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "没有线程 ID 的问题二",
                    "paper_id": 6,
                },
            )

        first_data = first.get_json()["data"]
        second_data = second.get_json()["data"]

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(
            first_data["thread_id"],
            second_data["thread_id"]
        )
        self.assertEqual(
            second_data["final_answer"],
            "history_count=1"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
