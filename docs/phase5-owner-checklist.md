# Phase 5 – owner checklist (connectors)

Do these steps as **pranav2@gmail.com**. Everything else (backups, code, tests) is ready.
Backups of the index and DB are in `backups/phase5-*/` (Qdrant snapshot files + `pg_dump`).

## 1. One-time setup: Google "Web application" client (required)

The current `credentials/client_secret.json` is a **Desktop app** client. The new
connect flow needs a **Web application** client.

1. Open <https://console.cloud.google.com/apis/credentials> and select the project
   that owns the current client.
2. **Create credentials → OAuth client ID → Application type: Web application**.
   Name: `CogniSeek (web)`.
3. **Authorized redirect URIs → Add URI**:
   `http://127.0.0.1:8000/platforms/google-drive/callback`
4. Create, then **Download JSON**. Replace `credentials/client_secret.json` with it
   (keep the old file as `client_secret.desktop.json` if you like).
   The new file must start with `{"web": ...}`.
5. **APIs & Services → OAuth consent screen**: make sure the scopes
   `.../auth/drive.readonly`, `openid`, `.../auth/userinfo.email` are listed and
   your Google account is a **test user** (while the app is in "Testing").

## 2. One-time setup: GitHub OAuth App callback

GitHub → Settings → Developer settings → OAuth Apps → your app →
**Authorization callback URL** = `http://127.0.0.1:8000/platforms/github/callback`
(no change needed if it already is).

## 3. Start the app

```powershell
docker compose up -d
venv\Scripts\alembic upgrade head
venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# second terminal
cd frontend; npm run dev
```

Open <http://localhost:3000> and log in.

## 4. Reconnect both platforms (new OAuth flows)

1. On the connections page, **Disconnect** Google Drive and answer **Cancel**
   ("keep indexed files"), then **Connect** Google Drive.
   You are sent to Google; approve; you come back with a green
   "Google Drive connected successfully." toast and your email on the card.
2. Do the same for **GitHub** (your GitHub login appears on the card).

## 5. Index both (first run)

Start indexing for Google Drive and GitHub. Wait until both jobs are finished
(Indexing Center shows *Completed* or *Completed with errors*).

## 6. Open results

1. Search for a Drive document, e.g. `final report` → **Open File** →
   a new tab opens on **drive.google.com / docs.google.com**.
2. Search for a GitHub file, e.g. `train model` → **Open File** →
   a new tab opens on `https://github.com/<owner>/<repo>/blob/<default-branch>/...`
   (the repository's real default branch, not always `main`).

## 7. Second run (must download ~0 files)

Start indexing for Google Drive and GitHub again. Both jobs should finish
quickly and show **0 downloaded** (unchanged files are skipped before download).

## 8. Tell the engineer you're done

The engineer then collects: both job summaries (first + second run, including
`downloaded_files`), indexed-file counts per platform before/after, and the
search-eval numbers.
