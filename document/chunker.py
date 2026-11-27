import re


class ChunkingError(Exception):
    """文本分块异常。"""
    pass


def _find_boundary(text: str, start: int, end: int) -> int:
    """
    在目标区间内寻找较自然的文本切分位置。
    优先考虑段落、换行和句子边界。
    """
    search_start = start + int((end - start) * 0.65)

    separators = [
        "\n\n",
        "\n",
        "。", "！", "？", "；",
        ". ", "! ", "? ", "; "
    ]

    candidates = []

    for separator in separators:
        position = text.rfind(separator, search_start, end)

        if position != -1:
            candidates.append(position + len(separator))

    if candidates:
        return max(candidates)

    return end


def _split_page_text(
    text: str,
    chunk_size: int,
    overlap: int
) -> list[str]:
    """将单页文本拆分为多个文本块。"""

    text = re.sub(r"\r\n?", "\n", text).strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):

        hard_end = min(start + chunk_size, len(text))

        if hard_end == len(text):
            end = hard_end
        else:
            end = _find_boundary(text, start, hard_end)

        content = text[start:end].strip()

        if content:
            chunks.append(content)

        if end >= len(text):
            break

        start = max(start + 1, end - overlap)

    return chunks


def build_chunks(
    parsed_pdf: dict,
    chunk_size: int = 1200,
    overlap: int = 150
) -> list[dict]:
    """
    根据 PDF 解析结果生成文本块。

    每个文本块保留：
    - chunk_index：全篇论文中的文本块序号
    - page_number：原始 PDF 页码
    - content：文本内容
    - char_count：字符数量
    """

    if not isinstance(parsed_pdf, dict):
        raise ChunkingError("PDF 解析结果必须是字典。")

    if (
        not isinstance(chunk_size, int)
        or isinstance(chunk_size, bool)
        or chunk_size <= 0
    ):
        raise ChunkingError("chunk_size 必须是正整数。")

    if (
        not isinstance(overlap, int)
        or isinstance(overlap, bool)
        or overlap < 0
        or overlap >= chunk_size
    ):
        raise ChunkingError(
            "overlap 必须是非负整数，且小于 chunk_size。"
        )

    pages = parsed_pdf.get("pages")

    if not isinstance(pages, list):
        raise ChunkingError("PDF 解析结果中缺少 pages 列表。")

    all_chunks = []

    for page in pages:

        if not isinstance(page, dict):
            raise ChunkingError("页面数据格式错误。")

        page_number = page.get("page_number")
        page_text = page.get("text", "")

        if (
            not isinstance(page_number, int)
            or isinstance(page_number, bool)
            or page_number < 1
        ):
            raise ChunkingError("页面页码必须是正整数。")

        if not isinstance(page_text, str):
            raise ChunkingError("页面文本必须是字符串。")

        page_chunks = _split_page_text(
            page_text,
            chunk_size,
            overlap
        )

        for content in page_chunks:

            chunk = {
                "chunk_index": len(all_chunks),
                "page_number": page_number,
                "content": content,
                "char_count": len(content)
            }

            all_chunks.append(chunk)

    return all_chunks