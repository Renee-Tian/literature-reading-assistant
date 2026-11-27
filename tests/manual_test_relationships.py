from uuid import uuid4

from app import create_app
from database.db import db
from models import (
    Paper,
    PaperChunk,
    ReadingReport,
    QARecord,
    Note
)


def test_relationships():

    app = create_app()

    with app.app_context():

        filename = f"relationship_{uuid4().hex}.pdf"

        # 创建一篇测试论文
        paper = Paper(
            title="SQLAlchemy 关联关系测试",
            authors="Test Author",
            original_filename="test.pdf",
            stored_filename=filename,
            file_path=f"storage/uploads/{filename}",
            status="uploaded"
        )

        # 为论文添加文本块
        paper.paper_chunks.append(
            PaperChunk(
                chunk_index=0,
                content="这是第一段测试文本。",
                page_number=1,
                section_title="Abstract"
            )
        )

        # 添加阅读报告
        paper.reading_reports.append(
            ReadingReport(
                report_type="comprehensive",
                report_data={
                    "research_background": "研究背景测试",
                    "research_method": "研究方法测试",
                    "main_findings": "研究结论测试"
                },
                model_name="test-model"
            )
        )

        # 添加问答记录
        paper.qa_records.append(
            QARecord(
                question="这篇论文研究什么？",
                answer="这是一个测试回答。",
                citations=[
                    {
                        "chunk_id": 1,
                        "page_number": 1,
                        "quote": "测试证据"
                    }
                ]
            )
        )

        # 添加阅读笔记
        paper.notes.append(
            Note(
                title="测试笔记",
                content="这是我的第一条论文阅读笔记。",
                page_number=1
            )
        )

        try:
            # 保存论文及其关联对象
            db.session.add(paper)
            db.session.commit()

            paper_id = paper.id

            print(f"论文创建成功，ID：{paper_id}")

            # 重新查询论文
            saved_paper = db.session.get(
                Paper,
                paper_id
            )

            print("关联关系查询：")
            print("文本块数量：", len(saved_paper.paper_chunks))
            print("阅读报告数量：", len(saved_paper.reading_reports))
            print("问答记录数量：", len(saved_paper.qa_records))
            print("阅读笔记数量：", len(saved_paper.notes))

            # 删除测试论文
            db.session.delete(saved_paper)
            db.session.commit()

            print("测试论文删除成功！")

            # 检查关联数据是否被一起删除
            remaining_chunks = (
                db.session.query(PaperChunk)
                .filter_by(paper_id=paper_id)
                .count()
            )

            print("删除后剩余文本块：", remaining_chunks)

            assert remaining_chunks == 0

            print("关联关系测试全部通过！")

        except Exception:
            db.session.rollback()
            raise

        finally:
            db.session.remove()


if __name__ == "__main__":
    test_relationships()