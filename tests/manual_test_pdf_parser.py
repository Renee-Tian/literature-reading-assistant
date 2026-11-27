import sys

from document.pdf_parser import (
    parse_pdf,
    PDFParserError
)


def main():

    # 从命令行获取 PDF 路径
    if len(sys.argv) < 2:
        print(
            "使用方法：python -m tests.manual_test_pdf_parser <PDF路径>"
        )
        return

    pdf_path = sys.argv[1]

    try:
        result = parse_pdf(pdf_path)

        print("=" * 50)
        print("PDF 解析成功")
        print("=" * 50)

        print("文件名称：", result["file_name"])
        print("总页数：", result["page_count"])
        print("总字符数：", result["total_characters"])

        print("空白页面：", result["empty_pages"])

        print(
            "是否提取到文本：",
            result["has_extractable_text"]
        )

        print("=" * 50)

        # 展示第一页文本
        for page in result["pages"]:
            if page["text"]:
                print("第一页可提取文本示例：")
                print(page["text"][:500])
                break

        if not result["has_extractable_text"]:
            print("警告：该 PDF 没有提取到文本，可能需要 OCR。")

    except PDFParserError as error:

        print("解析失败：", error)


if __name__ == "__main__":
    main()
    