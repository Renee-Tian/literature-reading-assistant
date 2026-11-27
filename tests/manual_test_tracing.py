import json
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
from utils.logging_config import (
    AGENT_TRACE_FILE,
    APP_LOG_FILE,
)
from utils.trace import record_llm_call, record_retrieval_call


class TracingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = create_app()
        cls.client = cls.app.test_client()

    def get_trace_record(self, request_id):

        lines = AGENT_TRACE_FILE.read_text(
            encoding="utf-8"
        ).splitlines()

        for line in reversed(lines):
            if not line.strip():
                continue

            record = json.loads(line)

            if record.get("request_id") == request_id:
                return record

        return None

    def build_success_patches(self):

        def fake_supervisor(state):

            return {
                "resolved_query": "测试论文的核心方法是什么？",
                "task_plan": "检索并回答",
                "next_agents": ["qa"],
                "current_agent_index": 0,
                "completed_agents": [],
            }

        def fake_qa(state):

            record_retrieval_call({
                "paper_id": 6,
                "top_k": 3,
                "search_mode": "hybrid",
                "result_count": 3,
                "embedding_time_ms": 12.5,
                "search_time_ms": 1.5,
                "total_elapsed_ms": 14.0,
                "status": "success",
                "error": None,
            })

            record_llm_call({
                "model": "mock-llm",
                "status": "success",
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "elapsed_ms": 8.0,
                "request_id": "mock-llm-request",
                "error": None,
            })

            return advance_state(
                state,
                "qa",
                {
                    "qa_result": {
                        "answer": "测试答案",
                        "citations": [{"evidence_id": "E1"}],
                        "retrieval": {
                            "search_mode": "hybrid",
                            "result_count": 3,
                        },
                    }
                },
            )

        def fake_synthesis(state):

            answer = "整合后的测试答案"

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

    def test_success_trace(self):

        thread_id = f"trace-{uuid4()}"

        supervisor_patch, qa_patch, synthesis_patch = (
            self.build_success_patches()
        )

        with supervisor_patch, qa_patch, synthesis_patch:
            response = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "测试问题",
                    "paper_id": 6,
                    "thread_id": thread_id,
                    "top_k": 3,
                },
            )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()["data"]

        self.assertTrue(data["request_id"])
        self.assertEqual(data["thread_id"], thread_id)

        record = self.get_trace_record(
            data["request_id"]
        )

        self.assertIsNotNone(record)
        self.assertEqual(record["thread_id"], thread_id)
        self.assertEqual(record["status"], "success")

        self.assertEqual(
            record["supervisor"]["next_agents"],
            ["qa"]
        )
        self.assertEqual(
            record["supervisor"]["task_plan"],
            "检索并回答"
        )

        self.assertEqual(len(record["agents"]), 1)
        self.assertEqual(record["agents"][0]["name"], "qa")
        self.assertEqual(
            record["agents"][0]["status"],
            "success"
        )
        self.assertTrue(
            record["agents"][0]["started_at"]
        )
        self.assertTrue(
            record["agents"][0]["finished_at"]
        )
        self.assertGreaterEqual(
            record["agents"][0]["elapsed_ms"],
            0
        )

        self.assertEqual(len(record["llm_calls"]), 1)
        self.assertEqual(
            record["llm_calls"][0]["model"],
            "mock-llm"
        )
        self.assertEqual(
            record["llm_calls"][0]["total_tokens"],
            120
        )

        self.assertEqual(len(record["retrieval_calls"]), 1)
        self.assertEqual(
            record["retrieval_calls"][0]["search_mode"],
            "hybrid"
        )
        self.assertEqual(
            record["retrieval_calls"][0]["result_count"],
            3
        )

        self.assertEqual(
            record["summary"]["total_tokens"],
            120
        )
        self.assertEqual(
            record["summary"]["agent_count"],
            1
        )
        self.assertEqual(
            record["summary"]["success_agent_count"],
            1
        )
        self.assertEqual(
            record["summary"]["failed_agent_count"],
            0
        )
        self.assertTrue(
            APP_LOG_FILE.exists()
        )

    def test_failed_trace(self):

        thread_id = f"trace-{uuid4()}"

        def fake_supervisor(state):

            return {
                "resolved_query": "失败测试",
                "task_plan": "触发异常",
                "next_agents": ["qa"],
                "current_agent_index": 0,
                "completed_agents": [],
            }

        def fake_qa(state):

            raise RuntimeError("模拟 Agent 异常")

        with patch.object(
            workflow_nodes,
            "supervisor_agent",
            side_effect=fake_supervisor,
        ), patch.object(
            workflow_nodes,
            "qa_agent",
            side_effect=fake_qa,
        ):
            response = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "失败问题",
                    "paper_id": 6,
                    "thread_id": thread_id,
                },
            )

        self.assertEqual(response.status_code, 502)

        lines = AGENT_TRACE_FILE.read_text(
            encoding="utf-8"
        ).splitlines()

        record = None

        for line in reversed(lines):
            if not line.strip():
                continue

            candidate = json.loads(line)

            if (
                candidate.get("thread_id") == thread_id
                and candidate.get("status") == "failed"
            ):
                record = candidate
                break

        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "failed")
        self.assertTrue(record["errors"])
        self.assertEqual(
            record["agents"][0]["status"],
            "failed"
        )
        self.assertEqual(
            record["summary"]["failed_agent_count"],
            1
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
