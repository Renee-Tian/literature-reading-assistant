
from rag.vector_store import ChromaVectorStore

def main():

    # 使用专门的测试 ID，避免影响真实论文
    test_paper_id = 999999

    store = ChromaVectorStore()

    print("当前向量库记录数：", store.count())

    # 使用模拟向量测试 ChromaDB
    # 注意：这里不是 Doubao 生成的真实语义向量
    test_chunks = [

        {
            "paper_id": test_paper_id,
            "chunk_index": 0,
            "page_number": 1,
            "content": "这是一段用于测试的论文文本。",
            "embedding": [0.001] * 1024,
            "sparse_embedding": [
                {"index": 0, "value": 1.0},
                {"index": 2, "value": 0.5}
            ]
        },

        {
            "paper_id": test_paper_id,
            "chunk_index": 1,
            "page_number": 2,
            "content": "这是第二段用于测试的论文文本。",
            "embedding": [0.002] * 1024,
            "sparse_embedding": [
                {"index": 1, "value": 1.0},
                {"index": 3, "value": 0.5}
            ]
        }

    ]

    # 保存测试向量
    saved_count = store.upsert_chunks(test_chunks)

    print("本次保存记录数：", saved_count)
    print("当前向量库记录数：", store.count())

    # 根据论文 ID 获取记录
    result = store.get_paper_chunks(test_paper_id)

    print("查询到的记录数：", len(result["ids"]))
    print("Chunk ID：", result["ids"])
    print("原文：", result["documents"])
    print("元数据：", result["metadatas"])

    # 重新创建客户端，模拟程序重新启动
    new_store = ChromaVectorStore()

    persisted_result = new_store.get_paper_chunks(
        test_paper_id
    )

    if len(persisted_result["ids"]) == 2:
        print("持久化测试通过：重新创建客户端后仍能读取数据。")
    else:
        print("持久化测试失败。")

    hybrid_results = new_store.search(
        query_embedding=[0.001] * 1024,
        query_sparse=[{"index": 0, "value": 1.0}],
        top_k=2,
        paper_id=test_paper_id
    )

    print("=" * 60)
    print("混合检索结果数：", len(hybrid_results))

    for item in hybrid_results:
        print("Chunk 编号：", item["chunk_index"])
        print("召回来源：", item["retrieval_sources"])
        print("RRF 分数：", round(item["rrf_score"], 6))
        print("Sparse 分数：", item["sparse_score"])
        print("-" * 40)

    if (
        hybrid_results
        and any(
            "sparse" in item["retrieval_sources"]
            for item in hybrid_results
        )
    ):
        print("混合检索验证成功：Dense 与 Sparse 双路召回已执行。")
    else:
        print("混合检索验证失败。")

    # 清理测试数据，不影响真实论文
    new_store.collection.delete(
        where={"paper_id": test_paper_id}
    )

    print("测试数据已清理。")
    print("最终向量库记录数：", new_store.count())

if __name__ == "__main__":
    main()