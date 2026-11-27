from flask import Blueprint, current_app, jsonify, request

from services.agent_service import (
    AgentServiceError,
    AgentWorkflowError,
    agent_service,
)


agent_bp = Blueprint("agent", __name__)


def success_response(data, message=None, status_code=200):
    """构造统一成功响应。"""

    payload = {
        "status": "success",
        "data": data,
    }

    if message:
        payload["message"] = message

    return jsonify(payload), status_code


def error_response(message, status_code):
    """构造统一错误响应。"""

    return jsonify({
        "status": "error",
        "message": message,
    }), status_code


@agent_bp.route("/api/agent/ask", methods=["POST"])
def ask_agent_endpoint():
    """
    触发 Supervisor 与三个专业 Agent 的多智能体工作流。

    请求体：
    {
        "question": "用户问题",
        "paper_id": 6,
        "thread_id": "会话 ID，可选",
        "top_k": 5,
        "reading_max_chars": 10000,
        "research_top_k": 8
    }
    """

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "请求数据格式错误，请提交 JSON 对象",
            400,
        )

    question = data.get("question")
    paper_id = data.get("paper_id")
    thread_id = data.get("thread_id")
    top_k = data.get("top_k", 5)
    reading_max_chars = data.get("reading_max_chars")
    research_top_k = data.get("research_top_k", 8)

    try:
        result = agent_service.ask(
            question=question,
            paper_id=paper_id,
            thread_id=thread_id,
            top_k=top_k,
            reading_max_chars=reading_max_chars,
            research_top_k=research_top_k,
        )

    except AgentWorkflowError as error:
        current_app.logger.exception(
            "Agent workflow request failed"
        )

        return error_response(
            str(error),
            502,
        )

    except AgentServiceError as error:
        return error_response(
            str(error),
            400,
        )

    except Exception:
        current_app.logger.exception(
            "Unexpected agent route error"
        )

        return error_response(
            "Agent 服务暂时不可用，请检查服务日志",
            500,
        )

    return success_response(
        data=result,
        message="Agent 工作流执行成功",
    )
