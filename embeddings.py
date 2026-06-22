from sentence_transformers import SentenceTransformer

print("Loading embedding model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

print("Embedding model loaded.")


def get_embeddings(texts):
    """
    Generate embeddings for a list of texts/chunks.
    """

    return model.encode(texts)