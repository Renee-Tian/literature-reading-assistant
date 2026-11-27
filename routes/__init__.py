from flask import Flask


def register_routes(app: Flask) -> None:
    """
    统一注册所有路由蓝图。
    """

    from .system_routes import system_bp
    from .page_routes import page_bp
    from .paper_routes import paper_bp
    from .reading_routes import reading_bp
    from .qa_routes import qa_bp
    from .agent_routes import agent_bp

    app.register_blueprint(system_bp)
    app.register_blueprint(page_bp)
    app.register_blueprint(paper_bp)
    app.register_blueprint(reading_bp)
    app.register_blueprint(qa_bp)
    app.register_blueprint(agent_bp)
