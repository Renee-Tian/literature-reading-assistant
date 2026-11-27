import json
import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

from app import create_app
from database.db import db
from models import Paper, QARecord
from ai.embedding_service import embedding_service
from rag.vector_store import vector_store
import services.qa_service as qa_service_module


TEST_VECTOR_IDS = [
    "qa_e2e_test_chunk_0",
    "qa_e2e_test_chunk_1"
]


def cleanup(paper_id, qa_id=None):

    if qa_id is not None:
        record = db.session.get(QARecord, qa_id)

        if record is not None:
            db.session.delete(record)
            db.session.commit()

    vector_store.collection.delete(ids=TEST_VECTOR_IDS)


def main():

    app = create_app()
    ctx = app.app_context()
    ctx.push()

    qa_id = None

    try:
        paper = db.session.query(Paper).order_by(
            Paper.id
        ).first()

        if paper is None:
            raise RuntimeError(
                "MySQL 中没有论文，无法执行端到端测试。"
            )

        print("测试论文：", paper.id, paper.title)

        vector_store.collection.upsert(
            ids=TEST_VECTOR_IDS,
            embeddings=[
                [0.001] * 1024,
                [0.002] * 1024
            ],
            documents=[
                "本文提出了一种基于 Transformer 的图像分类方法。",
                "实验结果表明该方法在公开数据集上有效。"
            ],
            metadatas=[
                {
                    "paper_id": paper.id,
                    "chunk_index": 90000,
                    "page_number": 1,
                    "embedding_model": "mock-embedding",
                    "embedding_dimensions": 1024,
                    "sparse_vector": json.dumps(
                        {
                            "indices": [0, 2],
                            "values": [1.0, 0.5]
                        }
                    ),
                    "sparse_nonzero_count": 2
                },
                {
                    "paper_id": paper.id,
                    "chunk_index": 90001,
                    "page_number": 2,
                    "embedding_model": "mock-embedding",
                    "embedding_dimensions": 1024,
                    "sparse_vector": json.dumps(
                        {
                            "indices": [1, 3],
                            "values": [1.0, 0.5]
                        }
                    ),
                    "sparse_nonzero_count": 2
                }
            ]
        )

        embedding_service.embed_query = lambda question: {
            "embedding": [0.001] * 1024,
            "dense_embedding": [0.001] * 1024,
            "sparse_embedding": [
                {"index": 0, "value": 1.0}
            ],
            "sparse_nonzero_count": 1,
            "model_name": "mock-embedding",
            "dimensions": 1024,
            "prompt_tokens": 10,
            "total_tokens": 10,
            "elapsed_ms": 1.0,
            "request_id": "mock-embedding-request"
        }

        qa_service_module.chat_completion_json = lambda **kwargs: {
            "data": {
                "answer": "论文使用了 Transformer 方法。[E1]",
                "citations": [
                    {
                        "evidence_id": "E1",
                        "quote": "本文提出了一种基于 Transformer 的图像分类方法。",
                        "reason": "该原文直接说明了论文使用的方法。"
                    }
                ]
            },
            "model": "mock-llm",
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30
            },
            "elapsed_ms": 2.0,
            "request_id": "mock-llm-request"
        }

        client = app.test_client()

        response = client.post(
            f"/api/papers/{paper.id}/qa",
            json={
                "question": "这篇论文使用了什么方法？",
                "top_k": 2,
                "save_history": True
            }
        )

        payload = response.get_json()

        print("HTTP 状态码：", response.status_code)
        print("响应状态：", payload.get("status"))
        print("检索信息：", payload["data"].get("retrieval"))
        print("回答：", payload["data"].get("answer"))
        print("引用数量：", len(payload["data"].get("citations", [])))

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["data"]["retrieval"]["search_mode"] == "hybrid"
        assert payload["data"]["answer"]
        assert payload["data"]["citations"]
        assert payload["data"]["qa_record"]["id"] is not None

        qa_id = payload["data"]["qa_record"]["id"]

        saved_record = db.session.get(QARecord, qa_id)

        assert saved_record is not None
        assert saved_record.paper_id == paper.id

        print("MySQL 问答记录：", saved_record.id)
        print("E2E PASS")

    finally:
        cleanup(
            paper_id=(
                paper.id
                if "paper" in locals() and paper is not None
                else None
            ),
            qa_id=qa_id
        )

        ctx.pop()


if __name__ == "__main__":
    main()
