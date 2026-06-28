import os

print("1")

from app.services.index_manager import (
    load_index,
    save_index
)

print("2")

from extract import extract_text
print("3")

from docx_extract import extract_docx
print("4")

from pptx_extract import extract_pptx
print("5")

from txt_extract import extract_txt
print("6")

from app.services.indexers.csv_extract import extract_csv

from chunk import chunk_text
print("7")

from embeddings import get_embeddings
print("8")


def index_document(
    file_path,
    platform="local",
    file_id=None,
    file_sha=None,
    owner=None,
    repo=None
):

    print(f"Indexing document: {file_path}")

    filename = os.path.basename(file_path)

    extension = os.path.splitext(file_path)[1].lower()

    text = ""

    if extension == ".pdf":

        text = extract_text(file_path)

    elif extension == ".docx":

        text = extract_docx(file_path)

    elif extension == ".pptx":

        text = extract_pptx(file_path)

    elif extension == ".txt":

         text = extract_txt(file_path)

    elif extension == ".csv":

          text = extract_csv(file_path)

    elif extension in (
        ".jpg",
        ".jpeg",
        ".png"
    ):
        from paddle_extract import extract_text as paddle_ocr

        text = paddle_ocr(file_path)

    else:

        print(f"Unsupported file type: {extension}")

        return

    if not text.strip():

        print("No text extracted.")

        return

    print("Creating chunks...")

    chunks = chunk_text(
        text,
        chunk_size=1000
    )

    print(f"Chunks Created: {len(chunks)}")

    print("Generating embeddings...")

    embeddings = get_embeddings(
        chunks
    )

    print("Embeddings Created")

    all_documents = load_index(file_path)
        
    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        all_documents.append(
            {
                "file": filename,
                "path": file_path,
                "platform": platform,
                "file_id": file_id,
                "owner": owner,
                "repo": repo,
                "sha": file_sha,
                "last_modified": os.path.getmtime(file_path),
                "chunk": chunk,
                "embedding": embedding
            }
        )
        
    save_index(
        file_path,
        all_documents
    )

    print("Document indexing completed.")