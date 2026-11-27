from uuid import uuid4

from app import create_app
from database.db import db
from models import Paper


def test_paper_crud():

    app = create_app()

    with app.app_context():

        # 生成唯一的测试文件名
        filename = f"test_{uuid4().hex}.pdf"

        paper = Paper(
            title="SQLAlchemy CRUD 测试论文",
            authors="Test Author",
            original_filename="test_paper.pdf",
            stored_filename=filename,
            file_path=f"storage/uploads/{filename}",
            status="uploaded"
        )

        try:
            # 1. Create：新增论文
            db.session.add(paper)
            db.session.commit()

            paper_id = paper.id

            print(f"新增成功，论文 ID：{paper_id}")

            # 2. Read：查询论文
            saved_paper = db.session.get(
                Paper,
                paper_id
            )

            print(f"查询成功，论文标题：{saved_paper.title}")

            # 3. Update：修改论文标题
            saved_paper.title = "已更新的测试论文"

            db.session.commit()

            print(f"更新成功，最新标题：{saved_paper.title}")

            # 4. Delete：删除论文
            db.session.delete(saved_paper)

            db.session.commit()

            print("删除成功！")

        except Exception:
            db.session.rollback()
            raise

        finally:
            db.session.remove()


if __name__ == "__main__":
    test_paper_crud()