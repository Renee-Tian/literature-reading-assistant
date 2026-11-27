
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.embedding_service import (
    embedding_service,
    EmbeddingError
)

def cosine_similarity(vector_a, vector_b):

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    norm_a = math.sqrt(sum(a * a for a in vector_a))
    norm_b = math.sqrt(sum(b * b for b in vector_b))

    if norm_a == 0 or norm_b == 0:
        raise ValueError("不能计算零向量的相似度。")

    return dot_product / (norm_a * norm_b)

def main():

    # 模拟一段论文原文
    document_text = (
        "本文提出了一种基于改进 Transformer 架构的"
        "医学图像分类方法，并通过注意力机制提高分类准确率。"
    )

    # 模拟用户问题
    query_text = (
        "这篇论文通过什么方法提高医学图像分类准确率？"
    )

    try:

        # 1. 生成论文文本向量
        document_result = (
            embedding_service.embed_document(
                document_text
            )
        )

        # 2. 生成用户问题向量
        query_result = (
            embedding_service.embed_query(
                query_text
            )
        )

        similarity = cosine_similarity(
        document_result["embedding"],
        query_result["embedding"]
        )

        print("论文文本与用户问题的余弦相似度：", similarity)

        # 3. 输出论文文本的调用信息
        print("=" * 50)
        print("论文文本 Embedding 结果")
        print("模型：", document_result["model_name"])
        print("向量维度：", document_result["dimensions"])
        print("Sparse 非零元素数量：", document_result["sparse_nonzero_count"])
        print("Prompt Tokens：", document_result["prompt_tokens"])
        print("Total Tokens：", document_result["total_tokens"])
        print("请求耗时：", document_result["elapsed_ms"], "ms")
        print("向量前 5 维：", document_result["embedding"][:5])

        # 4. 输出用户问题的调用信息
        print("=" * 50)
        print("用户问题 Embedding 结果")
        print("模型：", query_result["model_name"])
        print("向量维度：", query_result["dimensions"])
        print("Sparse 非零元素数量：", query_result["sparse_nonzero_count"])
        print("Prompt Tokens：", query_result["prompt_tokens"])
        print("Total Tokens：", query_result["total_tokens"])
        print("请求耗时：", query_result["elapsed_ms"], "ms")
        print("向量前 5 维：", query_result["embedding"][:5])

        print("=" * 50)

        if (
            document_result["dimensions"] == 1024
            and query_result["dimensions"] == 1024
            and document_result["sparse_nonzero_count"] > 0
            and query_result["sparse_nonzero_count"] > 0
        ):
            print("测试通过：Doubao Dense + Sparse Embedding 调用成功。")
        else:
            print("测试失败：向量维度或 Sparse 向量不符合预期。")

    except EmbeddingError as error:
        print("Embedding 测试失败：", error)


if __name__ == "__main__":
    main()
