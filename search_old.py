from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from rapidfuzz import fuzz

from extract import extract_text
from docx_extract import extract_docx
from txt_extract import extract_txt

from ocr_extract import extract_image_text as tesseract_ocr
from easyocr_extract import extract_image_text as easyocr_ocr

from chunk import chunk_text

import os

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Store all indexed documents
all_documents = []

data_folder = "data"

print("Indexing Files...\n")

# ==================================
# INDEX ALL FILES
# ==================================

for filename in os.listdir(data_folder):

    file_path = os.path.join(data_folder, filename)

    text = ""

    # PDF
    if filename.endswith(".pdf"):
        text = extract_text(file_path)

    # DOCX
    elif filename.endswith(".docx"):
        text = extract_docx(file_path)

    # TXT
    elif filename.endswith(".txt"):
        text = extract_txt(file_path)

    # IMAGE FILES
elif filename.lower().endswith((".jpg", ".jpeg", ".png")):

    print(f"Running EasyOCR on {filename}...")
    text_easy = easyocr_ocr(file_path)

    print(f"Running Tesseract OCR on {filename}...")
    text_tesseract = tesseract_ocr(file_path)

    # Use the OCR result with more extracted text
    if len(text_easy) >= len(text_tesseract):
        text = text_easy
        print("Using EasyOCR result")
    else:
        text = text_tesseract
        print("Using Tesseract result")

    # Skip empty files
    if not text.strip():
        continue

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

# ==================================
# SEARCH LOOP
# ==================================

while True:

    query = input("\nEnter Search Query (or type exit): ")

    if query.lower() == "exit":
        break

    query_lower = query.lower()

    # ==================================
    # 1. FILE NAME SEARCH
    # ==================================

    file_found = False

    for doc in all_documents:

        filename_without_extension = os.path.splitext(
            doc["file"]
        )[0].lower()

        if query_lower in filename_without_extension:

            print("\n==============================")
            print("Best Match File:")
            print(doc["file"])
            print("\nMatched using FILE NAME SEARCH")
            print("==============================")

            open_choice = input(
                "\nOpen this file? (y/n): "
            )

            if open_choice.lower() == "y":
                os.startfile(doc["path"])

            file_found = True
            break

    if file_found:
        continue

    # ==================================
# 2. FUZZY KEYWORD SEARCH
# ==================================

matched_docs = []

for doc in all_documents:

    score = fuzz.token_set_ratio(
        query_lower,
        doc["chunk"].lower()
    )

    if score > 90:

        if doc not in matched_docs:
            matched_docs.append(doc)

if len(matched_docs) > 0:

    print("\n==============================")
    print("\nFound in:\n")

    shown_files = set()

    count = 1

    for doc in matched_docs:

        if doc["file"] not in shown_files:

            print(f"{count}. {doc['file']}")

            shown_files.add(doc["file"])

            count += 1

    print("\nMatched using FUZZY KEYWORD SEARCH")
    print("==============================")

    choice = input(
        "\nEnter file number to open (0 to skip): "
    )

    if choice.isdigit():

        choice = int(choice)

        unique_docs = []

        unique_files = set()

        for doc in matched_docs:

            if doc["file"] not in unique_files:

                unique_docs.append(doc)

                unique_files.add(doc["file"])

        if 1 <= choice <= len(unique_docs):

            selected_doc = unique_docs[
                choice - 1
            ]

            print(
                f"\nOpening: {selected_doc['file']}"
            )

            os.startfile(
                selected_doc["path"]
            )

    continue

    # ==================================
    # 3. SEMANTIC SEARCH
    # ==================================

    query_embedding = model.encode([query])

    scores = cosine_similarity(
        query_embedding,
        [doc["embedding"]
         for doc in all_documents]
    )[0]

    best_index = scores.argmax()
    best_score = scores[best_index]

    if best_score < 0.35:

        print(
            "\nNo relevant document found."
        )

        continue

    print("\n==============================")
    print("Best Match File:")
    print(
        all_documents[best_index]["file"]
    )

    print("\nSimilarity Score:")
    print(best_score)

    print("\nBest Matching Content:")
    print(
        all_documents[best_index]["chunk"]
    )

    print("==============================")

    open_choice = input(
        "\nOpen this file? (y/n): "
    )

    if open_choice.lower() == "y":

        os.startfile(
            all_documents[best_index]["path"]
        )