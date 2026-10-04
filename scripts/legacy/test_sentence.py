print("1")

from sentence_transformers import SentenceTransformer

print("2")

model = SentenceTransformer(
    "all-MiniLM-L6-v2",
    device="cuda"
)

print("3")