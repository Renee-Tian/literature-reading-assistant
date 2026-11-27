
"""
论文智能阅读报告生成服务。

职责：
1. 接收论文标题和正文。
2. 构建学术论文阅读 Prompt。
3. 调用 LLM 生成结构化报告。
4. 校验报告字段和数据类型。
5. 返回报告及模型调用信息。

本模块暂不负责数据库持久化。
"""

from ai.llm_service import chat_completion_json
from ai.prompts.literature_reading import (
    build_literature_reading_messages,
    LITERATURE_READING_PROMPT_VERSION,
)


class ReadingReportError(Exception):
    """论文阅读报告生成异常。"""
    pass


REQUIRED_STRING_FIELDS = [
    "paper_title",
    "research_background",
    "research_problem",
    "research_objective",
    "research_method",
    "experimental_design",
    "main_results",
    "contributions",
    "limitations",
    "future_work",
    "overall_summary",
]

REQUIRED_LIST_FIELDS = [
    "not_stated",
]


def validate_reading_report(report):
    """
    校验模型返回的阅读报告结构。

    这里只检查字段完整性和类型，
    不代表已经验证报告内容的事实准确性。
    """

    if not isinstance(report, dict):
        raise ReadingReportError("阅读报告必须是 JSON 对象。")

    for field in REQUIRED_STRING_FIELDS:
        if field not in report:
            raise ReadingReportError(
                f"阅读报告缺少必要字段：{field}"
            )

        if not isinstance(report[field], str):
            raise ReadingReportError(
                f"字段 {field} 必须是字符串。"
            )

        if not report[field].strip():
            raise ReadingReportError(
                f"字段 {field} 不能为空。"
            )

    for field in REQUIRED_LIST_FIELDS:
        if field not in report:
            raise ReadingReportError(
                f"阅读报告缺少必要字段：{field}"
            )

        if not isinstance(report[field], list):
            raise ReadingReportError(
                f"字段 {field} 必须是列表。"
            )

        if not all(isinstance(item, str) for item in report[field]):
            raise ReadingReportError(
                f"字段 {field} 中的每一项必须是字符串。"
            )

    return report


def generate_reading_report(paper_text, title=None):
    """
    生成论文智能阅读报告。

    参数：
        paper_text: 论文正文
        title: 论文标题，可选

    返回：
        包含结构化报告和模型调用信息的字典
    """

    if not isinstance(paper_text, str) or not paper_text.strip():
        raise ReadingReportError("论文正文不能为空。")

    if title is not None and not isinstance(title, str):
        raise ReadingReportError("论文标题必须是字符串。")

    try:
        messages = build_literature_reading_messages(
            paper_text=paper_text,
            title=title,
        )

        result = chat_completion_json(
            messages=messages,
            temperature=0.1,
        )

        report = validate_reading_report(result["data"])

    except ReadingReportError:
        raise

    except Exception as error:
        raise ReadingReportError(
            f"论文阅读报告生成失败：{error}"
        ) from error

    return {
        "report": report,
        "model": result["model"],
        "usage": result["usage"],
        "elapsed_ms": result["elapsed_ms"],
        "request_id": result["request_id"],
        "prompt_version": LITERATURE_READING_PROMPT_VERSION,
    }
