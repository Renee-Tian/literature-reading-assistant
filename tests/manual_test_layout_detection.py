
import sys
import pymupdf

from document.layout_analyzer import extract_page_text


def test_layout_detection(pdf_path):

    doc = pymupdf.open(pdf_path)

    try:

        print("=" * 60)
        print(f"论文：{pdf_path}")
        print(f"总页数：{len(doc)}")
        print("=" * 60)

        for page_index, page in enumerate(doc):

            result = extract_page_text(page)

            print(f"\n第 {page_index + 1} 页")
            print(f"版式：{result['layout_type']}")
            print(f"文字块数量：{result['block_count']}")

            print("-" * 40)

            print(result["text"][:500])

    finally:
        doc.close()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(
            '使用方法：python -m tests.manual_test_layout_detection '
            '"PDF路径"'
        )
        sys.exit(1)

    test_layout_detection(sys.argv[1])
