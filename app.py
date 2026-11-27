from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from database.db import db
from routes import register_routes
from utils.logging_config import configure_logging


def create_app() -> Flask:
    """
    创建 Flask 应用。
    """

    app = Flask(__name__)

    # 初始化日志系统
    configure_logging(app)

    # 加载项目配置
    app.config.from_object(Config)

    # 初始化数据库扩展
    db.init_app(app)

    # 注册路由蓝图
    register_routes(app)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(error):
        return jsonify({
            "status": "error",
            "message": "上传文件超过30 MiB限制。"
        }), 413

    return app


if __name__ == "__main__":

    app = create_app()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
