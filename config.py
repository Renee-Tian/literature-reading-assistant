import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 加载 .env 文件
load_dotenv(BASE_DIR / ".env")


def create_database_url():
    """
    创建 MySQL 数据库连接地址。
    """

    # 检查必要的环境变量
    required = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD"
    ]

    missing = [
        key for key in required
        if not os.getenv(key)
    ]

    if missing:
        raise RuntimeError(
            f"缺少数据库配置：{', '.join(missing)}"
        )

    # 创建数据库连接 URL
    return URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        database=os.getenv("DB_NAME"),
        query={"charset": "utf8mb4"}
    )


class Config:

    # Flask 密钥
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-only-change-this"
    )

    # PDF 上传大小限制：30 MB
    MAX_CONTENT_LENGTH = 30 * 1024 * 1024

    # PDF 保存路径
    UPLOAD_FOLDER = str(
        BASE_DIR / "storage" / "uploads"
    )

    # SQLAlchemy 数据库连接
    SQLALCHEMY_DATABASE_URI = create_database_url()

    # 关闭不必要的修改追踪
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 数据库连接池配置
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600
    }