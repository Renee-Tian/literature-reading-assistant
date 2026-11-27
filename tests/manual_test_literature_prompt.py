from ai.prompts.literature_reading import (
    build_literature_reading_messages,
)


def test_prompt_structure():
    """检查 Prompt 的基本结构。"""

    sample_text = """
    本文研究基于深度学习的图像分类方法。
    作者提出了一种新的特征提取方法。
    实验使用公开数据集进行验证。
    """

    messages = build_literature_reading_messages(
        paper_text=sample_text,
        title="基于深度学习的图像分类研究",
    )

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"

    assert "研究背景" in messages[0]["content"]
    assert "研究方法" in messages[0]["content"]
    assert "研究局限" in messages[0]["content"]

    assert "基于深度学习的图像分类研究" in messages[1]["content"]
    assert sample_text in messages[1]["content"]

    print("Prompt 结构测试通过。")
    print("消息数量：", len(messages))
    print("System Prompt 长度：", len(messages[0]["content"]))
    print("User Prompt 长度：", len(messages[1]["content"]))


def test_empty_text():
    """检查空论文文本是否被拒绝。"""

    try:
        build_literature_reading_messages("")

    except ValueError as error:
        print("空文本校验通过：", error)

    else:
        raise AssertionError("空论文文本没有触发异常。")


if __name__ == "__main__":
    test_prompt_structure()
    test_empty_text()

    print("\n所有 Prompt 测试完成。")