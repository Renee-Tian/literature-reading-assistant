
from database.db import db
from models.paper_chunk import PaperChunk


class ChunkRepository:
    """论文文本块的数据访问层。"""

    @staticmethod
    def add_many(paper_id: int, chunks: list[dict]):
        """批量添加文本块。"""

        records = []

        for chunk in chunks:
            record = PaperChunk(
                paper_id=paper_id,
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                page_number=chunk["page_number"],
                token_count=chunk.get("token_count")
            )

            records.append(record)

        db.session.add_all(records)

        return records

    @staticmethod
    def delete_by_paper_id(paper_id: int):
        """删除某篇论文已有的全部文本块。"""

        db.session.query(PaperChunk).filter_by(
            paper_id=paper_id
        ).delete(synchronize_session=False)

    @staticmethod
    def list_by_paper_id(paper_id: int):
        """按照文本块顺序查询某篇论文的文本块。"""

        return (
            PaperChunk.query
            .filter_by(paper_id=paper_id)
            .order_by(PaperChunk.chunk_index.asc())
            .all()
        )

    @staticmethod
    def count_by_paper_id(paper_id: int):
        """统计某篇论文的文本块数量。"""

        return PaperChunk.query.filter_by(
            paper_id=paper_id
        ).count()
