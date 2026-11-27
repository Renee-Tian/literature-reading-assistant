
import sys
import pymupdf

from document.layout_analyzer import restore_two_column_order


def test_two_column_pdf(pdf_path, page_number):

    doc = pymupdf.open(pdf_path)

    try:
        page = doc[page_number - 1]

        blocks = page.get_text("blocks", sort=False)

        ordered_blocks = restore_two_column_order(
            blocks=blocks,
            page_width=page.rect.width
        )

        print("=" * 60)
        print(f"PDF：{pdf_path}")
        print(f"页码：{page_number}")
        print(f"恢复后的文字块数量：{len(ordered_blocks)}")
        print("=" * 60)

        for index, block in enumerate(ordered_blocks, start=1):

            print(f"\n【第 {index} 个文字块】")
            print(block["content"])

    finally:
        doc.close()


if __name__ == "__main__":

    if len(sys.argv) < 3:
        print(
            '使用方法：python -m tests.manual_test_two_column '
            '"PDF路径" 页码'
        )
        sys.exit(1)

    pdf_path = sys.argv[1]
    page_number = int(sys.argv[2])

    test_two_column_pdf(pdf_path, page_number)
