
from pathlib import Path

import pymupdf

from document.layout_analyzer import extract_page_text


class PDFParserError(Exception):
    """PDF 文件解析异常。"""
    pass


def parse_pdf(pdf_path):
    """
    解析 PDF 文件。

    功能：
    1. 检查文件是否存在。
    2. 检查文件格式。
    3. 检查 PDF 是否加密。
    4. 逐页提取文本。
    5. 自动识别单栏和双栏页面。
    6. 尝试恢复双栏页面的阅读顺序。
    7. 保留页码及页面版式信息。

    Args:
        pdf_path: PDF 文件路径。

    Returns:
        dict: PDF 解析结果。
    """

    # --------------------------------------------------
    # 1. 检查文件路径
    # --------------------------------------------------

    file_path = Path(pdf_path)

    if not file_path.exists():
        raise PDFParserError(
            f"PDF 文件不存在：{file_path}"
        )

    if not file_path.is_file():
        raise PDFParserError(
            f"指定路径不是文件：{file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise PDFParserError(
            "文件格式错误，仅支持 PDF 文件。"
        )

    # --------------------------------------------------
    # 2. 打开 PDF 文件
    # --------------------------------------------------

    try:
        doc = pymupdf.open(str(file_path))

    except Exception as exc:
        raise PDFParserError(
            f"无法打开 PDF 文件：{exc}"
        ) from exc

    try:

        # --------------------------------------------------
        # 3. 检查 PDF 加密状态
        # --------------------------------------------------

        if doc.needs_pass:
            raise PDFParserError(
                "PDF 文件已加密，请提供未加密的 PDF 文件。"
            )

        page_count = len(doc)

        if page_count == 0:
            raise PDFParserError(
                "PDF 文件没有页面。"
            )

        # --------------------------------------------------
        # 4. 初始化解析结果
        # --------------------------------------------------

        pages = []
        empty_pages = []

        total_characters = 0
        full_text_parts = []

        single_column_pages = 0
        two_column_pages = 0

        # --------------------------------------------------
        # 5. 逐页解析
        # --------------------------------------------------

        for page_index, page in enumerate(doc):

            page_number = page_index + 1

            try:

                # 使用版面分析模块提取页面文本
                page_result = extract_page_text(page)

                text = page_result["text"]
                layout_type = page_result["layout_type"]
                block_count = page_result["block_count"]

            except Exception as exc:

                raise PDFParserError(
                    f"第 {page_number} 页解析失败：{exc}"
                ) from exc

            # 记录空白页面
            if not text.strip():
                empty_pages.append(page_number)

            # 统计字符数量
            total_characters += len(text)

            # 统计页面版式
            if layout_type == "two_column":
                two_column_pages += 1
            else:
                single_column_pages += 1

            # 保存全文文本
            full_text_parts.append(text)

            # 保存单页解析结果
            pages.append({
                "page_number": page_number,
                "text": text,
                "layout_type": layout_type,
                "block_count": block_count
            })

        # --------------------------------------------------
        # 6. 合并全文
        # --------------------------------------------------

        full_text = "\n\n".join(full_text_parts)

        has_extractable_text = total_characters > 0

        # --------------------------------------------------
        # 7. 返回解析结果
        # --------------------------------------------------

        return {
            "file_name": file_path.name,

            "page_count": page_count,

            "total_characters": total_characters,

            "empty_pages": empty_pages,

            "has_extractable_text": has_extractable_text,

            "pages": pages,

            "full_text": full_text,

            "layout_statistics": {
                "single_column_pages": single_column_pages,
                "two_column_pages": two_column_pages
            }
        }

    finally:

        # 无论解析成功还是失败，都关闭 PDF
        doc.close()
