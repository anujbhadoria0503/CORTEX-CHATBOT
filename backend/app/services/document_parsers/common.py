import re
def clean_text(text):
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")
    text = re.sub(
        r"(?<=[a-z])(?=[A-Z])",
        " ",
        text
    )
    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )
    return text.strip()
def is_page_number(text):
    text = clean_text(text)
    if not text:
        return False
    return bool(
        re.fullmatch(
            r"\d+",
            text
        )
    )
def is_footer(text):
    text = clean_text(text)
    if not text:
        return False
    footer_patterns = [
        "Newfoundland and Labrador - Labour Standards",
        "Government of Newfoundland and Labrador"
    ]
    for pattern in footer_patterns:
        if text == pattern:
            return True
    return False
def clean_cell(cell):
    if cell is None:
        return ""
    cell = str(cell)
    cell = cell.replace(
        "\x00",
        " "
    )
    cell = re.sub(
        r"\s+",
        " ",
        cell
    )
    # Escape markdown pipe
    cell = cell.replace(
        "|",
        "\\|"
    )
    return cell.strip()
def is_heading(line):
    line = clean_text(line)
    if not line:
        return False
    if is_page_number(line):
        return False
    if is_footer(line):
        return False
    if len(line) > 100:
        return False
    if line.endswith("?"):
        return False
    # --------------------------------------------------------
    # Numbered heading
    # --------------------------------------------------------
    if re.match(
        r"^\d+(\.\d+)*\s+[A-Z].*",
        line
    ):
        return True
    # --------------------------------------------------------
    # ALL CAPS heading
    # --------------------------------------------------------
    if (
        line.upper() == line
        and any(
            char.isalpha()
            for char in line
        )
        and len(line) <= 80
    ):
        return True
    return False

