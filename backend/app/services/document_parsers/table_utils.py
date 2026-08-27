from .common import clean_text, clean_cell, is_page_number, is_footer, is_heading
def extract_table_rows(table):
    rows = table.extract()
    if not rows:
        return []
    cleaned_rows = []
    for row in rows:
        if row is None:
            continue
        cleaned_row = []
        for cell in row:
            cleaned_row.append(
                clean_cell(cell)
            )
        cleaned_rows.append(
            cleaned_row
        )
    if not cleaned_rows:
        return []
    column_count = max(
        len(row)
        for row in cleaned_rows
    )
    for row in cleaned_rows:
        while len(row) < column_count:
            row.append("")
    cleaned_rows = [
        row
        for row in cleaned_rows
        if any(
            cell.strip()
            for cell in row
        )
    ]
    return cleaned_rows
def rows_to_markdown(rows):
    if not rows:
        return ""
    column_count = max(
        len(row)
        for row in rows
    )
    normalized_rows = []
    for row in rows:
        row = list(row)
        while len(row) < column_count:
            row.append("")
        normalized_rows.append(
            row
        )
    header = normalized_rows[0]
    markdown = []
    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------
    markdown.append(
        "| "
        + " | ".join(header)
        + " |"
    )
    # --------------------------------------------------------
    # Separator
    # --------------------------------------------------------
    markdown.append(
        "| "
        + " | ".join(
            ["---"] * column_count
        )
        + " |"
    )
    # --------------------------------------------------------
    # Rows
    # --------------------------------------------------------
    for row in normalized_rows[1:]:
        markdown.append(
            "| "
            + " | ".join(row)
            + " |"
        )
    return "\n".join(
        markdown
    )

def extract_tables(page):
    tables = []
    try:
        finder = page.find_tables()
        for table in finder.tables:
            rows = extract_table_rows(
                table
            )
            if not rows:
                continue
            tables.append({
                "type": "table",
                "bbox": table.bbox,
                "rows": rows,
                "content": rows_to_markdown(
                    rows
                )
            })
    except Exception as e:
        print(
            f"Table detection failed "
            f"on page {page.number + 1}: {e}"
        )
    return tables
def rectangles_overlap(
    rect1,
    rect2
):
    x0, y0, x1, y1 = rect1
    a0, b0, a1, b1 = rect2
    if x1 <= a0 or a1 <= x0:
        return False
    if y1 <= b0 or b1 <= y0:
        return False
    return True
def block_inside_table(
    block,
    table_bboxes
):
    if len(block) < 5:
        return False
    block_bbox = (
        block[0],
        block[1],
        block[2],
        block[3]
    )
    for table_bbox in table_bboxes:
        if rectangles_overlap(
            block_bbox,
            table_bbox
        ):
            return True
    return False
def extract_non_table_text(
    page,
    table_bboxes
):
    blocks = page.get_text(
        "blocks"
    )
    text_blocks = []
    for block in blocks:
        if len(block) < 5:
            continue
        text = block[4]
        if not text:
            continue
        if block_inside_table(
            block,
            table_bboxes
        ):
            continue
        text = clean_text(
            text
        )
        if not text:
            continue
        if is_page_number(text):
            continue
        if is_footer(text):
            continue
        x0, y0, x1, y1 = block[:4]
        text_blocks.append({
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "text": text
        })
    text_blocks.sort(
        key=lambda item: (
            item["y0"],
            item["x0"]
        )
    )
    return text_blocks
def group_text_blocks(blocks):
    if not blocks:
        return []
    groups = []
    current_group = []
    previous_bottom = None
    for block in blocks:
        top = block["y0"]
        if previous_bottom is None:
            current_group.append(
                block
            )
            previous_bottom = block["y1"]
            continue
        gap = (
            top - previous_bottom
        )
        if gap < 20:
            current_group.append(
                block
            )
        else:
            if current_group:
                groups.append(
                    current_group
                )
            current_group = [
                block
            ]
        previous_bottom = block["y1"]
    if current_group:
        groups.append(
            current_group
        )
    return groups
def group_to_text(group):
    parts = []
    for block in group:
        text = clean_text(
            block["text"]
        )
        if text:
            parts.append(
                text
            )
    return "\n".join(
        parts
    ).strip()
def remove_duplicate_lines(lines):
    result = []
    previous = None
    for line in lines:
        line = clean_text(
            line
        )
        if not line:
            continue
        if line == previous:
            continue
        result.append(
            line
        )
        previous = line
    return result
def get_table_header(rows):
    if not rows:
        return []
    return [
        clean_cell(cell).lower()
        for cell in rows[0]
    ]
def is_same_table(
    previous_table,
    current_table
):
    if previous_table is None:
        return False
    if current_table is None:
        return False
    previous_rows = previous_table.get(
        "rows",
        []
    )
    current_rows = current_table.get(
        "rows",
        []
    )
    if not previous_rows or not current_rows:
        return False
    previous_header = get_table_header(
        previous_rows
    )
    current_header = get_table_header(
        current_rows
    )
    # --------------------------------------------------------
    # Same header
    # --------------------------------------------------------
    if (
        previous_header
        and current_header
        and previous_header == current_header
    ):
        return True
    # --------------------------------------------------------
    # Same columns + empty first row
    # --------------------------------------------------------
    if (
        len(previous_rows[-1])
        ==
        len(current_rows[0])
    ):
        first_row = current_rows[0]
        empty_count = sum(
            1
            for cell in first_row
            if not cell.strip()
        )
        if empty_count > 0:
            return True
    return False
def merge_tables(tables):
    if not tables:
        return []
    merged = []
    current = None
    for table in tables:
        if current is None:
            current = {
                "type": "table",
                "page": table["page"],
                "last_page": table["page"],
                "heading": table.get(
                    "heading",
                    ""
                ),
                "rows": [
                    list(row)
                    for row in table["rows"]
                ]
            }
            continue
        if is_same_table(
            current,
            table
        ):
            current_rows = current["rows"]
            new_rows = table["rows"]
            # Remove repeated header
            if (
                len(new_rows) > 1
                and
                get_table_header(
                    current_rows
                )
                ==
                get_table_header(
                    new_rows
                )
            ):
                new_rows = new_rows[1:]
            for row in new_rows:
                current["rows"].append(
                    list(row)
                )
            current["last_page"] = table[
                "page"
            ]
        else:
            current["content"] = rows_to_markdown(
                current["rows"]
            )
            merged.append(
                current
            )
            current = {
                "type": "table",
                "page": table["page"],
                "last_page": table["page"],
                "heading": table.get(
                    "heading",
                    ""
                ),
                "rows": [
                    list(row)
                    for row in table["rows"]
                ]
            }
    if current is not None:
        current["content"] = rows_to_markdown(
            current["rows"]
        )
        merged.append(
            current
        )
    return merged

