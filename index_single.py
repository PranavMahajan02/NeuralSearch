import os
import sys
import pickle

from sentence_transformers import SentenceTransformer

from extract import extract_text
from docx_extract import extract_docx
from txt_extract import extract_txt

from paddle_extract import extract_text as paddle_ocr

from chunk import chunk_text


model = SentenceTransformer("all-MiniLM-L6-v2")

if len(sys.argv) < 2:
    print("Usage: python index_single.py <file_path>")
    sys.exit(1)

file_path = sys.argv[1]

filename = os.path.basename(file_path)

print(f"\nProcessing new file: {filename}")

# -----------------------------
# Load existing index
# -----------------------------

if os.path.exists("index.pkl"):
    with open("index.pkl", "rb") as f:
        all_documents = pickle.load(f)
else:
    all_documents = []

print(f"Existing chunks: {len(all_documents)}")

before_count = len(all_documents)

# -----------------------------
# Remove old entries
# -----------------------------

all_documents = [
    doc
    for doc in all_documents
    if os.path.abspath(doc["path"])
       != os.path.abspath(file_path)
]

removed = before_count - len(all_documents)

print(f"Removed old chunks: {removed}")

# -----------------------------
# Extract text
# -----------------------------

text = ""

if filename.endswith(".pdf"):
    text = extract_text(file_path)

elif filename.endswith(".docx"):
    text = extract_docx(file_path)

elif filename.endswith(".txt"):
    text = extract_txt(file_path)

elif filename.lower().endswith(
    (".jpg", ".jpeg", ".png")
):

    print(f"Running PaddleOCR: {filename}")

    text = paddle_ocr(file_path)

else:
    print("Unsupported file type")
    sys.exit(1)

if not text.strip():
    print("No text extracted")
    sys.exit(1)

# -----------------------------
# Chunk + Embed
# -----------------------------

chunks = chunk_text(
    text,
    chunk_size=500
)

embeddings = model.encode(
    chunks
)

for chunk, embedding in zip(
    chunks,
    embeddings
):

    all_documents.append(
        {
            "file": filename,
            "path": file_path,
            "chunk": chunk,
            "embedding": embedding
        }
    )

# -----------------------------
# Save updated index
# -----------------------------

with open("index.pkl", "wb") as f:
    pickle.dump(
        all_documents,
        f
    )

print(f"Added {len(chunks)} new chunks")
print(f"Total chunks: {len(all_documents)}")
print("Index updated successfully")