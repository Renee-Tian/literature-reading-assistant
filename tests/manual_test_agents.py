import importlib
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from app import create_app
from database.db import db
from models import Paper
from services.qa_service import QAServiceError


reading_module = importlib.import_module(
    "agent.agents.reading_agent"
)
qa_module = importlib.import_module(
    "agent.agents.qa_agent"
)
research_module = importlib.import_module(
    "agent.agents.research_agent"
)


FAKE_REPORT_RESULT = {
    "report": {
        "paper_title": "测试论文",
        "overall_summary": "这是测试摘要。",
    },
    "batch_count": 1,
    "model": "mock-model",
    "usage": {
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "total_tokens": 15,
    },
    "elapsed_ms": 12.5,
    "prompt_version": "1.0",
}


FAKE_RESEARCH_DATA = {
    "research_problem": "研究问题",
    "methodology": "研究方法",
    "algorithms": ["Transformer"],
    "experimental_design": "实验设计",
    "datasets": ["测试数据集"],
    "metrics": ["Accuracy"],
    "results": "实验结果",
    "contributions": ["主要贡献"],
    "limitations": ["局限性"],
    "evidence_ids": ["E1"],
}


class AgentTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.app = create_app()
        cls.context = cls.app.app_context()
        cls.context.push()

        cls.paper = (
            db.session.query(Paper)
            .order_by(Paper.id)
            .first()
        )

        if cls.paper is None:
            raise unittest.SkipTest(
                "MySQL 中没有论文，跳过 Reading Agent 集成测试。"
            )

    @classmethod
    def tearDownClass(cls):

        cls.context.pop()

    def test_reading_success(self):

        with patch.object(
            reading_module,
            "generate_long_document_report",
            return_value=FAKE_REPORT_RESULT,
        ):
            result = reading_module.reading_agent({
                "paper_ids": [self.paper.id]
            })

        self.assertIn("reading_result", result)
        self.assertEqual(
            set(result),
            {"reading_result"}
        )

        reading_result = result["reading_result"]

        self.assertEqual(
            reading_result["paper_id"],
            self.paper.id
        )
        self.assertEqual(
            reading_result["paper_title"],
            self.paper.title
        )
        self.assertGreater(
            reading_result["chunk_count"],
            0
        )
        self.assertEqual(
            reading_result["report"]["paper_title"],
            "测试论文"
        )

    def test_reading_invalid_paper_ids(self):

        with self.assertRaises(
            reading_module.ReadingAgentError
        ):
            reading_module.reading_agent({
                "paper_ids": []
            })

        with self.assertRaises(
            reading_module.ReadingAgentError
        ):
            reading_module.reading_agent({
                "paper_ids": [1, 2]
            })

        with self.assertRaises(
            reading_module.ReadingAgentError
        ):
            reading_module.reading_agent({
                "paper_ids": [0]
            })

    def test_reading_no_chunks(self):

        with patch.object(
            reading_module.ChunkRepository,
            "list_by_paper_id",
            return_value=[],
        ):
            with self.assertRaises(
                reading_module.ReadingAgentError
            ):
                reading_module.reading_agent({
                    "paper_ids": [self.paper.id]
                })

    def test_reading_long_document_error(self):

        with patch.object(
            reading_module,
            "generate_long_document_report",
            side_effect=reading_module.LongDocumentError(
                "模拟长文档处理失败"
            ),
        ):
            with self.assertRaises(
                reading_module.ReadingAgentError
            ):
                reading_module.reading_agent({
                    "paper_ids": [self.paper.id]
                })

    def test_qa_success(self):

        fake_result = {
            "answer": "测试答案",
            "citations": [],
            "evidence": [],
            "retrieval": {"search_mode": "hybrid"},
        }

        with patch.object(
            qa_module,
            "answer_question",
            return_value=fake_result,
        ):
            result = qa_module.qa_agent({
                "user_query": "这篇论文讲了什么？",
                "paper_ids": [self.paper.id],
            })

        self.assertEqual(set(result), {"qa_result"})
        self.assertEqual(
            result["qa_result"]["answer"],
            "测试答案"
        )
        self.assertEqual(
            result["qa_result"]["retrieval"]["search_mode"],
            "hybrid"
        )

    def test_qa_uses_resolved_query(self):

        fake_result = {
            "answer": "测试答案",
            "citations": [],
            "evidence": [],
            "retrieval": {},
        }

        with patch.object(
            qa_module,
            "answer_question",
            return_value=fake_result,
        ) as mocked_answer:
            qa_module.qa_agent({
                "user_query": "它的流程是什么？",
                "resolved_query": "MAR 框架的流程是什么？",
                "paper_ids": [self.paper.id],
            })

        self.assertEqual(
            mocked_answer.call_args.kwargs["question"],
            "MAR 框架的流程是什么？"
        )

    def test_qa_invalid_input(self):

        with self.assertRaises(qa_module.QAAgentError):
            qa_module.qa_agent({
                "user_query": "",
                "paper_ids": [self.paper.id],
            })

        with self.assertRaises(qa_module.QAAgentError):
            qa_module.qa_agent({
                "user_query": "问题",
                "paper_ids": [],
            })

        with self.assertRaises(qa_module.QAAgentError):
            qa_module.qa_agent({
                "user_query": "问题",
                "paper_ids": [1, 2],
            })

    def test_qa_service_exception(self):

        with patch.object(
            qa_module,
            "answer_question",
            side_effect=QAServiceError("模拟问答失败"),
        ):
            with self.assertRaises(qa_module.QAAgentError):
                qa_module.qa_agent({
                    "user_query": "问题",
                    "paper_ids": [self.paper.id],
                })

    def test_research_success(self):

        evidence = [
            {
                "evidence_id": "E1",
                "page_number": 1,
                "chunk_index": 0,
                "content": "论文使用 Transformer 方法。",
            }
        ]

        fake_llm_result = {
            "data": FAKE_RESEARCH_DATA,
            "model": "mock-llm",
            "usage": {"total_tokens": 20},
            "elapsed_ms": 3.2,
            "request_id": "mock-request",
        }

        with patch.object(
            research_module,
            "get_research_evidence",
            return_value=evidence,
        ), patch.object(
            research_module,
            "chat_completion_json",
            return_value=fake_llm_result,
        ):
            result = research_module.research_agent({
                "user_query": "分析这篇论文的方法和实验。",
                "paper_ids": [self.paper.id],
            })

        self.assertEqual(set(result), {"research_result"})

        research_result = result["research_result"]

        self.assertEqual(
            research_result["paper_id"],
            self.paper.id
        )
        self.assertEqual(
            research_result["analysis"]["methodology"],
            "研究方法"
        )
        self.assertEqual(
            research_result["analysis"]["algorithms"],
            ["Transformer"]
        )
        self.assertEqual(
            research_result["evidence"],
            evidence
        )

    def test_research_invalid_evidence_id(self):

        evidence = [
            {
                "evidence_id": "E1",
                "page_number": 1,
                "chunk_index": 0,
                "content": "测试原文",
            }
        ]

        invalid_data = dict(FAKE_RESEARCH_DATA)
        invalid_data["evidence_ids"] = ["E99"]

        with patch.object(
            research_module,
            "get_research_evidence",
            return_value=evidence,
        ), patch.object(
            research_module,
            "chat_completion_json",
            return_value={
                "data": invalid_data,
                "model": "mock-llm",
                "usage": {},
                "elapsed_ms": 1.0,
                "request_id": "mock-request",
            },
        ):
            with self.assertRaises(
                research_module.ResearchAgentError
            ):
                research_module.research_agent({
                    "user_query": "分析论文。",
                    "paper_ids": [self.paper.id],
                })

    def test_research_no_evidence(self):

        with patch.object(
            research_module,
            "get_research_evidence",
            return_value=[],
        ):
            with self.assertRaises(
                research_module.ResearchAgentError
            ):
                research_module.research_agent({
                    "user_query": "分析论文。",
                    "paper_ids": [self.paper.id],
                })

    def test_research_reuses_qa_evidence(self):

        evidence = [{"evidence_id": "E1"}]

        result = research_module.get_research_evidence(
            state={
                "qa_result": {
                    "evidence": evidence
                }
            },
            paper_id=self.paper.id,
            user_query="分析论文。",
        )

        self.assertEqual(result, evidence)


if __name__ == "__main__":
    unittest.main(verbosity=2)
