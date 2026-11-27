from datetime import datetime

from repositories.paper_repository import PaperRepository
from models import Paper

from pathlib import Path
from uuid import uuid4

from flask import current_app

class PaperNotFoundError(Exception):
    """论文不存在时抛出的异常。"""


class PaperValidationError(Exception):
    """论文数据不符合业务规则时抛出的异常。"""


class PaperService:
    """
    论文业务服务层。

    负责业务校验、业务逻辑和数据操作协调。
    """

    def __init__(self, repository=None):
        self.repository = repository or PaperRepository()

    @staticmethod
    def _serialize(paper: Paper) -> dict:
        """将 Paper 对象转换为可返回的字典。"""

        return {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.authors,
            "abstract": paper.abstract,
            "publication_year": paper.publication_year,
            "original_filename": paper.original_filename,
            "stored_filename": paper.stored_filename,
            "status": paper.status,
            "created_at": (
                paper.created_at.isoformat()
                if paper.created_at else None
            ),
            "updated_at": (
                paper.updated_at.isoformat()
                if paper.updated_at else None
            )
        }

    @staticmethod
    def _validate_year(year):
        """检查论文发表年份。"""

        if year is None:
            return None

        try:
            year = int(year)
        except (TypeError, ValueError):
            raise PaperValidationError("发表年份必须是整数。")

        if not 1800 <= year <= datetime.now().year + 1:
            raise PaperValidationError("发表年份不在合理范围内。")

        return year

    def create_paper(self, data: dict) -> dict:
        """创建论文记录。"""

        if not isinstance(data, dict):
            raise PaperValidationError("论文数据格式错误。")

        title = data.get("title")

        if not isinstance(title, str) or not title.strip():
            raise PaperValidationError("论文标题不能为空。")

        if len(title.strip()) > 500:
            raise PaperValidationError("论文标题不能超过500个字符。")

        original_filename = data.get("original_filename")
        stored_filename = data.get("stored_filename")
        file_path = data.get("file_path")

        for name, value in [
            ("原始文件名", original_filename),
            ("存储文件名", stored_filename),
            ("文件路径", file_path)
        ]:
            if not isinstance(value, str) or not value.strip():
                raise PaperValidationError(f"{name}不能为空。")

        if len(original_filename) > 255:
            raise PaperValidationError("原始文件名过长。")

        if len(stored_filename) > 255:
            raise PaperValidationError("存储文件名过长。")

        if len(file_path) > 1000:
            raise PaperValidationError("文件路径过长。")

        paper = Paper(
            title=title.strip(),
            authors=data.get("authors"),
            abstract=data.get("abstract"),
            publication_year=self._validate_year(
                data.get("publication_year")
            ),
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            status="uploaded"
        )

        saved_paper = self.repository.add(paper)

        return self._serialize(saved_paper)

    def upload_paper(self, uploaded_file) -> dict:
    

        # 1. 检查文件是否存在
        if uploaded_file is None:
            raise PaperValidationError("请上传 PDF 文件。")

        raw_filename = uploaded_file.filename or ""

        if not raw_filename.strip():
            raise PaperValidationError("文件名不能为空。")

        # 2. 提取文件名，避免保存用户提供的路径
        original_filename = (
            raw_filename.replace("\\", "/")
            .rsplit("/", 1)[-1]
            .strip()
        )

        if not original_filename:
            raise PaperValidationError("文件名无效。")

        # 3. 检查扩展名
        if not original_filename.lower().endswith(".pdf"):
            raise PaperValidationError("仅支持 PDF 文件。")

        if len(original_filename) > 255:
            raise PaperValidationError("文件名过长。")

        # 4. 检查文件大小
        stream = uploaded_file.stream

        try:
            stream.seek(0, 2)
            file_size = stream.tell()
            stream.seek(0)

        except (OSError, AttributeError):
            raise PaperValidationError("无法读取上传文件。")

        if file_size <= 0:
            raise PaperValidationError("不能上传空文件。")

        max_size = current_app.config["MAX_CONTENT_LENGTH"]

        if file_size > max_size:
            raise PaperValidationError("PDF 文件超过大小限制。")

        # 5. 检查 PDF 文件头
        header = stream.read(5)
        stream.seek(0)

        if header != b"%PDF-":
            raise PaperValidationError("文件内容不是有效的 PDF 格式。")

        # 6. 创建安全的文件存储名称
        stored_filename = f"{uuid4().hex}.pdf"

        # 获取真实文件保存目录
        upload_dir = Path(
            current_app.config["UPLOAD_FOLDER"]
        ).resolve()

        upload_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        absolute_path = upload_dir / stored_filename

        # 数据库保存相对路径，方便将来迁移项目
        relative_path = (
            Path("storage") / "uploads" / stored_filename
        ).as_posix()

        try:
            # 7. 保存 PDF 文件
            uploaded_file.save(str(absolute_path))

            # 8. 创建论文数据库记录
            paper = Paper(
                title=Path(original_filename).stem,
                original_filename=original_filename,
                stored_filename=stored_filename,
                file_path=relative_path,
                status="uploaded"
            )

            saved_paper = self.repository.add(paper)

            return self._serialize(saved_paper)

        except Exception:
            # 数据库保存失败时，清理刚刚保存的文件
            if absolute_path.exists():
                absolute_path.unlink(missing_ok=True)

            raise


    def get_paper(self, paper_id: int) -> dict:
        """根据 ID 获取论文。"""

        if paper_id <= 0:
            raise PaperValidationError("论文 ID 必须大于0。")

        paper = self.repository.get_by_id(paper_id)

        if paper is None:
            raise PaperNotFoundError("指定论文不存在。")

        return self._serialize(paper)

    def get_pdf_path(self, paper_id: int) -> Path:
        """
        返回论文 PDF 的绝对路径。

        只允许访问上传目录内的文件，
        避免通过 paper_id 读取任意磁盘路径。
        """

        if paper_id <= 0:
            raise PaperValidationError("论文 ID 必须大于0。")

        paper = self.repository.get_by_id(paper_id)

        if paper is None:
            raise PaperNotFoundError("指定论文不存在。")

        upload_root = Path(
            current_app.config["UPLOAD_FOLDER"]
        ).resolve()

        stored_path = Path(paper.file_path)

        if stored_path.is_absolute():
            raise PaperValidationError("论文文件路径不合法。")

        absolute_path = (
            Path(current_app.root_path) / stored_path
        ).resolve()

        if absolute_path.parent != upload_root:
            raise PaperValidationError(
                "文件路径超出允许的访问范围。"
            )

        if not absolute_path.is_file():
            raise PaperNotFoundError("论文 PDF 文件不存在。")

        return absolute_path

    def list_papers(self, limit: int = 50) -> list[dict]:
        """获取论文列表。"""

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            raise PaperValidationError("查询数量必须是整数。")

        limit = max(1, min(limit, 100))

        papers = self.repository.list_all(limit=limit)

        return [
            self._serialize(paper)
            for paper in papers
        ]

    def update_paper(self, paper_id: int, data: dict) -> dict:
        """更新论文基本信息。"""

        if not isinstance(data, dict) or not data:
            raise PaperValidationError("更新内容不能为空。")

        paper = self.repository.get_by_id(paper_id)

        if paper is None:
            raise PaperNotFoundError("指定论文不存在。")

        # 只允许用户修改这些基本字段
        allowed_fields = {
            "title",
            "authors",
            "abstract",
            "publication_year"
        }

        invalid_fields = set(data.keys()) - allowed_fields

        if invalid_fields:
            raise PaperValidationError(
                f"不允许修改以下字段：{', '.join(invalid_fields)}"
            )

        if "title" in data:
            title = data["title"]

            if not isinstance(title, str) or not title.strip():
                raise PaperValidationError("论文标题不能为空。")

            paper.title = title.strip()

        if "authors" in data:
            paper.authors = data["authors"]

        if "abstract" in data:
            paper.abstract = data["abstract"]

        if "publication_year" in data:
            paper.publication_year = self._validate_year(
                data["publication_year"]
            )

        updated_paper = self.repository.save(paper)

        return self._serialize(updated_paper)

    def delete_paper(self, paper_id: int) -> None:
        """
        删除论文记录及对应 PDF 文件。
        """

        paper = self.repository.get_by_id(paper_id)

        if paper is None:
            raise PaperNotFoundError("指定论文不存在。")

        # 获取允许删除的 PDF 存储目录
        upload_root = Path(
            current_app.config["UPLOAD_FOLDER"]
        ).resolve()

        # 数据库中保存的是相对路径
        stored_path = Path(paper.file_path)

        if stored_path.is_absolute():
            raise PaperValidationError("论文文件路径不合法。")

        # 解析真实文件路径
        absolute_path = (
            Path(current_app.root_path) / stored_path
        ).resolve()

        # 只允许删除 uploads 目录下的文件
        if absolute_path.parent != upload_root:
            raise PaperValidationError("文件路径超出允许的删除范围。")

        # 先删除数据库记录
        self.repository.delete(paper)

        # 再清理磁盘文件
        try:
            absolute_path.unlink(missing_ok=True)

        except OSError:
            current_app.logger.exception(
                "论文记录已删除，但 PDF 文件清理失败：%s",
                absolute_path
            )

        # 最后清理向量库记录；失败不改变论文已删除的结果
        try:
            # 延迟导入，避免应用启动阶段就初始化 ChromaDB
            from rag.vector_store import vector_store

            deleted_count = vector_store.delete_paper_chunks(
                paper_id
            )

            current_app.logger.info(
                "论文向量库记录已清理 | paper_id=%s | count=%s",
                paper_id,
                deleted_count
            )

        except Exception:
            current_app.logger.exception(
                "论文已删除，但向量库记录清理失败：paper_id=%s",
                paper_id
            )