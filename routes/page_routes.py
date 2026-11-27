from flask import Blueprint, render_template


# 页面蓝图：只负责返回 Jinja2 模板，不承载业务逻辑
page_bp = Blueprint("page", __name__)


@page_bp.route("/papers", methods=["GET"])
def papers():
    """论文管理页面。"""
    return render_template("papers.html")


@page_bp.route("/papers/<int:paper_id>/reader", methods=["GET"])
def reader(paper_id):
    """智能阅读页面。"""
    return render_template("reader.html", paper_id=paper_id)


@page_bp.route("/chat", methods=["GET"])
def chat():
    """智能问答页面。"""
    return render_template("chat.html")


@page_bp.route("/research", methods=["GET"])
def research():
    """研究分析页面。"""
    return render_template("research.html")


@page_bp.route("/agents", methods=["GET"])
def agents():
    """多智能体协作页面。"""
    return render_template("agents.html")
