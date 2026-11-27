
from pathlib import Path

from database.db import db
from models import Paper

from document.pdf_parser import parse_pdf
from document.chunker import build_chunks
from services.chunk_service import ChunkService


class DocumentProcessingError(Exception):
    """论文文档处理异常。"""
    pass


class DocumentProcessingService:
    """论文文档处理编排服务。"""

    @staticmethod
    def process_paper(paper_id: int) -> dict:
        """
        完整处理一篇论文：

        1. 检查论文记录
        2. 更新处理状态
        3. 解析 PDF
        4. 生成文本 Chunk
        5. 保存 Chunk 到 MySQL
        6. 更新最终处理状态
        """

        # 1. 检查论文是否存在
        paper = db.session.get(Paper, paper_id)

        if paper is None:
            raise ValueError(f"论文不存在，paper_id={paper_id}")

        # 2. 更新处理状态
        paper.status = "processing"
        paper.error_message = None
        db.session.commit()

        try:
            # 3. 检查 PDF 文件
            pdf_path = Path(paper.file_path)

            if not pdf_path.exists():
                raise FileNotFoundError(
                    f"论文 PDF 文件不存在：{pdf_path}"
                )

            # 4. 解析 PDF
            parsed_pdf = parse_pdf(pdf_path)

            if not parsed_pdf["has_extractable_text"]:
                raise DocumentProcessingError(
                    "PDF 没有提取到有效文本，无法继续处理。"
                )

            # 5. 生成文本 Chunk
            chunks = build_chunks(parsed_pdf)

            if not chunks:
                raise DocumentProcessingError(
                    "PDF 文本分块结果为空。"
                )

            # 6. 保存 Chunk 到 MySQL
            saved_count = ChunkService.replace_chunks(
                paper_id=paper_id,
                chunks=chunks
            )

            # 7. 更新论文处理状态
            paper = db.session.get(Paper, paper_id)
            paper.status = "completed"
            paper.error_message = None
            db.session.commit()

            # 8. 返回处理结果
            return {
                "paper_id": paper_id,
                "title": paper.title,
                "status": paper.status,
                "page_count": parsed_pdf["page_count"],
                "total_characters": parsed_pdf["total_characters"],
                "chunk_count": saved_count,
                "layout_statistics": parsed_pdf[
                    "layout_statistics"
                ]
            }

        except Exception as exc:

            # 9. 回滚当前未提交的数据库事务
            db.session.rollback()

            # 10. 记录处理失败状态
            try:
                paper = db.session.get(Paper, paper_id)

                if paper is not None:
                    paper.status = "failed"
                    paper.error_message = str(exc)[:5000]
                    db.session.commit()

            except Exception:
                db.session.rollback()

            raise DocumentProcessingError(
                f"论文处理失败：{exc}"
            ) from exc
