# CogniSeek AI — QA & Code Audit Report

**Date:** 2026-10-04 · **Scope:** the whole repo (backend `app/` + root modules, frontend `frontend/src`, Postgres, Qdrant, pickle indexes)
**Method:** I traced the code end to end, ran the backend live on CUDA, ran about 90 scripted HTTP calls, inspected the Qdrant and pickle data directly, ran concurrency and CORS probes, and ran a TypeScript check and production build of the frontend.
**No project files were modified.** Side effects of testing:
- I started the existing `qdrant` Docker container.
- I created two `qa_*@example.com` users in Postgres.
- I added and then removed one local-folder row.
- `/scheduler/status` was mutated in memory (this resets when the backend restarts).

**Not tested live:** Google Drive and GitHub indexing (the test user has no OAuth connection, and I did not use your accounts), full re-indexing runs (they are destructive or very long on your real data), and click-through UI testing in a browser. The frontend findings below come from tracing the code and checking the API contract. They are marked **[code]**. Live-verified findings are marked **[live]**.

---

## 1. What is actually implemented (storage/architecture)

| Layer | Reality |
|---|---|
| Users, OAuth tokens, folders, indexing jobs | **PostgreSQL** (docker `cogniseek-postgres`) via SQLAlchemy; `create_all` runs at import |
| Vector search | **Qdrant** at localhost:6333. It has 5 collections: `cogniseek` (text, 384-d), `_image` (512), `_audio`, `_video`, `_video_frames`. **Qdrant is not in `docker-compose.yml`.** |
| Metadata / "index" | Four **pickle files** (`index.pkl`, `image_index.pkl`, `audio_index.pkl`, `video_index.pkl`), global for all users, loaded into memory caches |
| Unused | The `IndexedFile` and `SearchCache` DB tables are defined but never used. `app/config/local_storage.json` and `local_config.py` are legacy code: the registry reads them but indexing uses the DB. |

Search reads **Qdrant**. Change detection, GitHub "open", and dashboard counts read the **pickles**. These two stores have drifted apart (see BUG-03).

## 2. Severity summary

| # | Severity | Area | Title |
|---|---|---|---|
| SEC-01 | Critical | Security | Unauthenticated `/delete/` with path traversal can delete arbitrary files |
| SEC-02 | Critical | Security | Unauthenticated `/open/` calls `os.startfile` on any path (opens or executes any local file) |
| SEC-03 | Critical | Security / Data | Search is unauthenticated and not scoped per user. Every user sees every user's files. |
| SEC-04 | High | Security | Unauthenticated upload at `POST /` with path traversal in the filename |
| SEC-05 | High | Security | Hard-coded JWT secret and DB password |
| SEC-06 | High | Security | GitHub OAuth `state` is the user UUID, so there is no CSRF protection |
| BUG-01 | Critical | Indexing | One exception in the scheduler kills the worker thread. Jobs stay "indexing" forever and the remaining platforms never run. |
| BUG-02 | Critical | Video search | The semantic and transcript scores are always 0 (the payload lacks `embedding` and `transcript`) |
| BUG-03 | High | Index | Qdrant and the pickles are out of sync. Deleted or removed files stay searchable, and there are duplicate vectors. |
| BUG-04 | High | GitHub | Change detection ignores the repo, so same-path files across repos collide |
| BUG-05 | High | Drive / GitHub | Every file is downloaded on every run, before the change check |
| BUG-06 | High | Drive | One failed download aborts the whole Drive indexing run (no `except`) |
| BUG-07 | High | Search | Queries longer than 77 CLIP tokens give HTTP 500 |
| BUG-08 | High | Frontend | Results disappear while a platform re-indexes, after a reload, and when a job is stuck |
| BUG-09 | High | Frontend | "Index local storage" calls a non-existent endpoint (404) |
| BUG-10 | Medium | Search | Irrelevant or whitespace queries always return results. Duplicate results. |
| … | | | the full list follows |

---

## 3. Security findings

