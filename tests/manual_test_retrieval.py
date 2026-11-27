
import sys

from rag.retrieval_service import (
    retrieval_service,
    RetrievalError
)


def main():

    if len(sys.argv) < 2:
        print(
            '使用方法：python -m tests.manual_test_retrieval '
            '"你的问题" [论文ID] [Top-K]'
        )
        return

    question = sys.argv[1]

    paper_id = None
    top_k = 5

    try:

        if len(sys.argv) >= 3:
            paper_id = int(sys.argv[2])

        if len(sys.argv) >= 4:
            top_k = int(sys.argv[3])

    except ValueError:
        print("论文 ID 和 Top-K 必须是整数。")
        return

    try:

        print("=" * 60)
        print("开始执行学术文献语义检索")
        print("用户问题：", question)
        print("论文 ID：", paper_id)
        print("Top-K：", top_k)

        # 执行检索
        result = retrieval_service.search(
            question=question,
            paper_id=paper_id,
            top_k=top_k
        )

        print("=" * 60)
        print("检索执行成功")

        print("检索模式：", result["search_mode"])
        print("Embedding 模型：", result["embedding_model"])
        print("Query 向量维度：", result["query_dimensions"])
        print("Sparse 非零元素数量：", result["sparse_nonzero_count"])
        print("Query Tokens：", result["query_tokens"])
        print("Query 向量生成耗时：", result["embedding_time_ms"], "ms")

        print("检索结果数量：", result["result_count"])

        print("=" * 60)

        # 展示检索结果
        for index, item in enumerate(
            result["results"],
            start=1
        ):

            print(f"第 {index} 条检索结果")

            print("向量 ID：", item["id"])
            print("论文 ID：", item["paper_id"])
            print("Chunk 编号：", item["chunk_index"])
            print("原文页码：", item["page_number"])

            print("余弦距离：", round(item["distance"], 4))
            print("余弦相似度参考值：", round(item["similarity"], 4))
            print("召回来源：", item["retrieval_sources"])
            print("RRF 分数：", round(item["rrf_score"], 6))
            print("Sparse 分数：", item["sparse_score"])

            print("论文原文：")
            print(item["content"])

            print("-" * 60)

        if result["result_count"] > 0:
            print("测试通过：Dense + Sparse 混合检索成功。")
        else:
            print("检索执行成功，但没有找到相关记录。")

    except RetrievalError as error:

        print("检索失败：", error)


if __name__ == "__main__":
    main()
