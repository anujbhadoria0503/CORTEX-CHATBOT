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
# ============================================================
# QDRANT CONNECTION
# ============================================================
client = QdrantClient(
    path="./qdrant_data"
)
COLLECTION_NAME = "documents"
# ============================================================
# SAVE EMBEDDINGS
# ============================================================
def save_embeddings(
    chunks,
    embeddings,
    filename
):
    if chunks is None or len(chunks) == 0:
        print("No chunks to save.")
        return
    if embeddings is None or len(embeddings) == 0:
        print("No embeddings to save.")
        return
    # --------------------------------------------------------
    # CREATE COLLECTION
    # --------------------------------------------------------
    if not client.collection_exists(
        COLLECTION_NAME
    ):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=len(embeddings[0]),
                distance=Distance.COSINE
            )
        )
        print(
            f"Created Qdrant collection: "
            f"{COLLECTION_NAME}"
        )
    # --------------------------------------------------------
    # PREPARE POINTS
    # --------------------------------------------------------
    points = []
    for chunk, embedding in zip(
        chunks,
        embeddings
    ):
        point_id = str(
            uuid.uuid4()
        )
        text = chunk.get(
            "text",
            ""
        )
        chunk_type = chunk.get(
            "type",
            "paragraph"
        )
        page = chunk.get(
            "page"
        )
        last_page = chunk.get(
            "last_page",
            page
        )
        heading = chunk.get(
            "heading",
            ""
        )
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "text": text,
                    "filename": filename,
                    "type": chunk_type,
                    "page": page,
                    "last_page": last_page,
                    "heading": heading
                }
            )
        )
        # ----------------------------------------------------
        # SAVE DOCUMENT TO MYSQL
        # ----------------------------------------------------
        with session_scope() as session:
            document = Document(
                id=point_id,
                filename=filename,
                chunk=text
            )
            session.add(
                document
            )
            session.commit()
    # --------------------------------------------------------
    # SAVE VECTORS TO QDRANT
    # --------------------------------------------------------
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(
        f"Saved {len(points)} embeddings "
        f"to Qdrant."
    )
# ============================================================
# EXTRACT IDENTIFIER FROM QUESTION
# ============================================================
def extract_identifier(question):
    if not question:
        return None
    # ========================================================
    # EMPLOYEE / TRAINING / OTHER ALPHANUMERIC IDS
    # ========================================================
    #
    # Examples:
    #
    # EMP-1001
    # EMP-1004
    # TR-02
    # TR-100
    #
    # ========================================================
    match = re.search(
        r"\b[A-Za-z]{2,10}-\d{1,10}\b",
        question
    )
    if match:
        return match.group(0)
    return None
# ============================================================
# OLD FUNCTION NAME KEPT FOR COMPATIBILITY
# ============================================================
def extract_reg_id(question):
    return extract_identifier(
        question
    )
# ============================================================
# EXACT IDENTIFIER SEARCH
# ============================================================
def search_by_reg_id(
    reg_id,
    limit=5,
    filename=None
):
    matches = []
    offset = None
    # --------------------------------------------------------
    # SEARCH ALL QDRANT POINTS
    # --------------------------------------------------------
    while True:
        points, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        for point in points:
            payload = point.payload or {}
            # ------------------------------------------------
            # FILENAME FILTER
            # ------------------------------------------------
            if filename:
                if payload.get(
                    "filename"
                ) != filename:
                    continue
            text = payload.get(
                "text",
                ""
            )
            # ------------------------------------------------
            # EXACT IDENTIFIER MATCH
            # ------------------------------------------------
            pattern = (
                r"(?<![A-Za-z0-9])"
                + re.escape(
                    reg_id
                )
                + r"(?![A-Za-z0-9])"
            )
            if re.search(
                pattern,
                text,
                re.IGNORECASE
            ):
                matches.append({
                    "id": str(
                        point.id
                    ),
                    "score": 1.0,
                    "text": text,
                    "filename": payload.get(
                        "filename",
                        ""
                    ),
                    "type": payload.get(
                        "type",
                        ""
                    ),
                    "page": payload.get(
                        "page"
                    ),
                    "last_page": payload.get(
                        "last_page"
                    ),
                    "heading": payload.get(
                        "heading",
                        ""
                    )
                })
        # ----------------------------------------------------
        # STOP PAGINATION
        # ----------------------------------------------------
        if next_offset is None:
            break
        offset = next_offset
    return matches[:limit]
# ============================================================
# SEMANTIC SEARCH
# ============================================================
def semantic_search(
    question_embedding,
    top_k=5,
    filename=None
):
    # --------------------------------------------------------
    # BUILD FILENAME FILTER
    # --------------------------------------------------------
    query_filter = None
    if filename:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="filename",
                    match=MatchValue(
                        value=filename
                    )
                )
            ]
        )
    # --------------------------------------------------------
    # QDRANT SEMANTIC SEARCH
    # --------------------------------------------------------
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=question_embedding.tolist(),
        query_filter=query_filter,
        limit=top_k
    )
    relevant_chunks = []
    for result in results.points:
        payload = result.payload or {}
        relevant_chunks.append({
            "id": str(
                result.id
            ),
            "score": float(
                result.score
            ),
            "text": payload.get(
                "text",
                ""
            ),
            "filename": payload.get(
                "filename",
                ""
            ),
            "type": payload.get(
                "type",
                ""
            ),
            "page": payload.get(
                "page"
            ),
            "last_page": payload.get(
                "last_page"
            ),
            "heading": payload.get(
                "heading",
                ""
            )
        })
    return relevant_chunks
# ============================================================
# MAIN SEARCH FUNCTION
# ============================================================
def search_similar(
    question_embedding,
    top_k=5,
    question=None,
    filename=None
):
    # ========================================================
    # EXACT IDENTIFIER SEARCH
    # ========================================================
    if question:
        identifier = extract_identifier(
            question
        )
        if identifier:
            print(
                f"\nExact identifier detected: "
                f"{identifier}"
            )
            exact_results = search_by_reg_id(
                identifier,
                limit=top_k,
                filename=filename
            )
            if exact_results:
                print(
                    f"Exact identifier matches found: "
                    f"{len(exact_results)}"
                )
                return exact_results
            print(
                "No exact identifier match found."
            )
    # ========================================================
    # FALLBACK TO SEMANTIC SEARCH
    # ========================================================
    print(
        "Using semantic Qdrant search..."
    )
    return semantic_search(
        question_embedding,
        top_k=top_k,
        filename=filename
    )
