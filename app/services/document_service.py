from document_search_v2 import search_documents

def search_document(
    query: str,
    platform="all"
):
    return search_documents(
        query,
        platform
    )