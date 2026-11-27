
from models import ReadingReport


class ReadingReportRepository:
    """阅读报告的数据访问层。"""

    @staticmethod
    def add(report):
        """添加一条阅读报告记录。"""
        from database.db import db

        db.session.add(report)
        return report

    @staticmethod
    def get_by_id(report_id):
        """根据报告 ID 查询报告。"""
        return ReadingReport.query.filter_by(
            id=report_id
        ).first()

    @staticmethod
    def list_by_paper_id(paper_id):
        """查询某篇论文的全部阅读报告，按时间倒序排列。"""
        return (
            ReadingReport.query
            .filter_by(paper_id=paper_id)
            .order_by(
                ReadingReport.created_at.desc(),
                ReadingReport.id.desc()
            )
            .all()
        )

    @staticmethod
    def get_latest_by_paper_id(paper_id):
        """查询某篇论文最新的一份阅读报告。"""
        return (
            ReadingReport.query
            .filter_by(paper_id=paper_id)
            .order_by(
                ReadingReport.created_at.desc(),
                ReadingReport.id.desc()
            )
            .first()
        )

    @staticmethod
    def delete(report):
        """删除指定阅读报告对象。"""
        from database.db import db

        db.session.delete(report)
