import pickle

from app.vectorstore.insert import insert_vectors
from app.vectorstore.config import IMAGE_COLLECTION

print("Loading image_index.pkl...")

with open("image_index.pkl", "rb") as f:
    images = pickle.load(f)

print(f"Loaded {len(images)} images.")

documents = []

for image in images:

    documents.append({

        "file": image.get("file"),
        "path": image.get("path"),
        "platform": image.get("platform", "local"),
        "file_id": image.get("file_id"),
        "owner": image.get("owner"),
        "repo": image.get("repo"),
        "sha": image.get("sha"),
        "last_modified": image.get("last_modified"),

        # searchable text
        "chunk": image.get("ocr_text", ""),
        "ocr_text": image.get("ocr_text", ""),

        # CLIP vector
        "embedding": image.get("embedding"),

    })

print(f"Migrating {len(documents)} images to Qdrant...")

insert_vectors(
    documents,
    IMAGE_COLLECTION
)

print("Migration completed successfully.")