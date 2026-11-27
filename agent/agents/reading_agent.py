from database.db import db
from models import Paper
from repositories.chunk_repository import ChunkRepository
from services.long_document_service import (
    DEFAULT_MAX_CHARS,
    LongDocumentError,
    generate_long_document_report,
)


class ReadingAgentError(Exception):
    """Reading Agent 异常。"""
    pass


def get_single_paper_id(state):
    """读取并校验当前阅读的论文 ID。"""

    paper_ids = state.get("paper_ids") or []

    if not isinstance(paper_ids, list):
        raise ReadingAgentError("paper_ids 必须是列表。")

    if len(paper_ids) != 1:
        raise ReadingAgentError(
            "Reading Agent 当前只支持一篇论文，请提供一个 paper_id。"
        )

    paper_id = paper_ids[0]

    if (
        not isinstance(paper_id, int)
        or isinstance(paper_id, bool)
        or paper_id <= 0
    ):
        raise ReadingAgentError("paper_id 必须是正整数。")

    return paper_id


def load_paper_chunks(paper_id):
    """从 MySQL 读取论文的文本块，并转换为阅读服务需要的格式。"""

    records = ChunkRepository.list_by_paper_id(paper_id)

    if not records:
        raise ReadingAgentError(
            f"论文没有可用的文本块，paper_id={paper_id}。"
        )

    chunks = []

    for record in records:
        chunks.append({
            "chunk_index": record.chunk_index,
            "page_number": record.page_number,
            "content": record.content,
        })

    return chunks


def reading_agent(state):
    """
    Reading Agent。

    负责：
    1. 读取指定论文及其全部文本块。
    2. 使用长文档阅读服务进行分批阅读。
    3. 汇总生成整篇论文的结构化阅读报告。
    4. 返回阅读结果和模型调用信息。
    """

    paper_id = get_single_paper_id(state)

    paper = db.session.get(Paper, paper_id)

    if paper is None:
        raise ReadingAgentError(
            f"论文不存在，paper_id={paper_id}。"
        )

    chunks = load_paper_chunks(paper_id)

    try:
        result = generate_long_document_report(
            chunks=chunks,
            title=paper.title,
            max_chars=state.get(
                "reading_max_chars",
                DEFAULT_MAX_CHARS,
            ),
        )

    except LongDocumentError as error:
        raise ReadingAgentError(
            f"Reading Agent 阅读失败：{error}"
        ) from error

    return {
        "reading_result": {
            "paper_id": paper_id,
            "paper_title": paper.title,
            "chunk_count": len(chunks),
            "report": result["report"],
            "batch_count": result["batch_count"],
            "model": result.get("model"),
            "usage": result.get("usage"),
            "elapsed_ms": result.get("elapsed_ms"),
            "prompt_version": result.get("prompt_version"),
        }
    }
