
from database.db import db
from models import Paper, QARecord


class QARecordServiceError(Exception):
    """问答记录服务异常。"""


def save_qa_record(paper_id, question, answer, citations):
    """保存问答记录到 MySQL。"""

    paper = db.session.get(Paper, paper_id)

    if paper is None:
        raise QARecordServiceError("指定的论文不存在")

    try:
        record = QARecord(
            paper_id=paper_id,
            question=question,
            answer=answer,
            citations=citations
        )

        db.session.add(record)
        db.session.commit()

        return record

    except Exception as exc:
        db.session.rollback()
        raise QARecordServiceError(
            f"保存问答记录失败：{exc}"
        ) from exc
