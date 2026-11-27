
import sys
import pymupdf


def inspect_pdf_layout(pdf_path, page_number=1):
    """
    检查 PDF 指定页面的文字块坐标和版面分布。
    page_number 从 1 开始。
    """

    doc = pymupdf.open(pdf_path)

    try:
        if page_number < 1 or page_number > len(doc):
            raise ValueError(
                f"页码超出范围，当前 PDF 共 {len(doc)} 页"
            )

        page = doc[page_number - 1]

        page_width = page.rect.width
        page_height = page.rect.height
        middle_x = page_width / 2

        blocks = page.get_text("blocks", sort=False)

        print("=" * 60)
        print(f"PDF 文件：{pdf_path}")
        print(f"当前页码：{page_number}")
        print(f"页面宽度：{page_width:.2f}")
        print(f"页面高度：{page_height:.2f}")
        print(f"文字块数量：{len(blocks)}")
        print("=" * 60)

        for index, block in enumerate(blocks):

            x0, y0, x1, y1 = block[:4]
            content = block[4].strip()

            block_type = block[6] if len(block) > 6 else 0

            # 暂时只分析文字块
            if block_type != 0 or not content:
                continue

            block_width = x1 - x0
            center_x = (x0 + x1) / 2

            if x1 < middle_x - 10:
                position = "左栏"

            elif x0 > middle_x + 10:
                position = "右栏"

            else:
                position = "跨栏或中间区域"

            print(f"\n第 {index + 1} 个文字块")
            print(f"位置判断：{position}")
            print(
                f"坐标：x0={x0:.1f}, y0={y0:.1f}, "
                f"x1={x1:.1f}, y1={y1:.1f}"
            )
            print(f"文字块宽度：{block_width:.1f}")
            print(f"中心横坐标：{center_x:.1f}")
            print(f"文字内容：{content[:150]}")

    finally:
        doc.close()


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(
            '使用方法：python -m tests.manual_test_pdf_layout '
            '"PDF文件路径" [页码]'
        )
        sys.exit(1)

    pdf_path = sys.argv[1]

    page_number = int(sys.argv[2]) if len(sys.argv) >= 3 else 1

    inspect_pdf_layout(pdf_path, page_number)
