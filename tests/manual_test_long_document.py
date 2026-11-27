
from unittest.mock import patch

from services.long_document_service import (
    build_batches,
    generate_long_document_report,
    LongDocumentError,
)


def build_test_chunks():
    """构造测试用的论文 Chunk。"""

    return [
        {
            "chunk_index": index,
            "page_number": index // 2 + 1,
            "content": f"这是第 {index} 个 Chunk 的测试论文内容。" * 10,
        }
        for index in range(10)
    ]


def test_build_batches():
    """测试 Chunk 分批。"""

    chunks = build_test_chunks()

    batches = build_batches(
        chunks=chunks,
        max_chars=1000,
    )

    assert len(batches) > 1

    all_chunks = [
        chunk
        for batch in batches
        for chunk in batch
    ]

    assert len(all_chunks) == len(chunks)

    indexes = [
        chunk["chunk_index"]
        for chunk in all_chunks
    ]

    assert indexes == list(range(10))

    assert all(
        sum(len(chunk["content"]) for chunk in batch) <= 1000
        for batch in batches
    )

    print("Chunk 分批测试通过。")
    print("Chunk 总数：", len(chunks))
    print("批次数量：", len(batches))


def test_invalid_chunk():
    """测试非法 Chunk。"""

    try:
        build_batches(
            chunks=[
                {
                    "chunk_index": 0,
                    "page_number": 1,
                    "content": "",
                }
            ]
        )

    except LongDocumentError as error:
        print("非法 Chunk 校验通过：", error)

    else:
        raise AssertionError("非法 Chunk 没有触发异常。")


def test_long_document_pipeline():
    """测试分批分析和最终汇总流程。"""

    chunks = build_test_chunks()

    fake_batch_result = {
        "data": {
            "partial_summary": "本批次研究了论文的核心问题。",
            "key_findings": ["提出了一种研究方法。"],
            "unresolved_questions": ["具体实验结果尚待确认。"],
            "source_pages": ["第 1 页"],
        },
        "model": "test-model",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
        "elapsed_ms": 100,
        "request_id": "test-batch",
        "batch_number": 1,
    }

    fake_final_result = {
        "report": {
            "paper_title": "测试论文",
        },
        "model": "test-model",
        "usage": {
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
        },
        "elapsed_ms": 200,
        "prompt_version": "1.0",
    }

    with patch(
        "services.long_document_service.summarize_batch",
        return_value=fake_batch_result,
    ) as mock_batch, patch(
        "services.long_document_service.generate_reading_report",
        return_value=fake_final_result,
    ):
        result = generate_long_document_report(
            chunks=chunks,
            title="测试论文",
            max_chars=1000,
        )

    assert result["batch_count"] > 1
    assert result["usage"]["total_tokens"] == (
        result["batch_count"] * 150 + 300
    )

    assert mock_batch.call_count == result["batch_count"]

    print("长文档处理流程测试通过。")
    print("批次数量：", result["batch_count"])
    print("累计 Token：", result["usage"]["total_tokens"])


if __name__ == "__main__":
    test_build_batches()
    test_invalid_chunk()
    test_long_document_pipeline()

    print("\n所有长文档处理测试完成。")