**SEC-01 — Arbitrary file deletion [code + live]**
- **Where:** `app/routes/delete.py:8`, `app/services/delete_service.py:10`
- **Problem:** `DELETE /delete/?filename=` has no auth. It runs `os.path.join("data", filename)` and then `os.remove`. A value like `filename=../app/main.py`, or an absolute path, escapes the `data` folder (on Windows, `os.path.join` with an absolute second argument discards `data`).
- **Live check:** The endpoint answered unauthenticated with `{"status":"error","message":"File not found."}` for a non-existent name, which confirms it is reachable. I did not run a destructive test.
- **Also wrong:** It does not remove vectors from Qdrant and does not reload the caches. A "deleted" file remains searchable.

**SEC-02 — Arbitrary local open/execute [code + live]**
- **Where:** `app/routes/open.py:20`, `app/platforms/local/local_platform.py:222`
- **Problem:** `POST /open/` has no auth. With `platform=local`, any existing `path` is passed to `os.startfile`. For an `.exe`, `.bat`, or `.lnk` file, that means execution.
- **Exposure:** CORS blocks this from browsers, but any local process can call it, and so can the LAN if the backend is ever bound to `0.0.0.0`.

**SEC-03 — No tenant isolation [live]**
- **Where:** `app/routes/search.py:20` (no `get_current_user`). The pickles and Qdrant points have no `user_id`.
- **Live check:** A brand-new QA user with zero connected platforms and zero folders searched `"java notes"` and got 23 results from your local disk and Google Drive.
- **Also leaks across users:** `/dashboard/stats` counts are global, `/scheduler/status` is global and unauthenticated, and the scheduler queue is a single global list. A second user starting indexing replaces the first user's queue (`app/scheduler/queue.py:12`).

**SEC-04 — Upload path traversal [code]**
- **Where:** `app/routes/upload.py:12` (no auth, no prefix, so it is mounted at `POST /`) and `app/services/upload_service.py:52`, which joins `file.filename` unsanitized.

**SEC-05 — Hard-coded secrets**
- Potential secret exposed in `app/auth/jwt_handler.py:6` (JWT signing key, a placeholder value)
- Potential secret exposed in `app/database/db.py:5` (DB credentials in the URL)
- Potential secret exposed in `docker-compose.yml` (POSTGRES_PASSWORD)
- `credentials/` holds `client_secret.json`, `github_oauth.json`, `token.json`, and `google_photos_token.json`. These are git-ignored, which is good. However, `database/users.json` was tracked (it now shows as deleted, so check the git history).
- OAuth access and refresh tokens are stored in Postgres in **plaintext** (`PlatformConnection.access_token`, `refresh_token`, `token_json`).

**SEC-06 — OAuth CSRF [code]**
- **Where:** `app/routes/github.py:72`
- **Problem:** `state = user_id`, and the callback trusts any UUID in `state`. An attacker who knows a victim's UUID can bind the attacker's own GitHub token to the victim's account.
- **Related:** The callback also reflects `str(e)` into HTML without escaping (`github.py:167`), which is a minor XSS vector.

**Other security notes:**
- **Logout does not revoke the JWT.** It only sets a cancel flag. Tokens last 60 minutes and the frontend stores them in `localStorage`.
- **Weak registration validation [live]:** An empty name and an empty password were accepted (HTTP 200).
- **Unvalidated folders [live]:** `POST /platforms/local/folders` accepts any path, including `Z:/does/not/exist`, or a whole drive.
- **Server-side browser and GUI actions:** `webbrowser.open` (GitHub connect), `InstalledAppFlow.run_local_server` (Drive connect), and `tkinter` (`/platforms/local/pick-folder`) all run on the server. They only work when the server is on the user's own desktop, and they block a worker thread with no timeout.
- **`os.system` with an f-string:** `document_search_v2.py:39` and `image_search.py:29` build shell commands this way. The code is CLI-only today, but it is unsafe if reused.
- **Sensitive data on disk:** The `data/` folder holds personal documents (for example, ID and marksheet PDFs). It is git-ignored; keep it that way.

---

## 4. Indexing & platform bugs

