from flask import Flask
from sqlalchemy import inspect

from app import create_app
from database.db import db
from models import (
    Paper,
    PaperChunk,
    ReadingReport,
    QARecord,
    Note
)


def init_database(app: Flask) -> None:
    """
    初始化数据库并创建数据表。
    """

    with app.app_context():

        # 根据模型定义创建尚不存在的数据表
        db.create_all()

        # 检查数据库中的实际数据表
        inspector = inspect(db.engine)

        tables = inspector.get_table_names()

        print("数据库初始化完成！")
        print("当前数据表：")

        for table in tables:
            print(f"- {table}")


if __name__ == "__main__":

    app = create_app()

    init_database(app)