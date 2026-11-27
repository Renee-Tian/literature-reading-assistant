from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from database.db import db
from models import Paper


class PaperRepository:
    """
    论文数据访问层。

    只负责与数据库交互，不处理业务规则。
    """

    def add(self, paper: Paper) -> Paper:
        """新增论文记录。"""

        try:
            db.session.add(paper)
            db.session.commit()
            db.session.refresh(paper)

            return paper

        except SQLAlchemyError:
            db.session.rollback()
            raise

    def get_by_id(self, paper_id: int) -> Paper | None:
        """根据主键查询论文。"""

        return db.session.get(Paper, paper_id)

    def list_all(self, limit: int = 50) -> list[Paper]:
        """获取论文列表。"""

        statement = (
            select(Paper)
            .order_by(Paper.created_at.desc())
            .limit(limit)
        )

        return list(db.session.scalars(statement).all())

    def save(self, paper: Paper) -> Paper:
        """保存论文修改。"""

        try:
            db.session.commit()
            db.session.refresh(paper)

            return paper

        except SQLAlchemyError:
            db.session.rollback()
            raise

    def delete(self, paper: Paper) -> None:
        """删除论文记录。"""

        try:
            db.session.delete(paper)
            db.session.commit()

        except SQLAlchemyError:
            db.session.rollback()
            raise