**BUG-01 — Scheduler dies on first error, UI stuck forever [code]**
- **Where:** `app/scheduler/scheduler.py:100-116`
- **Problem:** `platform.index()` is not wrapped in try/except. Any exception kills the daemon thread. Examples: Drive not connected (`drive_service.py:30`), a GitHub 401/403/404 such as an empty repo (`github_service.py:27-33`), or a DB error.
- **Effect:** The DB job stays `indexing`, `worker_running` stays True, and the queued platforms never run. The frontend polls forever and shows endless progress.

**BUG-02 — Video semantic/transcript scoring is dead [live]**
- **Where:** `app/vectorstore/insert.py:18-29` stores only fixed payload keys. `video_search.py:183` reads `payload["embedding"]` (always None, so `semantic_score=0`) and `:205` reads `payload["transcript"]` (absent, so `content_score=0`).
- **Live check:** Every video result had `semantic_score 0.0, content_score 0.0`. Only the CLIP frame score and the filename score work.
- **Effect:** Video search can never match spoken content.

**BUG-03 — Qdrant ↔ pickle drift, ghost results [live]**
- **Measured:**

  | Collection | Qdrant | Pickle |
  |---|---|---|
  | Text | 4,223 points | 1,775 chunks |
  | Image | 84 points | 65 items |
  | Video | 115 points | 111 items |

  - 30 text files, 9 image files, and 4 video files exist only in Qdrant.
  - 154 identical duplicate chunk vectors exist.
  - 27 files have a different chunk count in Qdrant than in the pickle.
- **Live check:** A `tiger` search with platform=local returned 5 images. **All 5 paths no longer exist on disk,** and two of them were duplicates.
- **Root causes:**
  - `remove_deleted_files()` (`index_manager.py:180`) prunes the pickles only. It never deletes vectors and never reloads the caches.
  - `delete_file` and `remove_from_index` also touch the pickles only.
  - Removing a local folder (`platforms.py:98`) does not purge that folder's files.
  - Files that are skipped or fail (no text extracted) have their old vectors deleted (`document_indexer.py:48`) before extraction.
  - The migration scripts (`migrate_*_to_qdrant.py`) were probably run more than once on top of normal indexing.

**BUG-04 — GitHub identity collisions [code]**
- **Where:**
  - `is_file_indexed`, `is_file_modified`, and `remove_file_from_index` (`index_manager.py:91,126,165`) match GitHub items by `file_id` (the repo-relative path) only.
  - The search dedupe key is `(platform, file_id)` (`document_search_v2.py:330`, `github_platform.py:305`).
- **Effect:**
  - `README.md` in repo A and repo B compare SHAs against each other, so they re-index on every run.
  - `remove_file_from_index` drops README.md entries from every repo in the pickle.
  - Search shows only one README across all repos.
- **Opening files:** `GitHubPlatform.open` returns the first matching `file_id`, which may be the wrong repo. `get_github_file_url` hard-codes the `main` branch (`github_service.py:166`), so links break for repos on `master` or other default branches.

**BUG-05 — No real "skip unchanged" for cloud [code]**
- **Where:** `github_platform.py:171` and `google_drive_platform.py:79`
- **Problem:** Both download the file first and only then call `process_uploaded_file`, which compares the SHA or `modifiedTime`.
- **Effect:**
  - The comparison works, so unchanged files are not re-embedded.
  - However, the entire repository set and the entire Drive (including large videos and unsupported types — Drive has no extension filter) are downloaded on every run.
  - GitHub also lists every repo's tree twice: once in a counting pass (`:74-101`) and again in the indexing pass, which doubles API calls and rate-limit usage.

**BUG-06 — Drive aborts on first bad file [code]**
- **Where:** `google_drive_platform.py:72-116` is `try/finally` with no `except`.
- **Problem:** Google Forms, Drawings, Sites, shortcuts, and files over the export size limit fail in `get_media`/`export_media`. That exception propagates and ends the whole run (and then BUG-01 applies).
- **Other Drive issues:**
  - Names containing `/` or characters that are illegal on Windows break `temp/<name>`.
  - A native Google Doc named `a.b` loses `.b` when it is exported (`drive_service.py:83`).
  - `get_drive_service` rebuilds the client, with a DB query, for every file.
  - Refreshed credentials are never saved back.
  - **Deleted Drive files are never removed** (`remove_deleted_files` skips google_drive, and there is no Drive deletion check).
  - `last_modified` stores the `modifiedTime` string while local files store a float mtime, so the field's type is inconsistent.

