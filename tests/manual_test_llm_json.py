from unittest.mock import patch

from ai.llm_service import (
    chat_completion_json,
    LLMError,
)


def test_valid_json():
    """测试模型返回合法 JSON。"""

    fake_result = {
        "content": (
            '{"research_method": "深度学习", '
            '"research_goal": "图像分类"}'
        ),
        "model": "test-model",
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
        "elapsed_ms": 200,
        "request_id": "test-001",
    }

    with patch(
        "ai.llm_service.chat_completion",
        return_value=fake_result,
    ):
        result = chat_completion_json(
            messages=[
                {
                    "role": "user",
                    "content": "分析这篇论文。",
                }
            ]
        )

    assert isinstance(result["data"], dict)
    assert result["data"]["research_method"] == "深度学习"

    print("合法 JSON 测试通过。")
    print("解析结果：", result["data"])


def test_invalid_json():
    """测试模型返回非法 JSON。"""

    fake_result = {
        "content": "这不是合法 JSON",
        "model": "test-model",
        "usage": {},
        "elapsed_ms": 100,
        "request_id": "test-002",
    }

    with patch(
        "ai.llm_service.chat_completion",
        return_value=fake_result,
    ):
        try:
            chat_completion_json(
                messages=[
                    {
                        "role": "user",
                        "content": "分析这篇论文。",
                    }
                ]
            )
        except LLMError as error:
            print("非法 JSON 已被正确识别：", error)
        else:
            raise AssertionError("非法 JSON 没有触发异常。")


if __name__ == "__main__":
    test_valid_json()
    test_invalid_json()

    print("\n所有结构化输出测试完成。")