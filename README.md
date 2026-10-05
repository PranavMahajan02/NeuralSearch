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

## Connecting Google Drive and GitHub (OAuth)

Both connectors use a browser OAuth redirect: the app sends you to Google/GitHub and
their consent page sends you back to the backend callback, which then returns you to
the frontend (`/?google_drive=connected` or `/?github=connected`).

### Google Drive

1. Google Cloud console → **APIs & Services → Credentials → Create credentials → OAuth client ID**.
2. Application type: **Web application** (a "Desktop app" client does not work with this flow).
3. **Authorized redirect URIs**: add exactly the value of `GOOGLE_REDIRECT_URI`
   (default `http://127.0.0.1:8000/platforms/google-drive/callback`).
4. Enable the **Google Drive API** for the project, and on the OAuth consent screen add the scopes
   `drive.readonly`, `openid` and `userinfo.email` (and your account as a test user while the app is in testing).
5. Download the client JSON and save it as `credentials/client_secret.json`
   (the file must start with `{"web": ...}`).

### GitHub

1. GitHub → **Settings → Developer settings → OAuth Apps** → your app.
2. **Authorization callback URL**: `http://127.0.0.1:8000/platforms/github/callback`
   (i.e. `BACKEND_PUBLIC_URL` + `/platforms/github/callback`).
3. `credentials/github_oauth.json` holds `{"client_id": "...", "client_secret": "..."}`.

Disconnecting revokes the grant at Google/GitHub; choose whether to also delete the files
already indexed from that platform.
