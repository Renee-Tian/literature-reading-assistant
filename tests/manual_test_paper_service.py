from uuid import uuid4

from app import create_app
from services.paper_service import (
    PaperService,
    PaperNotFoundError
)


def test_paper_service():

    app = create_app()

    with app.app_context():

        service = PaperService()

        filename = f"service_test_{uuid4().hex}.pdf"
        paper_id = None

        try:
            # 1. Create：通过 Service 新增论文
            created = service.create_paper({
                "title": "Service Layer 测试论文",
                "authors": "Test Author",
                "abstract": "这是一条业务服务层测试数据。",
                "publication_year": 2025,
                "original_filename": "service_test.pdf",
                "stored_filename": filename,
                "file_path": f"storage/uploads/{filename}"
            })

            paper_id = created["id"]

            print("新增成功：", created["title"])

            # 2. Read：查询论文
            found = service.get_paper(paper_id)

            print("查询成功：", found["title"])

            # 3. List：获取论文列表
            papers = service.list_papers()

            print("论文列表数量：", len(papers))

            # 4. Update：更新论文标题
            updated = service.update_paper(
                paper_id,
                {
                    "title": "Service Layer 更新后的测试论文"
                }
            )

            print("更新成功：", updated["title"])

            assert updated["title"] == (
                "Service Layer 更新后的测试论文"
            )

            # 5. Delete：删除测试论文
            service.delete_paper(paper_id)

            paper_id = None

            print("删除成功！")

            # 6. 验证删除结果
            try:
                service.get_paper(created["id"])
                raise AssertionError("论文删除后仍然可以查询！")

            except PaperNotFoundError:
                print("删除验证成功：论文记录已不存在。")

            print("PaperService CRUD 测试全部通过！")

        finally:
            # 如果中途异常，尽量清理测试记录
            if paper_id is not None:
                try:
                    service.delete_paper(paper_id)
                except PaperNotFoundError:
                    pass


if __name__ == "__main__":
    test_paper_service()