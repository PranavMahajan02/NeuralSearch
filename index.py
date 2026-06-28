import os
import pickle
import time
import torch

from sentence_transformers import SentenceTransformer

from pptx_extract import extract_pptx
from extract import extract_text
from docx_extract import extract_docx
from txt_extract import extract_txt

from paddle_extract import extract_text as paddle_ocr

from chunk import chunk_text


def build_index():

    # ==========================
    # MODEL
    # ==========================

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(f"Using device: {device}")

    model = SentenceTransformer(
        "all-MiniLM-L6-v2",
        device=device
    )

    # ==========================
    # VARIABLES
    # ==========================

    all_documents = []

    data_folder = "data"

    seen_files = set()

    print("Building Index...\n")

    total_start = time.time()

    # ==========================
    # INDEXING LOOP
    # ==========================

    for filename in os.listdir(data_folder):

        normalized_name = (
            filename.lower()
            .replace(" copy", "")
        )

        if normalized_name in seen_files:

            print(
                f"Skipping duplicate: {filename}"
            )

            continue

        seen_files.add(
            normalized_name
        )

        file_path = os.path.join(
            data_folder,
            filename
        )

        file_start = time.time()

        text = ""

        # --------------------------
        # EXTRACTION
        # --------------------------

        if filename.endswith(".pdf"):

            text = extract_text(
                file_path
            )

        elif filename.endswith(".docx"):

            text = extract_docx(
                file_path
            )

        elif filename.endswith(".pptx"):

            text = extract_pptx(
                file_path
            )

        elif filename.endswith(".txt"):

            text = extract_txt(
                file_path
            )

        elif filename.lower().endswith(
            (
                ".jpg",
                ".jpeg",
                ".png"
            )
        ):

            print(
                f"Running PaddleOCR: {filename}"
            )

            text = paddle_ocr(
                file_path
            )

        else:
            continue

        extract_time = (
            time.time()
            - file_start
        )

        print(
            f"Extraction Time ({filename}): "
            f"{extract_time:.2f}s"
        )

        if not text.strip():

            print(
                f"Skipping empty file: {filename}\n"
            )

            continue

        print(
            f"Processing: {filename}"
        )

        # --------------------------
        # CHUNKING
        # --------------------------

        chunks = chunk_text(
            text,
            chunk_size=1000
        )

        print(
            f"Chunks Created: "
            f"{len(chunks)}"
        )

        # --------------------------
        # EMBEDDINGS
        # --------------------------

        embed_start = time.time()

        embeddings = model.encode(
            chunks,
            batch_size=256,
            show_progress_bar=False
        )

        embed_time = (
            time.time()
            - embed_start
        )

        print(
            f"Embedding Time ({filename}): "
            f"{embed_time:.2f}s"
        )

        # --------------------------
        # STORE
        # --------------------------

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

        file_time = (
            time.time()
            - file_start
        )

        print(
            f"Total File Time ({filename}): "
            f"{file_time:.2f}s\n"
        )

    # ==========================
    # FINAL STATS
    # ==========================

    total_time = (
        time.time()
        - total_start
    )

    print("\n======================")
    print("INDEXING COMPLETE")
    print("======================")

    print(
        f"Unique Files Indexed: "
        f"{len(seen_files)}"
    )

    print(
        f"Total Chunks Indexed: "
        f"{len(all_documents)}"
    )

    print(
        f"Total Indexing Time: "
        f"{total_time:.2f}s"
    )

    # ==========================
    # SAVE INDEX
    # ==========================

    with open(
        "index.pkl",
        "wb"
    ) as f:

        pickle.dump(
            all_documents,
            f
        )

    print(
        "\nIndex saved as index.pkl"
    )


if __name__ == "__main__":
    build_index()