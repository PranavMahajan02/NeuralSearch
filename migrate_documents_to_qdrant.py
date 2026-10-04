import pickle

from app.vectorstore.insert import insert_vectors
from app.vectorstore.config import TEXT_COLLECTION

print("Loading index.pkl...")

with open("index.pkl", "rb") as f:
    documents = pickle.load(f)

print(f"Loaded {len(documents)} document chunks.")

print("Migrating documents to Qdrant...")

insert_vectors(
    documents,
    TEXT_COLLECTION
)

print("Migration completed successfully.")