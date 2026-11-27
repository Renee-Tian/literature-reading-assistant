from services.qa_service import (
    QAServiceError,
    answer_question,
)


class QAAgentError(Exception):
    """QA Agent 异常。"""
    pass


def get_single_paper_id(state):
    """读取并校验当前 Agent 处理的论文 ID。"""

    paper_ids = state.get("paper_ids") or []

    if not isinstance(paper_ids, list):
        raise QAAgentError("paper_ids 必须是列表。")

    if len(paper_ids) != 1:
        raise QAAgentError(
            "QA Agent 当前只支持一篇论文，请提供一个 paper_id。"
        )

    paper_id = paper_ids[0]

    if (
        not isinstance(paper_id, int)
        or isinstance(paper_id, bool)
        or paper_id <= 0
    ):
        raise QAAgentError("paper_id 必须是正整数。")

    return paper_id


def qa_agent(state):
    """
    QA Agent。

    负责：
    1. 读取用户问题和论文 ID。
    2. 调用 qa_service 完成 Dense + Sparse + RRF 检索。
    3. 基于原文证据生成回答。
    4. 返回答案、引用、证据和检索信息。
    """

    user_query = state.get("user_query", "").strip()

    if not user_query:
        raise QAAgentError("用户问题不能为空。")

    resolved_query = (
        state.get("resolved_query") or user_query
    ).strip()

    paper_id = get_single_paper_id(state)

    try:
        qa_result = answer_question(
            question=resolved_query,
            paper_id=paper_id,
            top_k=state.get("top_k", 5),
            save_history=False,
        )

    except QAServiceError as error:
        raise QAAgentError(
            f"QA Agent 执行失败：{error}"
        ) from error

    return {
        "qa_result": qa_result
    }
