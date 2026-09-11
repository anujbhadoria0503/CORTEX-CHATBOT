from fastapi import APIRouter, File, UploadFile, Form
import os
import shutil
from app.services.embedding import create_embeddings
from app.services.qdrant_service import save_embeddings
from app.services.document_parser import parse_document
router = APIRouter()
@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    if not session_id:
        return {
            "message": "Session ID is required",
            "filename": file.filename or ""
        }
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
    upload_dir = "uploads"
    os.makedirs(
        upload_dir,
        exist_ok=True
    )
    file_path = os.path.join(
        upload_dir,
        filename
    )
    with open(
        file_path,
        "wb"
    ) as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )
    print(
        f"Document uploaded: {filename}"
    )
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
                str(e),
            "session_id":
                session_id
        }
    if not chunks:
        return {
            "message":
                "No content found in document",
            "filename":
                filename,
            "chunks":
                0,
            "session_id":
                session_id
        }
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
        "Creating embeddings..."
    )
    embeddings = create_embeddings(
        chunks
    )
    print(
        f"Created {len(embeddings)} embeddings."
    )
    print(
        "Saving embeddings..."
    )
    save_embeddings(
        chunks,
        embeddings,
        filename,
        session_id
    )
    print(
        "Document indexing completed."
    )
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
            table_count,
        "session_id":
            session_id
    }