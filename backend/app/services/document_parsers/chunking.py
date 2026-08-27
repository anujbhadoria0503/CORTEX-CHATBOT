from .common import clean_text
CUSTOM_CHUNKING = True
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
def custom_chunks(
    sections
):
    chunks = []
    for section in sections:
        content = clean_text(
            section.get(
                "content",
                ""
            )
        )
        if not content:
            continue
        chunk = {
            "text": content,
            "type": section.get(
                "type",
                "paragraph"
            ),
            "page": section.get(
                "page"
            ),
            "last_page": section.get(
                "last_page",
                section.get("page")
            ),
            "heading": section.get(
                "heading",
                ""
            )
        }
        chunks.append(
            chunk
        )
    return chunks
def normal_chunks(
    sections,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP
):
    chunks = []
    for section in sections:
        text = clean_text(
            section.get(
                "content",
                ""
            )
        )
        if not text:
            continue
        if overlap >= chunk_size:
            raise ValueError(
                "overlap must be smaller "
                "than chunk_size"
            )
        start = 0
        while start < len(text):
            end = (
                start + chunk_size
            )
            chunk_text = text[
                start:end
            ].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "type": section.get(
                        "type",
                        "paragraph"
                    ),
                    "page": section.get(
                        "page"
                    ),
                    "last_page": section.get(
                        "last_page",
                        section.get("page")
                    ),
                    "heading": section.get(
                        "heading",
                        ""
                    )
                })
            start += (
                chunk_size - overlap
            )
    return chunks

