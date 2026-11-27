
import sys

from app import create_app
from database.db import db
from models import Paper
from document.pdf_parser import extract_pdf_text
from document.chunker import build_chunks
from services.chunk_service import ChunkService
from repositories.chunk_repository import ChunkRepository


def main():

    if len(sys.argv) < 3:
        print(
            "使用方法：python -m tests.manual_test_chunk_persistence "
            "论文ID PDF文件路径"
        )
        return

    paper_id = int(sys.argv[1])
    pdf_path = sys.argv[2]

    app = create_app()

    with app.app_context():

        paper = db.session.get(Paper, paper_id)

        if paper is None:
            print(f"数据库中不存在论文 ID：{paper_id}")
            return

        # 第一步：提取 PDF 文本
        parsed_pdf = extract_pdf_text(pdf_path)

        # 第二步：生成文本块
        chunks = build_chunks(parsed_pdf)

        if not chunks:
            print("没有生成文本块，取消数据库保存。")
            return

        # 第三步：保存到 MySQL
        saved_count = ChunkService.replace_chunks(
            paper_id,
            chunks
        )

        # 第四步：重新从数据库读取
        saved_chunks = ChunkRepository.list_by_paper_id(
            paper_id
        )

        print("=" * 50)
        print("论文标题：", paper.title)
        print("论文 ID：", paper_id)
        print("生成 Chunk 数量：", len(chunks))
        print("保存 Chunk 数量：", saved_count)
        print("数据库查询数量：", len(saved_chunks))
        print("=" * 50)

        for chunk in saved_chunks[:3]:
            print("Chunk ID：", chunk.id)
            print("Chunk 序号：", chunk.chunk_index)
            print("原文页码：", chunk.page_number)
            print("文本预览：", chunk.content[:100])
            print("-" * 50)

        if len(saved_chunks) == saved_count:
            print("测试通过：文本块已保存并成功读取。")
        else:
            print("测试异常：生成数量与数据库查询数量不一致。")


if __name__ == "__main__":
    main()
