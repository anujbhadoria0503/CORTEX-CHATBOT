from sentence_transformers import SentenceTransformer
# EMBEDDING MODEL
model = SentenceTransformer(
    "BAAI/bge-large-en-v1.5"
)
# CREATE EMBEDDINGS
def create_embeddings(chunks):
    if not chunks:
        return []
    texts = [
        chunk["text"]
        for chunk in chunks
    ]
    embeddings = model.encode(
        texts,
        normalize_embeddings=True
    )
    return embeddings