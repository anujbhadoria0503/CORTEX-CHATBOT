from .pdf_parser import extract_document
from .docx_parser import extract_docx_document
from .chunking import custom_chunks, normal_chunks
CUSTOM_CHUNKING = True
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
def parse_document(
    file_path
):
    file_path_lower = file_path.lower()
    # ========================================================
    # PDF
    # ========================================================
    if file_path_lower.endswith(
        ".pdf"
    ):
        sections = extract_document(
            file_path
        )
    # ========================================================
    # DOCX
    # ========================================================
    elif file_path_lower.endswith(
        ".docx"
    ):
        sections = extract_docx_document(
            file_path
        )
    # ========================================================
    # UNSUPPORTED
    # ========================================================
    else:
        raise ValueError(
            "Unsupported file type. "
            "Only PDF and DOCX are supported."
        )
    # ========================================================
    # NO CONTENT
    # ========================================================
    if not sections:
        return []
    # ========================================================
    # CUSTOM CHUNKING
    # ========================================================
    if CUSTOM_CHUNKING:
        return custom_chunks(
            sections
        )
    # ========================================================
    # NORMAL CHUNKING
    # ========================================================
    return normal_chunks(
        sections,
        chunk_size=CHUNK_SIZE,
        overlap=CHUNK_OVERLAP
    )

