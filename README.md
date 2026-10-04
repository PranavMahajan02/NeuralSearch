# NeuralSearch

AI-powered document search system that supports:

- PDF Search
- DOCX Search
- TXT Search
- Image OCR Search

Technologies:
- EasyOCR
- Tesseract OCR
- Sentence Transformers
- RapidFuzz
- Cosine Similarity

Features:
- Semantic Search
- Fuzzy Search
- File Name Search
- Persistent Indexing

## Database migrations

The schema is managed with Alembic (the app no longer calls `create_all`).

```powershell
docker compose up -d                    # postgres + qdrant
venv\Scripts\alembic upgrade head       # create / upgrade the schema
```

- New schema change: `venv\Scripts\alembic revision --autogenerate -m "<what>"`, review the file, then `alembic upgrade head`.
- `venv\Scripts\alembic check` must report "No new upgrade operations detected".
- A database that predates Alembic is adopted once with `alembic stamp 0001_baseline`.
