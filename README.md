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

## Screenshots

Captured by `frontend/e2e/screenshots.ts`, which walks a throwaway demo account (sample notes and
stock photos only) through the real flow and deletes it afterwards.

| Sign in | Onboarding 1: connect platforms | Onboarding 2: choose the priority platform |
|---|---|---|
| ![Login](docs/screenshots/login.png) | ![Onboarding step 1](docs/screenshots/onboarding-step1.png) | ![Onboarding step 2](docs/screenshots/onboarding-step2.png) |
| **Dashboard while the priority platform indexes** | **Indexing Center (running)** | **Indexing Center (done, dark)** |
| ![Priority banner](docs/screenshots/dashboard-banner.png) | ![Indexing running](docs/screenshots/indexing-center-running.png) | ![Indexing dark](docs/screenshots/indexing-center-dark.png) |
| **Dashboard** | **Document query (highlighted passage)** | **Visual query "dog" (no query word in the file name)** |
| ![Dashboard](docs/screenshots/dashboard.png) | ![Document search](docs/screenshots/search-document.png) | ![Visual search](docs/screenshots/search-visual-dog.png) |
| **No results** | **Platforms** | **Platforms (dark)** |
| ![Empty result](docs/screenshots/search-empty.png) | ![Platforms](docs/screenshots/platforms.png) | ![Platforms dark](docs/screenshots/platforms-dark.png) |

Also: [visual query in dark mode](docs/screenshots/search-visual-dog-dark.png),
[mobile (375 px, dark)](docs/screenshots/mobile-dashboard-dark.png), [Indexing Center (light)](docs/screenshots/indexing-center.png).

## Frontend

React 19 + TypeScript + Vite + Tailwind, TanStack Query for server state, React Router.

```bash
cd frontend
npm install
npm run dev          # http://127.0.0.1:3000 - fails (strictPort) if the port is taken
```

Open the app at **http://127.0.0.1:3000** and set `FRONTEND_URL=http://127.0.0.1:3000` in `.env`:
the browser keeps the login token per origin, so the OAuth return URL must use the same host.
The backend URL comes from `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`).

| Command | What it does |
|---|---|
| `npm run lint` | ESLint (typescript-eslint, react-hooks, jsx-a11y) + Prettier check |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` / `npm run coverage` | Vitest + Testing Library + MSW (fake backend); coverage threshold 70% |
| `npm run build` | type check + production build |
| `npm run gen:api` | regenerate `src/api/schema.d.ts` from the backend's `/openapi.json` (backend running in development) |
| `npm run test:e2e` | Playwright smoke test against the real backend (below) |
| `npm run depcheck` | unused dependencies |

### End-to-end smoke test

Runs against the **real** backend: it creates a throwaway user `e2e-<id>@cogniseek.dev`, registers a
temporary folder with 3 sample files, indexes it, searches, downloads a result, runs axe accessibility
checks, logs out, then deletes the user and all of its data (`scripts/delete_e2e_user.py`, which refuses any
other e-mail) and the temporary folder.

```bash
# backend running (uvicorn app.main:app) with its worker; then, in frontend/:
npx playwright install chromium   # once
npm run test:e2e                  # starts `npm run dev` unless E2E_BASE_URL is set
```

The test registers a new user, so it also covers onboarding: step 1 (add the folder), step 2 (Local
Storage as the priority platform), the dashboard banner, then search and download; axe runs on the
login, onboarding, dashboard, indexing and platforms pages, in light and dark mode.

`E2E_BASE_URL` / `E2E_API_URL` point it at other URLs; the temporary folder is created under the system
temp directory, which must lie inside the backend's `ALLOWED_LOCAL_ROOTS` (default: the home directory) -
set `E2E_FILES_ROOT` otherwise. `E2E_PYTHON` selects the Python used for the cleanup (default: `venv`).

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

## Excluded files

Generated and noise files are never indexed by any connector: `INDEX_EXCLUDE_GLOBS` in `.env`
(comma-separated base-name globs, case-insensitive; default
`*.log,*.lock,*.min.js,*.map,*_log.txt,project_files.txt,package-lock.json,yarn.lock,poetry.lock`).
Matches are recorded as `excluded` and counted as skipped. To remove files indexed before a pattern
was added:

```bash
python scripts/purge_excluded.py --dry-run   # counts per user and platform
python scripts/purge_excluded.py             # delete them (vectors + ledger rows)
```

## Known limitations

- **Shared Drives are not indexed.** The Google Drive connector lists the files in your
  My Drive and those shared with you; files that live in a Shared Drive (Team Drive) are skipped.
- **No query expansion.** Search matches what files contain or are named. A category query such as
  "Find my government documents" finds files whose name or text uses those words (e.g. "government");
  an ID scan named `scan01.jpg` with no such words is only found by a query about its actual content.
- **Visual image search** returns an image on visual similarity alone only when the CLIP match is clear
  (about 70% of relevant images in the evaluation; see `docs/eval/phase5-clip-gate.md`).
  Photos of documents (screenshots, scanned forms) are found through their OCR text and file name, not visually.
- **Typos** are tolerated in single words ("jva" → "java"), but a typo plus an unmatched word
  ("jva notes") may return nothing.
- **Evaluation:** 1 false positive remains on the negative set — "elephant" returns a Java document whose
  text mentions elephants (a true content match the eval counts as wrong).
- **Local folders:** only files under the registered local folders stay indexed; removing a folder
  (or a file) removes it from the index on the next run.