**BUG-11 — Pagination gaps (GitHub) [code]**
- `list_repositories` (`github_service.py:52`) fetches only the first page, so at most **30 repos** are indexed.
- The contents API has no pagination either.
- Drive pagination (`google_drive_platform.py:136`) is correct.

**BUG-12 — Deleted GitHub files are never removed [code]**
- The call to `remove_deleted_github_files()` is commented out (`github_platform.py:205`).
- If it were enabled, it would crash: `get_all_repository_paths` does not exist in `github_service.py`.

**BUG-13 — `PlatformManager.index()` is broken [code]**
- **Where:** `platform_manager.py:37,51`
- **Problem:** It calls `platform.index()` with no arguments, but every platform requires `user_id`, so it raises `TypeError`. It is currently unused, but it is a trap. `BasePlatform` declares a different signature too.

**BUG-14 — Progress numbers are wrong [code + live]**
- **Local:** The total counts every file, including unsupported ones. Failures and unsupported files still increment `indexed_files` (`local_platform.py:108`, because `process_uploaded_file` swallows exceptions).
- **Drive:** Folders are counted in the total but skipped, so progress never reaches 100% naturally.
- **Scheduler completion:** On completion the scheduler forces `indexed_files = total_files` and `status=completed`, even when the run was cancelled (`scheduler.py:152-156`).
- **Invalid platforms [live]:** `POST /scheduler/start` with `platforms:["dropbox"]` returned 200 and reported `completed_platforms:["dropbox"], priority_completed:true`.

**BUG-15 — Cancel only stops the current platform [code]**
- Each platform's `finally: clear_cancel(user_id)` clears the flag, so the next queued platform still runs.
- Logout calls cancel, so logging out does not stop the queue.

**BUG-16 — Files with no extractable text are re-processed forever [code]**
- **Where:** `document_indexer.py:116`, `audio_indexer.py:38`
- **Problem:** When extraction yields nothing (scanned PDF without OCR, silent audio, empty or corrupt file), nothing is stored. The file is "not indexed" on every run, so it is re-extracted and re-transcribed every time.
- **Related gaps:**
  - Documents: `.md` is unsupported. Images in the document pipeline are OCR'd only for jpg and png.
  - **Image OCR for `.webp`/`.avif`:** It depends on PaddleOCR, and the startup log shows Paddle runs with `use_gpu=False` while every other model uses CUDA.

**BUG-17 — Indexing cost is O(n²) [code]**
- **Where:** `save_index` (`index_manager.py:52`)
- **Problem:** For **each file**, it rewrites the whole pickle and then fully reloads and rebuilds the caches. `load_index` also re-reads the whole pickle 2–3 times per file. The video pickle stores the full `clip_embeddings` list once **per transcript chunk**, which inflates it.

**BUG-18 — Shared temp dirs [code]**
- `temp_frames/` and `temp/` are fixed paths, so concurrent indexing of two videos, or of Drive and GitHub at once, collides.
- `temp_frames/*.jpg` and `temp/` files are **tracked in git** despite `.gitignore`.

**BUG-19 — Scheduler / index race [code]**
- `create_queue` (`queue.py:21`) calls `reset_status()`, which sets `worker_running=False` while a worker may still be running. Status then lies, and the queue is replaced mid-run.
- `/index/` creates DB jobs even when the worker is already running for someone else.

---

## 5. Search bugs

**BUG-07 — HTTP 500 on long query [live]**
- **Problem:** A ~300-word query fails with `ValueError: Sequence length … 302 … max_position_embeddings: 77`.
- **Cause:** The CLIP text encoder is called without `truncation=True` (`clip_extract.py:44`, `video_search.py:128`).
- **Frontend effect:** It then hits `response.json()` on the text body `Internal Server Error`, so the user sees nothing (see FE-05).

