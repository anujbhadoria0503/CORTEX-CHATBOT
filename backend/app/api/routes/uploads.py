from fastapi import APIRouter, File, UploadFile
import os
import shutil
from app.services.embedding import create_embeddings
from app.services.qdrant_service import save_embeddings
from app.services.document_parser import parse_document
router = APIRouter()
# ============================================================
# UPLOAD DOCUMENT
# Supports:
#   - PDF
#   - DOCX
# ============================================================
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...)
):
    # --------------------------------------------------------
    # Check file extension
    # --------------------------------------------------------
    allowed_extensions = {
        ".pdf",
        ".docx"
    }
    filename = file.filename or ""
    extension = os.path.splitext(
        filename
    )[1].lower()
    if extension not in allowed_extensions:
        return {
            "message": (
                "Unsupported file type. "
                "Only PDF and DOCX files are allowed."
            ),
            "filename": filename
        }
    # --------------------------------------------------------
    # Upload directory
    # --------------------------------------------------------
    upload_dir = "uploads"
    os.makedirs(
        upload_dir,
        exist_ok=True
    )
    # --------------------------------------------------------
    # File path
    # --------------------------------------------------------
    file_path = os.path.join(
        upload_dir,
        filename
    )
    # --------------------------------------------------------
    # Save uploaded file
    # --------------------------------------------------------
    with open(
        file_path,
        "wb"
    ) as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )
    print(
        "\n=========================================="
    )
    print(
        "DOCUMENT UPLOAD"
    )
    print(
        "=========================================="
    )
    print(
        f"Filename: {filename}"
    )
    print(
        f"Type: {extension}"
    )
    # --------------------------------------------------------
    # Parse document
    # PDF:
    #     PyMuPDF
    # DOCX:
    #     Mammoth -> HTML -> BeautifulSoup
    # --------------------------------------------------------
    try:
        chunks = parse_document(
            file_path
        )
    except Exception as e:
        print(
            f"Document parsing failed: {e}"
        )
        return {
            "message":
                "Document parsing failed",

            "filename":
                filename,

            "error":
                str(e)
        }
    # --------------------------------------------------------
    # Check chunks
    # --------------------------------------------------------
    if not chunks:
        return {
            "message":
                "No content found in document",

            "filename":
                filename,

            "chunks":
                0
        }
    # --------------------------------------------------------
    # Print chunk statistics
    # --------------------------------------------------------
    paragraph_count = sum(
        1
        for chunk in chunks
        if chunk.get("type") == "paragraph"
    )
    table_count = sum(
        1
        for chunk in chunks
        if chunk.get("type") == "table"
    )
    print(
        f"Created {len(chunks)} document chunks."
    )
    print(
        f"Paragraph chunks: {paragraph_count}"
    )
    print(
        f"Table chunks: {table_count}"
    )
    # --------------------------------------------------------
    # Create embeddings
    # --------------------------------------------------------
    print(
        "Creating embeddings..."
    )
    embeddings = create_embeddings(
        chunks
    )
    print(
        f"Created {len(embeddings)} embeddings."
    )
    # --------------------------------------------------------
    # Save to Qdrant + MySQL
    # --------------------------------------------------------
    print(
        "Saving embeddings..."
    )
    save_embeddings(
        chunks,
        embeddings,
        filename
    )
    print(
        "Document indexing completed."
    )
    print(
        "==========================================\n"
    )
    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------
    return {
        "message":
            "Document uploaded successfully",
        "filename":
            filename,
        "file_type":
            extension,
        "chunks":
            len(chunks),
        "paragraph_chunks":
            paragraph_count,
        "table_chunks":
            table_count
    }