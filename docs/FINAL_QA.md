# Final QA (v1.0.0)

The audit of [QA_REPORT.md](QA_REPORT.md) was re-run against the code at the end of Phase 7B.

**Setup:**
- **Date:** 2026-10-10.
- **Machine:** a Windows 11 laptop with an RTX 3050 (4 GB).
- **Backend:** run from this branch on **:8001**, with a scratch Postgres database
  (`cogniseek_finalqa`) and a scratch Qdrant prefix (`finalqa_`). No real data was touched.
- **Data:** two throwaway users and `sample-data/` (4 documents and 1 image).
- **Cleanup:** the users were deleted through `DELETE /auth/account`, then the database and the
  `finalqa_*` collections were dropped.

**Result: 43 of 43 probes passed.**

## Before → after

| Area | Before (QA_REPORT, Phase 0) | After (v1.0.0) |
|---|---|---|
| `POST /search/` without a token | 200: anyone could search everything | **401** |
| `/upload/`, `/delete/{name}`, `/open/` without a token | open (SEC-01/04, FE-06) | **401** |
| `/index/jobs`, `/dashboard/stats`, `/platforms/local/folders`, `/auth/export`, `/platforms/github/connect` without a token | some open; dashboard stats were global | **401**; stats are per user |
| Bad JWT on `/auth/profile` | 401 | 401 |
| `POST /auth/logout` | did not revoke the token | the token is **revoked** (`/auth/profile` → 401 afterwards) |
| Register with an empty password / blank name | **accepted** | **422** |
| Search with an empty query / a 5000-character query | 422 / **500** | 422 / **422** |
| Search with an unknown platform, `limit=0`, malformed JSON | partly unvalidated | **422** |
| Index an unknown platform | accepted (BUG-14) | **422** |
| Register a folder outside the allowed roots (`C:/Windows`), or `<root>/../..` | accepted, unvalidated | **400** |
| Download `<root>/../.env` / `C:/Windows/win.ini` | path traversal (SEC-04) | **404** (only files in the user's own ledger) |
| `DELETE /delete/..%2F.env` | traversal | **404** |
| Google / GitHub callback with a forged `state` | CSRF issue (SEC-06) | **303** to the frontend with `reason=invalid_state`; nothing stored |
| User B searches for user A's files | shared global index | **0 results** |
| User B downloads A's file / reads A's job errors / cancels A's job | no ownership checks | **404 / 404 / 404** |
| User A downloads their own file | — | 200 |
| A burst of about 95 searches by one user in under a minute | no rate limiting | 61 × 200, then **33 × 429** (`SEARCH_RATE_LIMIT` = 60/min) |
| `GET /upload/health` | 404 (no router prefix) | route present at `/upload/health` (OpenAPI) |
| `POST /platforms/local/index` (called by the old frontend) | 404 | removed; the frontend uses `POST /index/` |
| Google Drive `connect` | blocked until browser consent completed | returns the authorization URL immediately (web flow) |
| Search `xqzv` (nonsense) | results returned | **0 results, 0 possible matches** |
| Delete account | not available | **200**; vectors, ledger, connections and user removed |

## Search edge cases (sample-data)

| Query | Results | Possible matches | Time |
|---|---|---|---|
| `recipe` | 1 | 0 | 0.15 s (first query) |
| `notes` | 2 | 0 | 0.11 s |
| `red circle` | 1 (the image) | 0 | 0.11 s |
| `xqzv` | 0 | 0 | 0.10 s |
| `jva` | 0 | 0 | 0.10 s |

`jva` finds nothing here because no file in `sample-data` matches "java". The typo tolerance is
covered by the unit tests and the evaluation set.

## Performance snapshot

### Startup (process launch → `/ready` 200, models preloaded)

| | Before | After |
|---|---|---|
| First start after the laptop had been idle (cold OS file cache) | "tens of seconds", not captured; models loaded twice | **139 s** |
| Restart (warm file cache) | — | **79 s** |
| Docker, restart with the model volume | — | about 30 s (measured in Phase 7A, Linux CPU image) |

Startup is dominated by loading MiniLM, CLIP, Whisper and PaddleOCR from disk. Setting
`PRELOAD_MODELS=false` makes startup near-instant, but the first request then pays the load time.

### Search latency (warm)

8 queries; 10 rounds single, then 10 rounds of 8 concurrent. Every request returned 200. For this
measurement only, the scratch backend was restarted with `SEARCH_RATE_LIMIT=100000/minute` so
the limiter would not interfere.

| | Before | After |
|---|---|---|
| Single search, `all` platforms | 1.5–2.3 s | p50 **0.052 s**, p95 **0.083 s** (n = 80) |
| 8 concurrent searches | **10.5 s each** (serialized) | p50 **0.201 s**, p95 **0.260 s** (n = 80) |

**Caveat:** this index is tiny (5 files). Over the owner's real index (hundreds of files,
83 eval queries), the search p50 is about **0.18 s** ([EVALUATION.md](EVALUATION.md)). The
"before" numbers were taken on the owner's index of that time.

### Indexing throughput

Benchmark from [perf/RESULTS.md](perf/RESULTS.md): 69 files, 211 MB, run sequentially with GPU OCR.

| Type | Before | After |
|---|---|---|
| Documents | 10.5 files/min | 37.6 files/min |
| Images | 65.9 files/min | 271.8 files/min |
| Audio | 42.3 audio-min/min | 46.8 audio-min/min |
| Video | 13.4 video-min/min | 28.0 video-min/min |
| Whole benchmark (parallel) | 347 s | **93 s** (292 s with CPU OCR) |
| 50% of the files searchable | 191 s | **31 s** |

In this run, `sample-data` indexed in 3.8 s, end to end through the job queue. "Where the time
went" showed 2.7 s of image OCR, 0.6 s of CLIP, 0.16 s of MiniLM and 0.21 s of Qdrant upserts.

## Automated checks at release

| Check | Result |
|---|---|
| Backend tests (pytest) | see the release report / CI Backend run |
| Frontend (lint, typecheck, Vitest coverage, build) | CI Frontend |
| gitleaks (full history), pip-audit, npm audit, CodeQL | CI Security |
| Docker images build | CI Docker |
| Playwright e2e against the Docker stack | CI E2E |

The links to the green runs are in the release report.

## Remaining known issues

These are the documented limitations, not regressions:
- Shared Drives are not indexed.
- There is no query expansion.
- Visual-only recall is about 70% for images and 50% for video.
- Indexed text is not encrypted at rest.
- The token is stored in `localStorage`.

See the README's *Known limitations* and [SECURITY.md](SECURITY.md#known-gaps).
