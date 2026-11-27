
def restore_two_column_order(blocks, page_width):
    """
    根据文字块坐标，恢复常见双栏 PDF 的阅读顺序。

    blocks: PyMuPDF get_text("blocks") 返回的文字块
    page_width: PDF 页面宽度

    返回：按照估计阅读顺序排列的文字块
    """

    text_blocks = []

    for block in blocks:
        x0, y0, x1, y1 = block[:4]
        content = block[4].strip()

        block_type = block[6] if len(block) > 6 else 0

        if block_type != 0 or not content:
            continue

        text_blocks.append({
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "content": content,
            "width": x1 - x0
        })

    if not text_blocks:
        return []

    # 页面中线
    middle_x = page_width / 2

    # 初步识别跨栏文字块
    spanning_blocks = [
        block for block in text_blocks
        if block["width"] >= page_width * 0.72
    ]

    spanning_blocks.sort(key=lambda b: (b["y0"], b["x0"]))

    # 普通文字块
    column_blocks = [
        block for block in text_blocks
        if block not in spanning_blocks
    ]

    result = []
    current_y = 0

    # 逐个处理跨栏内容之间的区域
    for spanning in spanning_blocks:

        # 当前区域中，位于跨栏块之前的文字
        region = [
            block for block in column_blocks
            if current_y <= block["y0"] < spanning["y0"]
        ]

        left_blocks = [
            block for block in region
            if (block["x0"] + block["x1"]) / 2 < middle_x
        ]

        right_blocks = [
            block for block in region
            if (block["x0"] + block["x1"]) / 2 >= middle_x
        ]

        # 左栏优先，栏内从上到下
        left_blocks.sort(key=lambda b: (b["y0"], b["x0"]))
        right_blocks.sort(key=lambda b: (b["y0"], b["x0"]))

        result.extend(left_blocks)
        result.extend(right_blocks)

        # 放回跨栏文字块
        result.append(spanning)

        current_y = spanning["y1"]

    # 处理最后一个跨栏块之后的内容
    remaining = [
        block for block in column_blocks
        if block["y0"] >= current_y
    ]

    left_blocks = [
        block for block in remaining
        if (block["x0"] + block["x1"]) / 2 < middle_x
    ]

    right_blocks = [
        block for block in remaining
        if (block["x0"] + block["x1"]) / 2 >= middle_x
    ]

    left_blocks.sort(key=lambda b: (b["y0"], b["x0"]))
    right_blocks.sort(key=lambda b: (b["y0"], b["x0"]))

    result.extend(left_blocks)
    result.extend(right_blocks)

    return result


def detect_page_layout(blocks, page_width):
    """
    根据文字块坐标，初步判断页面是单栏还是双栏。

    返回：
    single_column 或 two_column
    """

    middle_x = page_width / 2

    left_count = 0
    right_count = 0

    for block in blocks:

        x0, y0, x1, y1 = block[:4]

        content = block[4].strip()
        block_type = block[6] if len(block) > 6 else 0

        if block_type != 0 or not content:
            continue

        width = x1 - x0

        # 排除明显的跨栏文字块
        if width >= page_width * 0.72:
            continue

        # 判断文字块属于左侧还是右侧
        if x1 < middle_x - 10:
            left_count += 1

        elif x0 > middle_x + 10:
            right_count += 1

    # 两侧均有足够文字块，才初步判定为双栏
    if left_count >= 2 and right_count >= 2:
        return "two_column"

    return "single_column"


def extract_page_text(page):
    """
    自动判断页面版式，并按照相应策略提取文本。
    """

    blocks = page.get_text("blocks", sort=False)

    layout_type = detect_page_layout(
        blocks=blocks,
        page_width=page.rect.width
    )

    if layout_type == "two_column":

        ordered_blocks = restore_two_column_order(
            blocks=blocks,
            page_width=page.rect.width
        )

    else:

        ordered_blocks = []

        for block in blocks:

            x0, y0, x1, y1 = block[:4]
            content = block[4].strip()

            block_type = block[6] if len(block) > 6 else 0

            if block_type != 0 or not content:
                continue

            ordered_blocks.append({
                "x0": x0,
                "y0": y0,
                "x1": x1,
                "y1": y1,
                "content": content
            })

        ordered_blocks.sort(
            key=lambda item: (item["y0"], item["x0"])
        )

    text = "\n\n".join(
        block["content"] for block in ordered_blocks
    )

    return {
        "layout_type": layout_type,
        "text": text,
        "block_count": len(ordered_blocks)
    }
