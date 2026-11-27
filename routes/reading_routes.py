from flask import Blueprint, current_app, jsonify

from services.paper_service import (
    PaperNotFoundError,
    PaperService,
    PaperValidationError,
)

from services.reading_report_service import (
    ReadingReportServiceError,
    get_latest_reading_report,
)


# 阅读报告蓝图：只读接口，不触发生成
reading_bp = Blueprint("reading", __name__)

paper_service = PaperService()


@reading_bp.route(
    "/api/papers/<int:paper_id>/reading-report/latest",
    methods=["GET"]
)
def latest_reading_report(paper_id):
    """
    读取指定论文最新的阅读报告。

    报告中不存在时返回 data=None，
    由前端展示空状态，不生成任何替代内容。
    """

    try:
        paper_service.get_paper(paper_id)

    except PaperNotFoundError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 404

    except PaperValidationError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    try:
        report = get_latest_reading_report(paper_id)

    except ReadingReportServiceError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    except Exception:

        current_app.logger.exception(
            "Latest reading report query failed | paper_id=%s",
            paper_id
        )

        return jsonify({
            "status": "error",
            "message": "阅读报告查询失败，请检查服务端日志"
        }), 500

    return jsonify({
        "status": "success",
        "message": "暂无阅读报告" if report is None else "阅读报告查询成功",
        "data": report
    }), 200
