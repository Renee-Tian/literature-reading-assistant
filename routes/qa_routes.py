from flask import Blueprint, current_app, jsonify, request

from services.qa_service import (
    QAServiceError,
    answer_question,
    list_qa_history,
)


qa_bp = Blueprint("qa", __name__)


def success_response(data, message=None, status_code=200):
    """构造统一成功响应。"""

    payload = {
        "status": "success",
        "data": data
    }

    if message:
        payload["message"] = message

    return jsonify(payload), status_code


def error_response(message, status_code):
    """构造统一错误响应。"""

    return jsonify({
        "status": "error",
        "message": message
    }), status_code


@qa_bp.route("/api/papers/<int:paper_id>/qa", methods=["POST"])
def ask_question(paper_id):
    """
    对指定论文进行 Dense + Sparse + RRF RAG 问答。

    QA 检索、LLM 调用和问答记录保存均由 qa_service 协调完成，
    本路由只负责 HTTP 参数解析和响应封装。
    """

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response(
            "请求数据格式错误，请提交 JSON 对象",
            400
        )

    question = data.get("question")

    if not isinstance(question, str) or not question.strip():
        return error_response(
            "问题不能为空",
            400
        )

    top_k = data.get("top_k", 5)

    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
        or top_k > 20
    ):
        return error_response(
            "top_k 必须是 1 到 20 之间的整数",
            400
        )

    save_history = data.get("save_history", True)

    if not isinstance(save_history, bool):
        return error_response(
            "save_history 必须是布尔值",
            400
        )

    try:
        result = answer_question(
            paper_id=paper_id,
            question=question.strip(),
            top_k=top_k,
            save_history=save_history
        )

    except QAServiceError as error:
        return error_response(
            str(error),
            400
        )

    except Exception:
        current_app.logger.exception("QA request failed")

        return error_response(
            "问答服务暂时不可用，请检查服务日志",
            500
        )

    return success_response(
        data=result,
        message="问答成功"
    )


@qa_bp.route(
    "/api/papers/<int:paper_id>/qa/history",
    methods=["GET"]
)
def get_qa_history(paper_id):
    """获取指定论文的问答历史。"""

    limit = request.args.get(
        "limit",
        default=20,
        type=int
    )

    if limit is None or limit <= 0 or limit > 100:
        return error_response(
            "limit 必须是 1 到 100 之间的整数",
            400
        )

    try:
        records = list_qa_history(
            paper_id=paper_id,
            limit=limit
        )

    except QAServiceError as error:
        return error_response(
            str(error),
            400
        )

    except Exception:
        current_app.logger.exception(
            "QA history query failed"
        )

        return error_response(
            "问答历史查询失败，请检查服务日志",
            500
        )

    return success_response(
        data={
            "total": len(records),
            "items": records
        },
        message="问答历史查询成功"
    )
