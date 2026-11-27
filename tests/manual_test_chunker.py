import sys

from document.pdf_parser import (
    extract_pdf_text,
    PDFParseError
)

from document.chunker import (
    build_chunks,
    ChunkingError
)


def main():

    if len(sys.argv) < 2:
        print("使用方法：python -m tests.manual_test_chunker PDF文件路径")
        return

    pdf_path = sys.argv[1]

    try:
        # 第一步：解析 PDF
        parsed_pdf = extract_pdf_text(pdf_path)

        # 第二步：生成文本块
        chunks = build_chunks(parsed_pdf)

        # 第三步：输出测试结果
        print("PDF 文件：", parsed_pdf["file_name"])
        print("PDF 总页数：", parsed_pdf["page_count"])
        print("文本块总数：", len(chunks))
        print("-" * 50)

        for chunk in chunks[:5]:
            print("Chunk 序号：", chunk["chunk_index"])
            print("来源页码：", chunk["page_number"])
            print("字符数量：", chunk["char_count"])
            print("文本预览：", chunk["content"][:150])
            print("-" * 50)

        if chunks:
            print("文本分块测试完成。")
        else:
            print("没有生成文本块，请检查 PDF 是否包含可提取文本。")

    except (PDFParseError, ChunkingError) as error:
        print("测试失败：", error)


if __name__ == "__main__":
    main()