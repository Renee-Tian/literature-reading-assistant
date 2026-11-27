
from unittest.mock import patch

from services.reading_service import (
    generate_reading_report,
    validate_reading_report,
    ReadingReportError,
)


def build_fake_report():
    """构造一份符合结构要求的模拟报告。"""

    return {
        "paper_title": "基于深度学习的图像分类研究",
        "research_background": "图像分类是计算机视觉的重要研究任务。",
        "research_problem": "传统方法在复杂图像场景下存在局限。",
        "research_objective": "提高图像分类的准确性。",
        "research_method": "采用深度学习方法进行特征提取。",
        "experimental_design": "使用公开数据集开展实验。",
        "main_results": "实验结果显示分类效果得到改善。",
        "contributions": "提出了一种新的特征提取思路。",
        "limitations": "原文未明确说明。",
        "future_work": "原文未明确说明。",
        "overall_summary": "本文研究了基于深度学习的图像分类方法。",
        "not_stated": [
            "具体数据集名称原文未明确说明。",
            "具体评价指标原文未明确说明。",
        ],
    }


def test_generate_reading_report():
    """测试阅读报告生成主流程。"""

    fake_result = {
        "data": build_fake_report(),
        "model": "test-model",
        "usage": {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500,
        },
        "elapsed_ms": 800,
        "request_id": "test-request-001",
    }

    with patch(
        "services.reading_service.chat_completion_json",
        return_value=fake_result,
    ):
        result = generate_reading_report(
            paper_text="本文研究基于深度学习的图像分类方法。",
            title="基于深度学习的图像分类研究",
        )

    assert result["report"]["paper_title"] == (
        "基于深度学习的图像分类研究"
    )

    assert result["model"] == "test-model"
    assert result["usage"]["total_tokens"] == 1500

    print("阅读报告生成流程测试通过。")
    print("报告标题：", result["report"]["paper_title"])
    print("Token 总量：", result["usage"]["total_tokens"])


def test_invalid_report():
    """测试模型返回缺少字段的报告。"""

    invalid_report = {
        "paper_title": "测试论文",
    }

    try:
        validate_reading_report(invalid_report)

    except ReadingReportError as error:
        print("报告结构校验通过：", error)

    else:
        raise AssertionError("不完整的报告没有触发异常。")


def test_empty_paper():
    """测试空论文正文。"""

    try:
        generate_reading_report("")

    except ReadingReportError as error:
        print("空论文校验通过：", error)

    else:
        raise AssertionError("空论文没有触发异常。")


if __name__ == "__main__":
    test_generate_reading_report()
    test_invalid_report()
    test_empty_paper()

    print("\n所有阅读报告服务测试完成。")
