import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from app import create_app
import agent.nodes.workflow_nodes as workflow_nodes
from agent.nodes import advance_state


class AgentAPITest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_invalid_request(self):

        response = self.client.post(
            "/api/agent/ask",
            json={"paper_id": 6},
        )

        self.assertEqual(response.status_code, 400)

    def test_api_triggers_all_agents(self):

        invoked = []

        def fake_supervisor(state):

            return {
                "task_plan": "先阅读，再问答，最后研究分析",
                "next_agents": [
                    "reading",
                    "qa",
                    "research",
                ],
                "current_agent_index": 0,
                "completed_agents": [],
            }

        def fake_reading(state):

            invoked.append("reading")

            return advance_state(
                state,
                "reading",
                {"reading_result": {"status": "ok"}},
            )

        def fake_qa(state):

            invoked.append("qa")

            return advance_state(
                state,
                "qa",
                {"qa_result": {"status": "ok"}},
            )

        def fake_research(state):

            invoked.append("research")

            return advance_state(
                state,
                "research",
                {"research_result": {"status": "ok"}},
            )

        def fake_synthesis(state):

            invoked.append("synthesis")

            return {"final_answer": "整合完成"}

        with patch.object(
            workflow_nodes,
            "supervisor_agent",
            side_effect=fake_supervisor,
        ), patch.object(
            workflow_nodes,
            "reading_agent",
            side_effect=fake_reading,
        ), patch.object(
            workflow_nodes,
            "qa_agent",
            side_effect=fake_qa,
        ), patch.object(
            workflow_nodes,
            "research_agent",
            side_effect=fake_research,
        ), patch.object(
            workflow_nodes,
            "supervisor_synthesis_agent",
            side_effect=fake_synthesis,
        ):
            response = self.client.post(
                "/api/agent/ask",
                json={
                    "question": "综合阅读、问答和研究分析论文",
                    "paper_id": 6,
                    "top_k": 3,
                },
            )

        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        data = payload["data"]

        self.assertEqual(payload["status"], "success")
        self.assertEqual(
            data["completed_agents"],
            ["reading", "qa", "research"],
        )
        self.assertEqual(
            invoked,
            [
                "reading",
                "qa",
                "research",
                "synthesis",
            ],
        )
        self.assertEqual(data["final_answer"], "整合完成")
        self.assertTrue(data["reading_result"])
        self.assertTrue(data["qa_result"])
        self.assertTrue(data["research_result"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