**BUG-10 — Relevance thresholds [live]**
- **Nonsense queries:**
  - `"xqzv wplk qqq"` returned 19 results.
  - `"Find my government documents"` returned pizza and helicopter images as the top hits.
  - **Cause:** For images, `MIN_FINAL_SCORE=0.05` while raw CLIP cosine similarity is about 0.2 for anything (`image_search.py:18`). Video uses the same 0.05 threshold.
- **Whitespace query:**
  - `"   "` returned documents with score 0.5.
  - **Cause:** `search_documents` checks `if not query` without stripping. `get_title_score` then sees `"   " in filename` and returns 0.9 for any filename containing two or more spaces.
- **Duplicates in one response:**
  - `Hall ticket.jpeg` appeared 3 times and `helicopter…webp` twice. These are the Qdrant duplicates.
  - Image search does not dedupe by file (audio and video do dedupe, but by **basename**, which wrongly merges different files with the same name).

**BUG-20 — Document scoring keyed by basename [code + live]**
- **Where:** `semantic_lookup`, `content_cache`, and `fuzzy_cache` (`document_search_v2.py:282,305`) are keyed by `doc["file"]` (the basename).
- **Live check:** Several basenames are shared by 2 files (for example `Calculator.docx` and `jury 1.docx`, from local and Drive).
- **Effect:**
  - A file inherits another file's content and semantic score.
  - `DOCUMENT_CONTENT_LOOKUP` concatenates chunks from different files with the same name.

**BUG-21 — Title match can't rescue a file [code]**
- Ranking only considers files that are in Qdrant's top 500 *chunks* (`limit=500`).
- A file whose name matches exactly, but whose chunks rank below 500, is never returned.

**BUG-22 — Results limits inconsistent [live]**
- Documents return the top 10, and images, audio, and video return the top 5 each, all **per platform**. "All platforms" therefore returns up to 3×.
- Results are concatenated and never re-ranked across types or platforms, except within GitHub. As a result, an image scoring 0.38 is listed after documents scoring 0.317.
- **Invalid inputs give empty results instead of 422 [live]:** `platform="dropbox"`, `search_type="spreadsheet"`, and case variants like `"Document"` all return 200 with `[]`.

**BUG-23 — Stale paths in results [live]**
- Google Drive results carry `path: "temp\\<name>"`, a file that was deleted after indexing.
- Opening still works because it uses the `file_id`, but any display of the path is misleading.

---

## 6. Frontend bugs [code unless noted]

**FE-01 / BUG-08 — Results filtered out client-side**
- **Where:** `PageDashboard.tsx:342`
- **Problem:** Results are dropped unless the platform is in `indexedPlatforms`. That list is derived only from jobs whose status is `completed` (`App.tsx:508`).
- **Cases where valid backend results vanish:**
  - During any re-index (the status is `indexing`/`queued`).
  - For about 1 second after a page reload (the list starts as `[]`).
  - Forever if a job is stuck (BUG-01).
- **Local results:** They are also dropped when `selectedFolders` is empty.
- **Per the rules of this audit,** this is a **FRONTEND bug**.

**FE-02 — Missing endpoint (verified)**
- `indexLocalStorage()` calls `POST /platforms/local/index`, which returns **404** [live]. It is used in `PageConnection.tsx:121`.

**FE-03 — Missing module (verified)**
- `PageIndexingCenter.tsx:9` imports `../services/scheduler`, which does not exist.
- `tsc --noEmit` fails [live]. The Vite build succeeds only because esbuild drops the unused import.

**FE-04 — CORS / origin mismatch [live]**
- The dev server runs at `--port=3000 --host=0.0.0.0`.
- The backend allows only `http://localhost:3000` and `http://127.0.0.1:5173`. Preflight from `http://127.0.0.1:3000` or a LAN IP returned **400**, so every API call fails if the app is opened that way.
- The `127.0.0.1:5173` entry is dead config.

