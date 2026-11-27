from flask import Blueprint, current_app, jsonify, render_template
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from database.db import db
from models import Paper, PaperChunk, QARecord, ReadingReport
from services.paper_service import PaperService

# 创建系统蓝图
system_bp = Blueprint("system", __name__)


# 首页页面
@system_bp.route("/", methods=["GET"])
def index():
    """工作台首页，渲染 Dashboard 模板。"""

    return render_template("index.html")


# 健康检查接口
@system_bp.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "ok",
        "service": "Flask Backend",
        "message": "后端服务运行正常"
    })


# MySQL 数据库连接检查接口
@system_bp.route("/api/db-health", methods=["GET"])
def db_health():

    try:
        # 执行 SQL 查询，获取当前数据库名称
        result = db.session.execute(
            text("SELECT DATABASE()")
        ).scalar_one()

        return jsonify({
            "status": "ok",
            "database": result,
            "message": "MySQL 数据库连接成功"
        })

    except SQLAlchemyError:

        # 在服务端记录详细异常
        current_app.logger.exception(
            "MySQL database connection failed"
        )

        return jsonify({
            "status": "error",
            "message": "数据库连接失败，请检查服务端日志"
        }), 503


# 首页统计接口
@system_bp.route("/api/system/stats", methods=["GET"])
def system_stats():
    """
    返回首页所需的真实统计数据。

    所有数字均来自 MySQL 计数或 ChromaDB 记录数，
    不做任何推断或补足。
    """

    try:
        paper_total = db.session.scalar(
            select(func.count()).select_from(Paper)
        ) or 0

        status_rows = db.session.execute(
            select(Paper.status, func.count(Paper.id))
            .group_by(Paper.status)
        ).all()

        paper_status = {
            (status or "unknown"): count
            for status, count in status_rows
        }

        chunk_total = db.session.scalar(
            select(func.count()).select_from(PaperChunk)
        ) or 0

        qa_record_total = db.session.scalar(
            select(func.count()).select_from(QARecord)
        ) or 0

        reading_report_total = db.session.scalar(
            select(func.count()).select_from(ReadingReport)
        ) or 0

        recent_papers = PaperService().list_papers(5)

    except SQLAlchemyError:

        current_app.logger.exception(
            "System statistics query failed"
        )

        return jsonify({
            "status": "error",
            "message": "统计信息查询失败，请检查数据库连接"
        }), 503

    except Exception:

        current_app.logger.exception(
            "Unexpected system statistics error"
        )

        return jsonify({
            "status": "error",
            "message": "统计信息服务暂时不可用，请检查服务端日志"
        }), 500

    # 向量库统计独立处理，避免 ChromaDB 异常导致整个接口失败
    vector_total = None
    vector_error = None

    try:
        from rag.vector_store import vector_store

        vector_total = vector_store.count()

    except Exception:

        current_app.logger.exception(
            "Vector store statistics failed"
        )

        vector_error = "向量库统计不可用"

    return jsonify({
        "status": "success",
        "data": {
            "paper_total": paper_total,
            "paper_status": paper_status,
            "chunk_total": chunk_total,
            "vector_total": vector_total,
            "vector_error": vector_error,
            "qa_record_total": qa_record_total,
            "reading_report_total": reading_report_total,
            "recent_papers": recent_papers
        }
    })
