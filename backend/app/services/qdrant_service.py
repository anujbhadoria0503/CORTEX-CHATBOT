from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
import uuid
import re
from app.db.models import Document
from app.db.connection import session_scope
# QDRANT CONNECTION
client = QdrantClient(path="./qdrant_data")
COLLECTION_NAME = "documents"
# SAVE EMBEDDINGS
def save_embeddings(chunks, embeddings, filename, session_id):
    if chunks is None or len(chunks) == 0:
        print("No chunks to save.")
        return
    if embeddings is None or len(embeddings) == 0:
        print("No embeddings to save.")
        return
    if not session_id:
        print("Session ID is required.")
        return
    # CREATE COLLECTION
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=len(embeddings[0]),
                distance=Distance.COSINE
            )
        )
        print(f"Created Qdrant collection: {COLLECTION_NAME}")
    # PREPARE POINTS
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        point_id = str(uuid.uuid4())
        text = chunk.get("text", "")
        chunk_type = chunk.get("type", "paragraph")
        page = chunk.get("page")
        last_page = chunk.get("last_page", page)
        heading = chunk.get("heading", "")
        # QDRANT POINT
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "text": text,
                    "filename": filename,
                    "session_id": session_id,
                    "type": chunk_type,
                    "page": page,
                    "last_page": last_page,
                    "heading": heading
                }
            )
        )
        # SAVE DOCUMENT CHUNK TO MYSQL
        with session_scope() as session:
            document = Document(
                id=point_id,
                filename=filename,
                chunk=text
            )
            session.add(document)
            session.commit()
    # SAVE VECTORS TO QDRANT
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"Saved {len(points)} embeddings to Qdrant.")
# GET FILENAMES FOR A SESSION
def get_session_filenames(session_id):
    if not session_id:
        return []
    # BUILD SESSION FILTER
    session_filter = Filter(
        must=[
            FieldCondition(
                key="session_id",
                match=MatchValue(value=session_id)
            )
        ]
    )
    # CHECK COLLECTION
    try:
        if not client.collection_exists(COLLECTION_NAME):
            return []
    except Exception:
        return []
    # GET ALL POINTS FOR THIS SESSION
    try:
        points, _ = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=session_filter,
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
    except Exception as e:
        print(f"Could not get session documents: {e}")
        return []
    # EXTRACT UNIQUE FILENAMES
    filenames = []
    seen = set()
    for point in points:
        payload = point.payload or {}
        filename = payload.get("filename")
        if filename and filename not in seen:
            seen.add(filename)
            filenames.append(filename)
    return filenames
# EXTRACT IDENTIFIER FROM QUESTION
def extract_identifier(question):
    if not question:
        return None
    # EMPLOYEE / TRAINING / OTHER ALPHANUMERIC IDS
    match = re.search(
        r"\b[A-Za-z]{2,10}-\d{1,10}\b",
        question
    )
    if match:
        return match.group(0)
    return None
# OLD FUNCTION NAME KEPT FOR COMPATIBILITY
def extract_reg_id(question):
    return extract_identifier(question)
# EXACT IDENTIFIER SEARCH
def search_by_reg_id(reg_id, limit=5, filename=None, session_id=None):
    matches = []
    offset = None
    # BUILD SCROLL FILTER
    must_conditions = []
    if session_id:
        must_conditions.append(
            FieldCondition(
                key="session_id",
                match=MatchValue(value=session_id)
            )
        )
    if filename:
        must_conditions.append(
            FieldCondition(
                key="filename",
                match=MatchValue(value=filename)
            )
        )
    scroll_filter = None
    if must_conditions:
        scroll_filter = Filter(must=must_conditions)
    # SEARCH QDRANT POINTS
    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            scroll_filter=scroll_filter,
            with_payload=True,
            with_vectors=False
        )
        for point in points:
            payload = point.payload or {}
            text = payload.get("text", "")
            # EXACT IDENTIFIER MATCH
            pattern = (
                r"(?<![A-Za-z0-9])"
                + re.escape(reg_id)
                + r"(?![A-Za-z0-9])"
            )
            if re.search(pattern, text, re.IGNORECASE):
                matches.append({
                    "id": str(point.id),
                    "score": 1.0,
                    "text": text,
                    "filename": payload.get("filename", ""),
                    "session_id": payload.get("session_id"),
                    "type": payload.get("type", ""),
                    "page": payload.get("page"),
                    "last_page": payload.get("last_page"),
                    "heading": payload.get("heading", "")
                })
        # STOP PAGINATION
        if next_offset is None:
            break
        offset = next_offset
    return matches[:limit]
# SEMANTIC SEARCH
def semantic_search(question_embedding, top_k=5, filename=None, session_id=None):
    # BUILD FILTER
    must_conditions = []
    # SESSION FILTER
    if session_id:
        must_conditions.append(
            FieldCondition(
                key="session_id",
                match=MatchValue(value=session_id)
            )
        )
    # FILENAME FILTER
    if filename:
        must_conditions.append(
            FieldCondition(
                key="filename",
                match=MatchValue(value=filename)
            )
        )
    # FINAL FILTER
    query_filter = None
    if must_conditions:
        query_filter = Filter(must=must_conditions)
    # QDRANT SEMANTIC SEARCH
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=question_embedding.tolist(),
        query_filter=query_filter,
        limit=top_k
    )
    # BUILD RESULTS
    relevant_chunks = []
    for result in results.points:
        payload = result.payload or {}
        relevant_chunks.append({
            "id": str(result.id),
            "score": float(result.score),
            "text": payload.get("text", ""),
            "filename": payload.get("filename", ""),
            "session_id": payload.get("session_id"),
            "type": payload.get("type", ""),
            "page": payload.get("page"),
            "last_page": payload.get("last_page"),
            "heading": payload.get("heading", "")
        })
    return relevant_chunks
# MAIN SEARCH FUNCTION
def search_similar(question_embedding, top_k=5, question=None, filename=None, session_id=None):
    # EXACT IDENTIFIER SEARCH
    if question:
        identifier = extract_identifier(question)
        if identifier:
            print(f"\nExact identifier detected: {identifier}")
            exact_results = search_by_reg_id(
                identifier,
                limit=top_k,
                filename=filename,
                session_id=session_id
            )
            if exact_results:
                print(
                    f"Exact identifier matches found: "
                    f"{len(exact_results)}"
                )
                return exact_results
            print("No exact identifier match found.")
    # FALLBACK TO SEMANTIC SEARCH
    print("Using semantic Qdrant search...")
    return semantic_search(
        question_embedding,
        top_k=top_k,
        filename=filename,
        session_id=session_id
    )