**FE-05 — Error handling**
- `search.ts`, `dashboard.ts`, and `localStorage.ts` read `data.message`, but FastAPI returns `detail`. Users get generic messages.
- `index.ts` passes a 422 `detail` array, which renders as `[object Object]`.
- On a 500 with a non-JSON body, `response.json()` throws a parse error.
- `performSearch` catches errors with `console.error` only. No message is shown, and previous results stay on screen (stale).

**FE-06 — Open-file errors invisible [live contract]**
- `/open/` returns **HTTP 200** with `{"status":"error"}` for a missing file, a missing Drive id, or an unknown platform.
- `openFile` only checks `response.ok`, so the user gets no feedback.
- Local open succeeds silently on the server (a window opens on the server machine).

**FE-07 — Fake or broken result metadata**
- **Relevance** is hard-coded to `98%`/`84%` (`PageDashboard.tsx:1142`); the backend `score` is ignored.
- **Size and Last Modified** are always blank (the backend never sends them).
- **Snippet:** It shows `ocr_text ?? file`, so documents show their filename, and the audio/video `preview` is ignored.
- **Suggestions:** The "Recent / Favorites / Most searched" lists come from `MOCK_FILES` (fake data).
- **React keys:** `key={file.id}` is undefined for every result, which causes duplicate-key warnings and mis-rendered or stale cards.

**FE-08 — Race conditions / duplicate requests**
- **No search cancellation:** There is no abort or request sequencing. Preset buttons and dropdowns stay enabled while a search runs, so an older response can overwrite a newer one.
- **Changing filters doesn't re-search:** Changing the type or platform after a search only filters the old results client-side. Switching from "Images" to "All" shows only the images previously fetched.
- **Duplicate polling:** `/index/jobs` is polled every **1 s by both** `App.tsx:480` and `PageDashboard.tsx:281`, which is 2 requests per second for the whole session, even when idle.
- **State update inside an updater:** `setIndexingState` is called inside a `setPlatforms` updater (`App.tsx:453`), which is a side effect in a state updater.
- **Extra logging:** There are many `console.log`/`console.table` calls on every render.

**FE-09 — Types**
- `AuthUser.id: number`, but the backend returns a UUID string (`types.ts:72`).

---

## 7. API inventory (live results)

| Method | Endpoint | Auth | Result |
|---|---|---|---|
| GET | `/` | none | 200 |
| POST | `/auth/register` | none | 200. Duplicate email → 400. Bad email → 422. **Empty name/password accepted.** |
| POST | `/auth/login` | none | 200 / 401 (≈0.27 s, bcrypt) |
| GET | `/auth/profile` | JWT | 200. No token → 401. Bad token → 401. |
| GET | `/auth/login-state` | JWT | 200 |
| POST | `/auth/logout` | JWT | does not revoke the token |
| POST | `/search/` | **none** | 200 in 1.3–2.3 s (all/all), 0.4–0.7 s (one platform). Bad JSON or missing query → 422. Long query → **500**. |
| GET | `/search/health`, `/index/health`, `/open/health`, `/delete/health` | none | 200 |
| GET | `/upload/health` | — | **404**. The upload router has no prefix, so its health check is at `/health`. |
| POST | `/` (upload) | **none** | 422 without a file. Path traversal (SEC-04). |
| DELETE | `/delete/?filename=` | **none** | SEC-01 |
| POST | `/open/` | **none** | always 200, even for errors (FE-06) |
| POST | `/index/` | JWT | 422 / 401 as expected. No platform-name validation. |
| GET | `/index/jobs` | JWT | 200 |
| GET | `/scheduler/status` | **none** | global state |
| POST | `/scheduler/start` | JWT | accepts unknown platforms (BUG-14) |
| GET | `/dashboard/stats`, `/dashboard/platforms` | JWT | 200. Stats are global, not per user. `connected_platforms` actually counts *completed* scheduler runs and resets when the server restarts. The router is defined twice in `dashboard.py`. |
| GET/POST/DELETE | `/platforms/local/folders` | JWT | 200. Paths are not validated. |
| POST | `/platforms/local/pick-folder` | JWT | opens a tkinter dialog on the server (blocking) |
| POST | `/platforms/local/index` | — | **404**, but the frontend calls it |
| GET | `/platforms/github/connect`, `/status`; POST `/disconnect` | JWT | status 200 |
| GET | `/platforms/github/callback` | none | invalid state → friendly HTML. CSRF issue (SEC-06). |
| GET | `/platforms/google-drive/connect`, `/status`; POST `/disconnect` | JWT | `connect` blocks until browser consent completes |
| GET | `/docs`, `/openapi.json` | none | 200. Schemas declare no response models except auth. |

