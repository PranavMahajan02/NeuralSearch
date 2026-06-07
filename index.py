import os
import pickle

from sentence_transformers import SentenceTransformer

from extract import extract_text
from docx_extract import extract_docx
from txt_extract import extract_txt

from ocr_extract import extract_image_text as tesseract_ocr
from easyocr_extract import extract_image_text as easyocr_ocr

from chunk import chunk_text

model = SentenceTransformer("all-MiniLM-L6-v2")

all_documents = []

data_folder = "data"

print("Building Index...\n")

for filename in os.listdir(data_folder):

    file_path = os.path.join(data_folder, filename)

    text = ""

    if filename.endswith(".pdf"):
        text = extract_text(file_path)

    elif filename.endswith(".docx"):
        text = extract_docx(file_path)

    elif filename.endswith(".txt"):
        text = extract_txt(file_path)

    elif filename.lower().endswith((".jpg", ".jpeg", ".png")):

        print(f"Running OCR: {filename}")

        easy_text = easyocr_ocr(file_path)
        tess_text = tesseract_ocr(file_path)

        if len(easy_text) >= len(tess_text):
            text = easy_text
        else:
            text = tess_text

    else:
        continue

    if not text.strip():
        continue

    print(f"Processing: {filename}")

    chunks = chunk_text(text, chunk_size=500)

    embeddings = model.encode(chunks)

    for chunk, embedding in zip(chunks, embeddings):

        all_documents.append({
            "file": filename,
            "path": file_path,
            "chunk": chunk,
            "embedding": embedding
        })

print(f"\nTotal Chunks Indexed: {len(all_documents)}")

with open("index.pkl", "wb") as f:
    pickle.dump(all_documents, f)

print("\nIndex saved as index.pkl")