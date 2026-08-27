import mammoth
from bs4 import BeautifulSoup
from .common import clean_text, clean_cell
from .table_utils import rows_to_markdown
def extract_docx_document(
    docx_path
):
    """
    DOCX -> HTML using Mammoth -> BeautifulSoup.
    Important:
    - <h1> ... <h6> => heading
    - <p>             => paragraph
    - <table>         => table
    - Paragraphs inside a table are NOT added as separate paragraph chunks.
    """
    print(
        f"Processing DOCX: {docx_path}"
    )
    # --------------------------------------------------------
    # DOCX -> HTML
    # --------------------------------------------------------
    with open(
        docx_path,
        "rb"
    ) as docx_file:
        result = mammoth.convert_to_html(
            docx_file
        )
    html = result.value
    # --------------------------------------------------------
    # Mammoth warnings
    # --------------------------------------------------------
    if result.messages:
        for message in result.messages:
            print(
                f"Mammoth: {message}"
            )
    # --------------------------------------------------------
    # Debug: verify what Mammoth actually generated
    # --------------------------------------------------------
    table_count = len(
        BeautifulSoup(
            html,
            "html.parser"
        ).find_all("table")
    )
    print(
        f"Mammoth HTML tables detected: {table_count}"
    )
    # --------------------------------------------------------
    # HTML parser
    # --------------------------------------------------------
    soup = BeautifulSoup(
        html,
        "html.parser"
    )
    sections = []
    current_heading = ""
    # --------------------------------------------------------
    # Process HTML in document order
    #
    # IMPORTANT:
    # We iterate over direct document elements as much as
    # possible and explicitly ignore <p> elements that are
    # descendants of <table>.
    # --------------------------------------------------------
    for element in soup.find_all(
        [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "table"
        ]
    ):
        # ====================================================
        # TABLE
        # ====================================================
        if element.name == "table":
            rows = []
            for tr in element.find_all(
                "tr"
            ):
                cells = tr.find_all(
                    [
                        "th",
                        "td"
                    ],
                    recursive=False
                )
                # Some DOCX HTML can contain nested markup
                # inside cells, so fall back if necessary.
                if not cells:
                    cells = tr.find_all(
                        [
                            "th",
                            "td"
                        ]
                    )
                row = []
                for cell in cells:
                    cell_text = clean_cell(
                        cell.get_text(
                            " ",
                            strip=True
                        )
                    )
                    row.append(
                        cell_text
                    )
                # Ignore completely empty rows
                if any(
                    cell.strip()
                    for cell in row
                ):
                    rows.append(
                        row
                    )
            if not rows:
                continue
            content = rows_to_markdown(
                rows
            )
            if not content:
                continue
            sections.append({
                "type": "table",
                "page": None,
                "last_page": None,
                "heading": current_heading,
                "content": content
            })
            continue
        # ====================================================
        # IGNORE PARAGRAPHS THAT BELONG TO A TABLE
        # ====================================================
        if element.name == "p":
            if element.find_parent("table") is not None:
                continue
        # ====================================================
        # HEADING
        # ====================================================
        if element.name in [
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6"
        ]:
            heading = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )
            if heading:
                current_heading = heading
            continue
        # ====================================================
        # PARAGRAPH
        # ====================================================
        if element.name == "p":
            text = clean_text(
                element.get_text(
                    " ",
                    strip=True
                )
            )
            if not text:
                continue
            sections.append({
                "type": "paragraph",
                "page": None,
                "last_page": None,
                "heading": current_heading,
                "content": text
            })
            continue
    print(
        f"DOCX sections extracted: {len(sections)}"
    )
    print(
        "DOCX paragraphs:",
        sum(
            1
            for section in sections
            if section.get("type") == "paragraph"
        )
    )
    print(
        "DOCX tables:",
        sum(
            1
            for section in sections
            if section.get("type") == "table"
        )
    )
    return sections

