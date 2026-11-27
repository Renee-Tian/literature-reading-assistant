
from ai.embedding_service import (
    embedding_service,
    EmbeddingError
)

from rag.vector_store import (
    vector_store,
    VectorStoreError
)

from utils.trace import record_retrieval_call

import time


class RetrievalError(Exception):
    """语义检索异常。"""
    pass


class RetrievalService:
    """学术文献 Dense + Sparse 混合检索服务。"""

    @staticmethod
    def search(
        question: str,
        paper_id: int | None = None,
        top_k: int = 5
    ) -> dict:
        """
        将用户问题转换为向量，
        并从 ChromaDB 检索相关论文片段。
        """

        if not isinstance(question, str) or not question.strip():
            raise RetrievalError("检索问题不能为空。")

        start_time = time.perf_counter()

        def record_failure(error):
            record_retrieval_call({
                "paper_id": paper_id,
                "top_k": top_k,
                "search_mode": None,
                "result_count": 0,
                "embedding_time_ms": None,
                "search_time_ms": None,
                "total_elapsed_ms": round(
                    (time.perf_counter() - start_time) * 1000,
                    2,
                ),
                "status": "failed",
                "error": str(error),
            })

        try:

            # 1. 将用户问题转换为 Dense + Sparse Query 向量
            embedding_result = (
                embedding_service.embed_query(question)
            )

            query_embedding = embedding_result["embedding"]
            query_sparse = embedding_result.get(
                "sparse_embedding"
            )

            search_mode = (
                "hybrid"
                if query_embedding and query_sparse
                else "dense"
            )

            # 2. 执行 Dense + Sparse 混合召回
            search_start_time = time.perf_counter()

            results = vector_store.search(
                query_embedding=query_embedding,
                query_sparse=query_sparse,
                top_k=top_k,
                paper_id=paper_id
            )

            search_elapsed_ms = round(
                (
                    time.perf_counter()
                    - search_start_time
                ) * 1000,
                2,
            )

            total_elapsed_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )

            record_retrieval_call({
                "paper_id": paper_id,
                "top_k": top_k,
                "search_mode": search_mode,
                "result_count": len(results),
                "embedding_time_ms": (
                    embedding_result["elapsed_ms"]
                ),
                "search_time_ms": search_elapsed_ms,
                "total_elapsed_ms": total_elapsed_ms,
                "status": "success",
                "error": None,
            })

            # 3. 组织检索结果
            return {

                "question": question,

                "paper_id": paper_id,

                "search_mode": search_mode,

                "embedding_model": (
                    embedding_result["model_name"]
                ),

                "query_dimensions": (
                    embedding_result["dimensions"]
                ),

                "sparse_nonzero_count": (
                    embedding_result.get(
                        "sparse_nonzero_count"
                    )
                ),

                "query_tokens": (
                    embedding_result.get("total_tokens")
                ),

                "embedding_time_ms": (
                    embedding_result["elapsed_ms"]
                ),

                "result_count": len(results),

                "results": results

            }

        except EmbeddingError as error:

            record_failure(error)

            raise RetrievalError(
                f"Query 向量生成失败：{error}"
            ) from error

        except VectorStoreError as error:

            record_failure(error)

            raise RetrievalError(
                f"向量检索失败：{error}"
            ) from error


retrieval_service = RetrievalService()