## 8. Performance (measured)

| Metric | Result |
|---|---|
| Startup | It loads SentenceTransformer, CLIP, Whisper, and PaddleOCR eagerly, plus all pickles. That took tens of seconds on this machine; I did not capture an exact number. Eager loading happens twice: at import (`document_search_v2.py:25`, `video_search.py:16`, and `clip_utils.py`, which also loads `image_index.pkl` at import) and again in the startup hook. |
| Search, all/all | **1.5–2.3 s.** The previous 30–40 s figure is **no longer accurate.** |
| Search, one platform | 0.4–0.7 s for documents or all types. Images, audio, and video take 0.05–0.3 s. |
| Repeated identical search | 1.66 / 1.71 / 1.74 s. Results are not cached. |
| 4 concurrent searches | each 5.3 s |
| 8 concurrent searches | each 10.5 s. Requests are effectively serialized, so latency grows linearly. |

**Bottleneck:** In `search_documents` (`document_search_v2.py:296-310`), each call computes `get_file_fuzzy_score` and `get_content_score` for **every file in the cache**, whatever the platform. That includes an O(query_words × content_words) `fuzz.ratio` loop. These steps are not covered by the timing prints: the logged phases total about 0.06 s, but the platform total is about 0.55 s.

With `platform=all`, this runs **3 times** (once per platform). The query is also embedded 12 times: 3 platforms × 4 modalities, using both MiniLM and CLIP. Disk I/O is *not* involved in search: the caches are in memory and Qdrant takes 0.01–0.04 s.

For indexing, the bottleneck is BUG-17 (whole-pickle rewrite and cache reload per file) plus BUG-05 (full re-download).

## 9. Repo hygiene

- **`requirements.txt` is UTF-16 encoded.** pip usually detects the BOM, but many tools will choke on it. Its contents also do not match the imports (for example, the qdrant/Paddle versions).
- **Tracked files that shouldn't be:** `audio_index.pkl` and `video_index.pkl` are tracked despite `.gitignore`. `temp_frames/` (hundreds of JPGs), `temp/`, and `import_log.txt` are tracked too.
- **Leftover scripts:** About 25 ad-hoc `test_*.py` scripts sit at the root, and none are real tests. `document_indexer.py` has leftover `print("1")…print("8")` debug lines.
- **Infrastructure:** Qdrant is missing from `docker-compose.yml`. Hosts, ports, and URLs are hard-coded (`127.0.0.1:8000`, the callback URL, the DB URL).
- **Deprecated APIs:** `@app.on_event` and `datetime.utcnow` are deprecated.

## 10. Recommended fix order (no fixes applied)

1. SEC-01/02/03/04: add auth and per-user scoping to search, open, delete, and upload, and sanitize paths.
2. BUG-01 and BUG-06: add per-file and per-platform exception handling so indexing can't wedge.
3. BUG-03: make Qdrant the single source of truth, or delete vectors wherever the pickles are pruned. Then rebuild the index once to remove the orphans and duplicates.
4. BUG-02 and BUG-07: fix the video payload fields and enable CLIP truncation.
5. FE-01 and FE-02: stop hiding backend results client-side, and fix the local-index endpoint.
6. BUG-04 and BUG-05: use a `(repo, path)` identity, and check SHA / `modifiedTime` *before* downloading.
7. Raise the image/video thresholds, strip queries, dedupe by full identity, and validate `platform` and `search_type`.
