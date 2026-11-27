from uuid import uuid4

from flask import has_app_context

from agent.workflow import get_thread_state, run_workflow

from utils.trace import finish_trace, start_trace


class AgentServiceError(Exception):
    """多智能体服务参数或业务异常。"""
    pass


class AgentWorkflowError(AgentServiceError):
    """多智能体工作流执行异常。"""
    pass


def validate_question(question):
    """校验用户问题。"""

    if not isinstance(question, str) or not question.strip():
        raise AgentServiceError("用户问题不能为空。")

    return question.strip()


def validate_paper_id(paper_id):
    """校验单篇论文 ID。"""

    if (
        not isinstance(paper_id, int)
        or isinstance(paper_id, bool)
        or paper_id <= 0
    ):
        raise AgentServiceError("paper_id 必须是正整数。")

    return paper_id


def validate_top_k(top_k, field_name="top_k"):
    """校验检索数量参数。"""

    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
        or top_k > 20
    ):
        raise AgentServiceError(
            f"{field_name} 必须是 1 到 20 之间的整数。"
        )

    return top_k


def validate_reading_max_chars(reading_max_chars):
    """校验 Reading Agent 单批字符数。"""

    if reading_max_chars is None:
        return None

    if (
        not isinstance(reading_max_chars, int)
        or isinstance(reading_max_chars, bool)
        or reading_max_chars <= 0
    ):
        raise AgentServiceError(
            "reading_max_chars 必须是正整数。"
        )

    return reading_max_chars


def validate_thread_id(thread_id):
    """校验会话 ID；未提供时自动创建新会话。"""

    if thread_id is None:
        return str(uuid4())

    if (
        not isinstance(thread_id, str)
        or not thread_id.strip()
    ):
        raise AgentServiceError(
            "thread_id 必须是非空字符串。"
        )

    thread_id = thread_id.strip()

    if len(thread_id) > 128:
        raise AgentServiceError(
            "thread_id 长度不能超过 128 个字符。"
        )

    return thread_id


def serialize_workflow_state(state, thread_id, request_id):
    """把 LangGraph State 转换为前端可消费的数据。"""

    if not isinstance(state, dict):
        raise AgentWorkflowError(
            "多智能体工作流返回的 State 格式错误。"
        )

    final_answer = state.get("final_answer")

    if (
        not isinstance(final_answer, str)
        or not final_answer.strip()
    ):
        raise AgentWorkflowError(
            "多智能体工作流没有生成最终回答。"
        )

    return {
        "request_id": request_id,
        "thread_id": thread_id,
        "question": state.get("user_query"),
        "resolved_query": state.get(
            "resolved_query",
            state.get("user_query"),
        ),
        "paper_ids": state.get("paper_ids", []),
        "task_plan": state.get("task_plan"),
        "next_agents": state.get("next_agents", []),
        "completed_agents": state.get(
            "completed_agents",
            []
        ),
        "final_answer": final_answer.strip(),
        "reading_result": state.get("reading_result"),
        "qa_result": state.get("qa_result"),
        "research_result": state.get("research_result"),
        "error": state.get("error"),
    }


def ask_agent(
    question,
    paper_id,
    thread_id=None,
    top_k=5,
    reading_max_chars=None,
    research_top_k=8,
):
    """
    调用多智能体 Workflow 完成一次完整问答。

    本函数只负责参数校验、Workflow 调用和结果序列化，
    不重新实现 Supervisor 或专业 Agent 的内部逻辑。
    """

    question = validate_question(question)
    paper_id = validate_paper_id(paper_id)
    thread_id = validate_thread_id(thread_id)
    top_k = validate_top_k(top_k)
    research_top_k = validate_top_k(
        research_top_k,
        "research_top_k",
    )
    reading_max_chars = validate_reading_max_chars(
        reading_max_chars
    )

    if not has_app_context():
        raise AgentWorkflowError(
            "AgentService 必须在 Flask 应用上下文中调用。"
        )

    trace = start_trace(
        question=question,
        thread_id=thread_id,
        paper_ids=[paper_id],
    )

    state = None

    try:
        snapshot = get_thread_state(thread_id)

        if snapshot.values:
            previous_paper_ids = snapshot.values.get(
                "paper_ids"
            )

            if (
                previous_paper_ids
                and previous_paper_ids != [paper_id]
            ):
                raise AgentServiceError(
                    "同一 thread_id 不能切换到其他论文。"
                )

        state = run_workflow(
            user_query=question,
            paper_ids=[paper_id],
            thread_id=thread_id,
            top_k=top_k,
            reading_max_chars=reading_max_chars,
            research_top_k=research_top_k,
        )

        result = serialize_workflow_state(
            state,
            thread_id=thread_id,
            request_id=trace.request_id,
        )

    except AgentServiceError as error:
        finish_trace(
            status="failed",
            error=error,
            final_state=state,
        )
        raise

    except Exception as error:
        wrapped_error = AgentWorkflowError(
            f"多智能体工作流执行失败：{error}"
        )

        finish_trace(
            status="failed",
            error=wrapped_error,
            final_state=state,
        )

        raise wrapped_error from error

    finish_trace(
        status="success",
        final_state=state,
    )

    return result


class AgentService:
    """多智能体业务服务类入口。"""

    @staticmethod
    def ask(
        question,
        paper_id,
        thread_id=None,
        top_k=5,
        reading_max_chars=None,
        research_top_k=8,
    ):
        return ask_agent(
            question=question,
            paper_id=paper_id,
            thread_id=thread_id,
            top_k=top_k,
            reading_max_chars=reading_max_chars,
            research_top_k=research_top_k,
        )


agent_service = AgentService()
