from io import BytesIO
import pymupdf
import pytesseract
from PIL import Image

from .common import clean_text, is_page_number, is_footer, is_heading
from .table_utils import (
    extract_tables,
    extract_non_table_text,
    group_text_blocks,
    group_to_text,
    remove_duplicate_lines,
    merge_tables,
)

def ocr_page(page):
    pix = page.get_pixmap(
        matrix=pymupdf.Matrix(2, 2),
        alpha=False
    )
    image_bytes = pix.tobytes(
        "png"
    )
    image = Image.open(
        BytesIO(image_bytes)
    )
    text = pytesseract.image_to_string(
        image
    )
    return clean_text(
        text
    )

def extract_page_text(page):
    text = page.get_text(
        "text"
    )
    text = clean_text(
        text
    )
    if text:
        return text
    print(
        f"Native text unavailable "
        f"on page {page.number + 1}. "
        f"Running OCR..."
    )
    return ocr_page(
        page
    )

def extract_document(
    pdf_path
):
    pdf = pymupdf.open(
        pdf_path
    )
    sections = []
    current_heading = ""
    all_tables = []
    for page_number, page in enumerate(pdf):
        print(
            f"Processing page "
            f"{page_number + 1}/"
            f"{len(pdf)}"
        )
        # ----------------------------------------------------
        # Skip TOC
        # ----------------------------------------------------
        if page_number == 1:
            continue
        # ----------------------------------------------------
        # TABLES
        # ----------------------------------------------------
        page_tables = extract_tables(
            page
        )
        for table in page_tables:
            table["page"] = (
                page_number + 1
            )
            table["heading"] = (
                current_heading
            )
            all_tables.append(
                table
            )
        table_bboxes = [
            table["bbox"]
            for table in page_tables
        ]
        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------
        text_blocks = extract_non_table_text(
            page,
            table_bboxes
        )
        groups = group_text_blocks(
            text_blocks
        )
        for group in groups:
            text = group_to_text(
                group
            )
            if not text:
                continue
            lines = text.splitlines()
            lines = remove_duplicate_lines(
                lines
            )
            paragraph_lines = []
            for line in lines:
                line = clean_text(
                    line
                )
                if not line:
                    continue
                if is_page_number(line):
                    continue
                if is_footer(line):
                    continue
                # ------------------------------------------------
                # HEADING
                # ------------------------------------------------
                if is_heading(line):
                    if line == current_heading:
                        continue
                    # Save paragraph before heading
                    if paragraph_lines:
                        content = "\n".join(
                            paragraph_lines
                        ).strip()
                        if content:
                            sections.append({
                                "type": "paragraph",
                                "page": page_number + 1,
                                "heading": current_heading,
                                "content": content
                            })
                        paragraph_lines = []
                    current_heading = line
                else:
                    paragraph_lines.append(
                        line
                    )
            # Save remaining paragraph
            if paragraph_lines:
                content = "\n".join(
                    paragraph_lines
                ).strip()
                if content:
                    sections.append({
                        "type": "paragraph",
                        "page": page_number + 1,
                        "heading": current_heading,
                        "content": content
                    })
    pdf.close()
    # --------------------------------------------------------
    # MERGE TABLES
    # --------------------------------------------------------
    merged_tables = merge_tables(
        all_tables
    )
    # --------------------------------------------------------
    # ADD TABLE SECTIONS
    # --------------------------------------------------------
    for table in merged_tables:
        sections.append({
            "type": "table",
            "page": table["page"],
            "last_page": table["last_page"],
            "heading": table.get(
                "heading",
                ""
            ),
            "content": table["content"]
        })
    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------
    sections.sort(
        key=lambda section: (
            section.get(
                "page",
                0
            ),
            0 if section["type"] == "paragraph" else 1
        )
    )
    return sections

