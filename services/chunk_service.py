
from database.db import db
from models import Paper
from repositories.chunk_repository import ChunkRepository


class ChunkService:
    """论文文本块业务服务。"""

    @staticmethod
    def replace_chunks(paper_id: int, chunks: list[dict]) -> int:
        """
        替换指定论文的全部文本块。

        成功返回保存的文本块数量。
        失败时回滚数据库事务。
        """

        # 1. 检查论文是否存在
        paper = db.session.get(Paper, paper_id)

        if paper is None:
            raise ValueError(f"论文不存在，paper_id={paper_id}")

        # 2. 检查输入数据
        if not isinstance(chunks, list) or not chunks:
            raise ValueError("chunks 必须是非空列表。")

        seen_indexes = set()

        for chunk in chunks:
            if not isinstance(chunk, dict):
                raise ValueError("Chunk 数据格式错误。")

            chunk_index = chunk.get("chunk_index")
            page_number = chunk.get("page_number")
            content = chunk.get("content")

            if (
                not isinstance(chunk_index, int)
                or isinstance(chunk_index, bool)
                or chunk_index < 0
            ):
                raise ValueError("chunk_index 必须是非负整数。")

            if chunk_index in seen_indexes:
                raise ValueError("存在重复的 chunk_index。")

            seen_indexes.add(chunk_index)

            if (
                not isinstance(page_number, int)
                or isinstance(page_number, bool)
                or page_number < 1
            ):
                raise ValueError("page_number 必须是正整数。")

            if not isinstance(content, str) or not content.strip():
                raise ValueError("Chunk 内容不能为空。")

        # 3. 删除旧数据并保存新数据
        try:
            ChunkRepository.delete_by_paper_id(paper_id)

            ChunkRepository.add_many(paper_id, chunks)

            # 4. 提交事务
            db.session.commit()

            return len(chunks)

        except Exception:
            # 5. 出错时回滚
            db.session.rollback()
            raise
