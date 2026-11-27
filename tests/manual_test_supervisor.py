import importlib
import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage


supervisor_module = importlib.import_module(
    "agent.agents.supervisor"
)


class SupervisorDispatchTest(unittest.TestCase):
    """验证 Supervisor 的调度协议和输出校验。"""

    def run_supervisor(self, decision, user_query="测试请求"):

        payload = {
            "resolved_query": user_query,
            **decision,
        }

        with patch.object(
            supervisor_module,
            "chat_completion_json",
            return_value={"data": payload},
        ):
            return supervisor_module.supervisor_agent({
                "user_query": user_query
            })

    def test_single_reading_selection(self):

        result = self.run_supervisor({
            "task_plan": "整体阅读并概括论文",
            "next_agents": ["reading"],
        })

        self.assertEqual(
            result["next_agents"],
            ["reading"]
        )
        self.assertEqual(
            result["task_plan"],
            "整体阅读并概括论文"
        )

    def test_single_qa_selection(self):

        result = self.run_supervisor({
            "task_plan": "检索原文证据并回答问题",
            "next_agents": ["qa"],
        })

        self.assertEqual(
            result["next_agents"],
            ["qa"]
        )

    def test_single_research_selection(self):

        result = self.run_supervisor({
            "task_plan": "分析研究方法与实验结果",
            "next_agents": ["research"],
        })

        self.assertEqual(
            result["next_agents"],
            ["research"]
        )

    def test_multi_agent_selection(self):

        result = self.run_supervisor({
            "task_plan": "先检索，再总结，最后分析",
            "next_agents": [
                "qa",
                "reading",
                "research"
            ],
        })

        self.assertEqual(
            result["next_agents"],
            ["qa", "reading", "research"]
        )

    def test_invalid_agent_name(self):

        with self.assertRaises(ValueError):
            self.run_supervisor({
                "task_plan": "非法调度",
                "next_agents": [
                    "literature_retrieval"
                ],
            })

    def test_duplicate_agent(self):

        with self.assertRaises(ValueError):
            self.run_supervisor({
                "task_plan": "重复调度",
                "next_agents": [
                    "qa",
                    "qa"
                ],
            })

    def test_empty_next_agents(self):

        with self.assertRaises(ValueError):
            self.run_supervisor({
                "task_plan": "没有选择 Agent",
                "next_agents": [],
            })

    def test_empty_task_plan(self):

        with self.assertRaises(ValueError):
            self.run_supervisor({
                "task_plan": "",
                "next_agents": ["reading"],
            })

    def test_empty_user_query(self):

        with self.assertRaises(ValueError):
            self.run_supervisor(
                {
                    "task_plan": "计划",
                    "next_agents": ["reading"],
                },
                user_query="",
            )

    def test_history_is_passed_to_llm(self):

        with patch.object(
            supervisor_module,
            "chat_completion_json",
            return_value={
                "data": {
                    "resolved_query": "MAR 框架的流程是什么？",
                    "task_plan": "结合上下文继续回答",
                    "next_agents": ["qa"],
                }
            },
        ) as mocked_llm:
            result = supervisor_module.supervisor_agent({
                "user_query": "它的流程是什么？",
                "messages": [
                    HumanMessage(
                        content="这篇论文提出了什么框架？"
                    ),
                    AIMessage(
                        content="论文提出了 MAR 框架。"
                    ),
                    HumanMessage(
                        content="它的流程是什么？"
                    ),
                ],
            })

        messages = mocked_llm.call_args.kwargs["messages"]

        self.assertEqual(
            [item["role"] for item in messages],
            ["system", "user", "assistant", "user"]
        )
        self.assertEqual(
            messages[-1]["content"],
            "它的流程是什么？"
        )
        self.assertEqual(
            result["resolved_query"],
            "MAR 框架的流程是什么？"
        )

    def test_state_update_shape(self):

        result = self.run_supervisor({
            "task_plan": "问答任务",
            "next_agents": ["qa"],
        })

        self.assertEqual(
            set(result),
            {
                "resolved_query",
                "task_plan",
                "next_agents",
            }
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
