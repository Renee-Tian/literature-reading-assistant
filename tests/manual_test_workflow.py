import importlib
import unittest
from unittest.mock import patch

from agent.nodes import advance_state


workflow_module = importlib.import_module(
    "agent.workflow"
)


def fake_supervisor_node(state):

    return {
        "task_plan": "测试计划",
        "next_agents": state["test_next_agents"],
        "current_agent_index": 0,
        "completed_agents": [],
    }


def make_fake_agent(agent_name, result_key):

    def fake_agent(state):

        return advance_state(
            state,
            agent_name,
            {
                result_key: {
                    "agent": agent_name
                }
            },
        )

    return fake_agent


def fake_synthesis_node(state):

    return {
        "final_answer": "整合完成"
    }


class WorkflowTest(unittest.TestCase):

    def build_fake_workflow(self, next_agents):

        with patch.object(
            workflow_module,
            "supervisor_node",
            side_effect=lambda state: fake_supervisor_node({
                **state,
                "test_next_agents": next_agents,
            }),
        ), patch.object(
            workflow_module,
            "reading_node",
            side_effect=make_fake_agent(
                "reading",
                "reading_result",
            ),
        ), patch.object(
            workflow_module,
            "qa_node",
            side_effect=make_fake_agent(
                "qa",
                "qa_result",
            ),
        ), patch.object(
            workflow_module,
            "research_node",
            side_effect=make_fake_agent(
                "research",
                "research_result",
            ),
        ), patch.object(
            workflow_module,
            "synthesis_node",
            side_effect=fake_synthesis_node,
        ):
            graph = workflow_module.build_workflow()

        return graph

    def test_initial_state(self):

        state = workflow_module.build_initial_state(
            user_query="测试问题",
            paper_ids=[6],
            top_k=3,
        )

        self.assertEqual(state["user_query"], "测试问题")
        self.assertEqual(state["paper_ids"], [6])
        self.assertEqual(state["current_agent_index"], 0)
        self.assertEqual(state["completed_agents"], [])

    def test_initial_state_validation(self):

        with self.assertRaises(ValueError):
            workflow_module.build_initial_state(
                user_query="",
                paper_ids=[6],
            )

        with self.assertRaises(ValueError):
            workflow_module.build_initial_state(
                user_query="问题",
                paper_ids=[],
            )

        with self.assertRaises(ValueError):
            workflow_module.build_initial_state(
                user_query="问题",
                paper_ids=[1, 2],
            )

    def test_single_agent_workflow(self):

        graph = self.build_fake_workflow(["reading"])

        result = graph.invoke(
            workflow_module.build_initial_state(
                user_query="概括论文",
                paper_ids=[6],
            ),
            config={
                "configurable": {
                    "thread_id": "test-single-agent"
                }
            },
        )

        self.assertEqual(
            result["completed_agents"],
            ["reading"]
        )
        self.assertIn("reading_result", result)
        self.assertEqual(result["final_answer"], "整合完成")

    def test_multi_agent_workflow_order(self):

        graph = self.build_fake_workflow([
            "reading",
            "qa",
            "research",
        ])

        result = graph.invoke(
            workflow_module.build_initial_state(
                user_query="综合任务",
                paper_ids=[6],
            ),
            config={
                "configurable": {
                    "thread_id": "test-multi-agent"
                }
            },
        )

        self.assertEqual(
            result["completed_agents"],
            ["reading", "qa", "research"]
        )
        self.assertIn("reading_result", result)
        self.assertIn("qa_result", result)
        self.assertIn("research_result", result)
        self.assertEqual(result["final_answer"], "整合完成")

    def test_router_after_all_agents(self):

        route = workflow_module.route_next_agent({
            "next_agents": ["reading", "qa"],
            "current_agent_index": 2,
            "completed_agents": ["reading", "qa"],
        })

        self.assertEqual(route, "synthesis")

    def test_router_selects_next_agent(self):

        route = workflow_module.route_next_agent({
            "next_agents": ["reading", "qa", "research"],
            "current_agent_index": 1,
            "completed_agents": ["reading"],
        })

        self.assertEqual(route, "qa")


if __name__ == "__main__":
    unittest.main(verbosity=2)
