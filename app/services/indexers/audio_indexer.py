"""Audio -> Whisper transcript chunks -> MiniLM vectors (collection: audio)."""

from app.ai.embedder import embed_texts
from app.services.index_store import IndexPoint
from app.services.indexers.document_indexer import chunk_text

CHUNK_SIZE = 500


def extract_audio_transcript(path: str) -> str:

    from app.extractors.audio_extract import extract_audio_text

    return extract_audio_text(path) or ""


def build_audio_points(path: str, temp_dir=None) -> list[IndexPoint]:
    """Silent audio -> no points ('no_content', not re-transcribed next run)."""

    transcript = extract_audio_transcript(path)

    if not transcript.strip():
        return []

    chunks = chunk_text(transcript, CHUNK_SIZE)
    vectors = embed_texts(chunks)

    return [
        IndexPoint(type="audio", vector=vector, chunk_index=index, chunk=chunk)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]
