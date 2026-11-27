
import sys

from app import create_app

from services.embedding_pipeline_service import (
    embedding_pipeline_service,
    EmbeddingPipelineError
)

from ai.embedding_service import EmbeddingError

from rag.vector_store import (
    vector_store,
    VectorStoreError
)


def main():

    if len(sys.argv) < 2:
        print(
            "使用方法："
            "python -m tests.manual_test_embedding_pipeline 论文ID"
        )
        return

    try:
        paper_id = int(sys.argv[1])
    except ValueError:
        print("论文 ID 必须是整数。")
        return

    app = create_app()

    with app.app_context():

        try:

            print("=" * 50)
            print("开始执行论文向量化入库")
            print("论文 ID：", paper_id)

            # 1. 执行完整向量化流程
            result = (
                embedding_pipeline_service.index_paper(
                    paper_id
                )
            )

            # 2. 从 ChromaDB 重新读取数据
            stored_result = (
                vector_store.get_paper_chunks(
                    paper_id
                )
            )

            # 3. 输出处理结果
            print("=" * 50)
            print("向量化入库成功！")

            print("论文标题：", result["paper_title"])
            print("论文 ID：", result["paper_id"])

            print("Chunk 总数：", result["chunks_count"])
            print("成功入库：", result["indexed_count"])

            print("Embedding 模型：", result["embedding_model"])
            print("向量维度：", result["dimensions"])

            print("总 Token：", result["total_tokens"])
            print("向量生成耗时：", result["embedding_time_ms"], "ms")

            print(
                "ChromaDB 实际查询数量：",
                len(stored_result["ids"])
            )

            print("=" * 50)

            # 4. 显示前 3 条记录
            for i in range(
                min(3, len(stored_result["ids"]))
            ):

                print("记录 ID：", stored_result["ids"][i])
                print("原文：", stored_result["documents"][i])
                print("元数据：", stored_result["metadatas"][i])
                print("-" * 40)

            # 5. 最终验收
            if (
                result["indexed_count"] == result["chunks_count"]
                and len(stored_result["ids"]) == result["chunks_count"]
            ):
                print("测试通过：论文向量化入库成功。")
            else:
                print("测试失败：入库数量不一致。")

        except (
            EmbeddingPipelineError,
            EmbeddingError,
            VectorStoreError
        ) as error:

            print("向量化入库失败：", error)


if __name__ == "__main__":
    main()
