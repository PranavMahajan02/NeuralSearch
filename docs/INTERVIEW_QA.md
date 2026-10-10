# Interview preparation: CogniSeek

Questions an interviewer is likely to ask about this project, with answers grounded in the code
and the measured numbers. The numbers come from [EVALUATION.md](EVALUATION.md),
[perf/RESULTS.md](perf/RESULTS.md) and [FINAL_QA.md](FINAL_QA.md).

## 1. The elevator pitch

**Q1. What is CogniSeek, in one minute?**
A self-hosted, multi-user search engine over your own files: local folders, Google Drive and
GitHub. It indexes documents, code, images, audio and video, and lets you search by meaning
("polar bear cubs") as well as by name. Under the hood: FastAPI, Postgres, Qdrant and Redis behind
Caddy, plus a React 19 frontend. The models are MiniLM for text, CLIP for images and video frames,
faster-whisper for speech and PaddleOCR for scanned text.

**Q2. Why did you build it?**
My files are spread across a laptop, Drive and GitHub, and each has its own weak search that only
matches names. I wanted one box that finds a photo by what it shows and a lecture by what was said.
I also wanted a project that forced me through the full lifecycle: ML, backend, security, ops and CI.

**Q3. What are you proudest of?**
The measurement discipline. Every relevance threshold is calibrated against an 83-query labelled
evaluation set: nonsense queries went from 61 false positives to 1 while non-visual P@5 rose to
0.935. Indexing went from 347 s to 93 s on a fixed benchmark, and the eval was re-run to prove
quality didn't regress.

**Q4. What is the hardest part?**
Visual search precision. CLIP similarity scores are noisy and close together, so a fixed cut-off
either floods the results or hides real matches. The solution is a calibrated evidence gate plus a
separate, capped "Possible matches" tier for weaker visual hits.

**Q5. What would you do differently?**
Start with the evaluation harness and the test database isolation on day one. Several early
"improvements" were tuned by eye, and some of them overfit to file names (see the STAR story in §9).

## 2. Architecture

**Q6. Walk me through the architecture.**
- **Caddy** terminates TLS, serves the SPA, sets a strict CSP and proxies `/api/*`.
- **The FastAPI process** holds the API, the models and an in-process indexing worker.
- **Postgres** stores users, connections, the job queue, the file ledger and revoked tokens.
- **Qdrant** stores vectors and chunk payloads in five `cogniseek_v2_*` collections.
- **Redis** backs the rate limits.
- Only Caddy publishes ports; the data services live on an internal Docker network.

**Q7. Why Qdrant and not pgvector?**
- **Payload filtering:** fast filtering by `user_id`, which every search applies.
- **Named collections per modality:** text and CLIP vectors have different dimensions.
- **Good HNSW performance** without tuning Postgres.

The trade-off is a second datastore to back up, which `scripts/backup.py` handles together with
Postgres.

**Q8. Why five collections?**
They separate the modalities, which have different vector spaces and different score
distributions. There is one collection each for text (documents, code, OCR text; MiniLM 384-d), image (CLIP
512-d), audio (transcript chunks), video (transcript chunks) and video_frames (CLIP). Each modality has its own calibrated threshold.

**Q9. Why is the indexing worker in the API process?**
The models take about 2 GB of memory. A separate worker would load them twice on a single machine.
The job queue is in Postgres (`SELECT … FOR UPDATE SKIP LOCKED`), so moving the worker to its own
process later is a deployment change, not a redesign. `WORKERS` must stay 1 for this reason.

**Q10. How does a search request flow?**
1. JWT check and rate limit.
2. The query is embedded with MiniLM and CLIP.
3. The vector searches run, each filtered by `user_id`.
4. A trigram file-name search runs in Postgres.
5. The results are merged per file, then the evidence gates and the ranking are applied.
6. Weak visual hits go to "Possible matches" (max 3).
7. Paths are normalized for display, and internal temp paths are hidden.

**Q11. How does indexing flow?**
1. List the files on the platform.
2. Compare against the ledger (modified time, size, revision) and skip unchanged files **before
   downloading**.
3. Download in parallel: `INDEX_IO_WORKERS=4`, up to `INDEX_PREFETCH=8` in flight.
4. Extract: text, OCR, frames, transcription.
5. Embed under per-model locks.
6. Upsert into Qdrant, update the ledger.
7. Delete the vectors of files that disappeared.
8. Record `stage_timings`.

**Q12. How do you handle Google Drive and GitHub specifics?**
- **Drive:** OAuth web flow with state + PKCE and the `drive.readonly` scope. Google Docs are
  exported. A `CooldownGate` handles 429s and shares the back-off across threads. Each thread has
  its own `AuthorizedHttp`.
- **GitHub:** OAuth and the Git Trees API on the default branch, with a per-thread
  `requests.Session`.

## 3. Search and ML

**Q13. Why MiniLM and CLIP rather than one bigger model?**
They run on a 4 GB laptop GPU, or on a CPU. MiniLM is fast and good at short passages; CLIP is the
standard for text-to-image matching. A larger multimodal model would make indexing several times
slower for a gain I couldn't prove on my eval set.

**Q14. How are documents chunked?**
Into overlapping passages, so a match can be highlighted in the result and no idea is cut at a
boundary. Code is chunked by lines. Each chunk payload stores the text, the page or offset, and the
file id.

**Q15. What is the "evidence gate"?**
A per-modality rule that decides whether a hit is strong enough to show. A file qualifies on:
- a strong vector score, or
- file-name evidence, or
- the agreement of several weaker signals.

Visual-only hits need a higher calibrated CLIP score; below it, and above a lower bound, they go to
"Possible matches".

**Q16. How did you calibrate the thresholds?**
With the labelled eval set: 83 queries with relevant files, including nonsense negatives like
"xqzv". I swept the thresholds and picked the ones that keep negatives at about zero while
maximizing P@5. Calibration and history: [EVALUATION.md](EVALUATION.md).

**Q17. What are the current quality numbers?**
- **Non-visual P@5:** 0.935.
- **Visual-only images:** 0.719.
- **Visual-only video:** 0.50.
- **Code:** 0.357.
- **False positives:** 0 on the non-visual negatives; nonsense false positives went 61 → 1 overall.
- **Search latency:** p50 about 0.18 s warm.

**Q18. Why is code search weak?**
MiniLM is trained on natural language, not code, and the code queries in the eval are conceptual
("retry with backoff"). A code-specific embedder is on the roadmap. File-name and identifier
matching still works.

**Q19. How do you search video?**
- **Speech:** Whisper transcribes it into searchable chunks.
- **Visuals:** CLIP embeds one frame every 5 s. I measured every 2 s; it cost 4.8–6.6× more frames
  and didn't improve the eval, so I rejected it.

**Q20. How do you handle typos?**
Postgres trigram similarity on file names, plus a fuzzy fallback for single words ("jva" → "java").
A typo combined with an unmatched word can return nothing, which is documented.

**Q21. Why not query expansion?**
It is on the roadmap. Without it, "government documents" doesn't find a passport scan named
`scan01.jpg`. Expansion raises recall, but it also raises false positives, so it needs its own
evaluation pass.

**Q22. How do you rank?**
A weighted score per file:
- the best chunk score;
- a bonus when several modalities agree;
- a file-name match boost;
- a length normalization (`close_length`), so a short exact name beats a long one that merely
  contains the word.

The weights are fixed and validated on the eval set.

## 4. Indexing performance

**Q23. How did you make indexing 3.7× faster?**
I measured first: per-stage timings on a fixed 69-file, 211 MB benchmark. OCR on CPU dominated.
The changes:
- a parallel pipeline: I/O workers, a prefetch window, and per-model locks instead of one global lock;
- opt-in GPU OCR.

The result: 347 s → 93 s, and 50% of the files searchable after 31 s instead of 191 s.

**Q24. What did you try that didn't work?**
- **One lock for all GPU models** (`GPU_SERIALIZE`): 115 s vs 93 s.
- **Batched Whisper:** slower end-to-end on a 4 GB GPU.
- **2 s video frames:** more cost, no quality gain.

All three are documented in [perf/RESULTS.md](perf/RESULTS.md) with numbers.

**Q25. Why is GPU OCR opt-in?**
`paddlepaddle-gpu` needs CUDA 12 and cuDNN 8 and adds about 480 MB of VRAM. The default install has
to work everywhere. `OCR_DEVICE=auto` picks the GPU when the CUDA build is installed
(`requirements-gpu.txt`); without it, the run takes 292 s on CPU OCR.

**Q26. How do you show users where the time goes?**
Every job stores `stage_timings` (seconds per stage). The Indexing Center renders them as a
"Where the time went" bar list.

**Q27. How do you avoid re-downloading unchanged files?**
The ledger stores the modified time, the size and the platform revision per file. The connector
listing is compared with the ledger before any download, so unchanged files cost one metadata row.

**Q28. How do you prioritize during onboarding?**
The user picks a priority platform. Its job is enqueued first, and the dashboard shows a banner
until the files from that platform are searchable.

## 5. Security

**Q29. How do you isolate users?**
- Every Qdrant query carries a `user_id` filter, and every SQL query is scoped by the current user.
- There are tests for cross-user access on search, download, jobs and connections.
- File downloads resolve through the ledger, never through a client-supplied path.

**Q30. How do you store OAuth tokens?**
Fernet-encrypted (`TOKEN_ENCRYPTION_KEY`) in `platform_connections`. `scripts/rotate_token_key.py`
re-encrypts every token in one transaction and verifies each value before committing.

**Q31. Why PKCE for a confidential client?**
- **Defence in depth:** it binds the authorization code to the session that started the flow, so a
  leaked code is useless.
- **State:** the `state` parameter is signed, single-use and expires.
- **GitHub:** it doesn't enforce PKCE for OAuth Apps, so state is the main protection there.

**Q32. How do JWTs work here, and how do you revoke them?**
Short-lived HS256 tokens with a `jti`. Logout and account deletion add the `jti` to a revocation
table, which is checked on every request. Rotating `JWT_SECRET_KEY` ends every session.

**Q33. What about path traversal?**
- **Local folders:** the backend resolves the path and checks that it is inside an allowed root
  (`/data` in Docker).
- **Symlinks** that escape the root are rejected.
- **Downloads** go through the file ledger.

The probes are in [FINAL_QA.md](FINAL_QA.md).

**Q34. What does the CSP look like?**
- `default-src 'self'`, no inline scripts, `frame-ancestors 'none'`;
- images from `self`, `data:` and `blob:`.

The Playwright e2e test fails on any CSP violation.

**Q35. What are the known security gaps?**
- Indexed text is not encrypted at rest; use disk encryption.
- The access token sits in `localStorage`, so it is exposed to XSS, mitigated by the CSP.

The planned fix is an HttpOnly SameSite cookie plus a CSRF token. Both gaps are in
[SECURITY.md](SECURITY.md#known-gaps).

**Q36. How do you prevent secrets in logs?**
- A logging filter redacts tokens, JWTs, OAuth codes and state, and passwords.
- Caddy logs without query strings.
- Startup errors name the missing setting, never its value.
- gitleaks scans the full history in CI.

**Q37. What's in the security CI?**
- gitleaks over the full history;
- pip-audit (with OSV severity lookup) and npm audit, both against an allowlist with a reason and
  a review date per entry;
- CodeQL for Python and TypeScript;
- Dependabot weekly.

**Q38. How do you rate-limit?**
Redis-backed limits per IP and per user on login, registration, search and OAuth starts. Without
Redis (development only) the limits are in memory. Production refuses to start without `REDIS_URL`.

## 6. Data and database

**Q39. Why Postgres for the job queue instead of Celery/RQ?**
- One less service.
- Jobs are transactional with the ledger.
- `SKIP LOCKED` gives safe concurrent claims.

The queue load is tiny: a few jobs per user per day.

**Q40. How do you manage schema changes?**
With Alembic: 15 migrations, all reversible. CI runs `alembic upgrade head` and `alembic check`
against a real Postgres, which proves the models and the migrations agree. The backend migrates on
start in Docker.

**Q41. How do backups work?**
`docker compose run --rm backup` dumps Postgres and snapshots the Qdrant collections into one
encrypted archive. `restore.py` has a `--dry-run` mode and a scratch-restore mode that verifies the
point counts without touching the live data.

**Q42. What about account deletion and export?**
Users can export their data, and they can delete their account. Deletion removes the vectors, the
ledger rows, the connections (and revokes the grants at Google/GitHub) and the user row.

## 7. Testing and CI

**Q43. How is the backend tested?**
470+ pytest tests against:
- a throwaway Postgres database per run;
- an in-memory Qdrant;
- fake embedders.

No real models are loaded and no real Google/GitHub calls are made (the `responses` library mocks
HTTP). The tests never touch the real collections.

**Q44. And the frontend?**
- **Vitest + Testing Library + MSW:** 73 tests, coverage ≥ 70%.
- **Playwright e2e:** register → onboarding → index → search → download → delete account, with axe
  accessibility checks in light and dark mode.

**Q45. What runs in CI?**
Five workflows:
- **Backend:** ruff, the mypy baseline, migrations, pytest with coverage, and a startup smoke test.
- **Frontend:** lint, typecheck, coverage, build, depcheck.
- **Security:** see Q37.
- **Docker:** builds the images.
- **E2E:** the full Docker stack plus Playwright.

**Q46. What is the mypy baseline?**
The codebase predates strict typing, with 85 existing errors. `scripts/check_mypy_baseline.py`
fails CI only on errors that are not in `mypy-baseline.txt`, so new code must be clean and the
count can only go down.

**Q47. How do you test the OAuth flows without real providers?**
- The provider endpoints are mocked with `responses`.
- The tests check state signing and expiry, PKCE verifier handling, granted-scope verification (a
  token without `drive.readonly` is revoked and not stored) and the callback error paths.

**Q48. How do you test search quality?**
Separately from the unit tests. `scripts/eval_search.py` runs the 83 labelled queries against a
live backend, and `compare_eval.py` diffs two runs per query, so a regression is visible as a
specific query getting worse.

## 8. Frontend and UX

**Q49. Why React 19 + TanStack Query?**
TanStack Query handles caching, polling (indexing progress) and invalidation declaratively.
The API types are generated from the backend's OpenAPI schema (`npm run gen:api`), so frontend
and backend can't drift silently.

**Q50. How do you show indexing progress?**
The Indexing Center polls the active job, shows per-file errors, supports cancel, and keeps a run
history with the stage-timing breakdown.

**Q51. Accessibility?**
axe runs in the e2e test in both themes. Components are keyboard-reachable, and the results list
uses semantic headings and landmarks.

## 9. Behavioural (STAR stories)

**Q52. Tell me about a security bug you found and fixed. (PKCE)**
- **S:** The Google OAuth flow used only a `state` parameter.
- **T:** Harden it without breaking existing connections.
- **A:**
  - added PKCE: the verifier is stored server-side keyed by the signed state, and the challenge is
    sent to Google;
  - made state single-use with an expiry;
  - added tests for replay, expiry and a mismatched verifier.
- **R:** An intercepted authorization code can no longer be redeemed. All OAuth tests pass, and the
  dev and Docker callback URLs are documented.

**Q53. Tell me about a time a user saw confusing behaviour. (Granted scope)**
- **S:** Users connected Drive, and then indexing failed with 403s.
- **T:** Find out why.
- **A:**
  - Google's consent screen has a checkbox per scope, and users weren't ticking "See and download
    your Drive files", so we got a token without `drive.readonly`.
  - The callback now checks the **granted** scopes. A token without Drive is revoked, nothing is
    stored, and the UI explains which box to tick.
- **R:** The failure moved from a confusing indexing error to a clear message at connect time, with
  a test for it.

**Q54. Tell me about a time your metrics misled you. (Visual overfit to filenames)**
- **S:** Visual search P@5 looked great after a tuning round.
- **T:** Verify it before shipping.
- **A:**
  - I noticed that many "visual" eval queries had the query word in the file name, so the
    file-name boost was doing the work.
  - I split the eval into visual-only queries, whose relevant files don't contain the query in
    their names, and re-calibrated on those.
- **R:** The honest visual-only number was 0.719. The thresholds are now calibrated on the right
  signal, and the README reports both numbers.

**Q55. Tell me about a flaky test you fixed. (Shared test DB)**
- **S:** Tests passed alone and failed in CI, intermittently.
- **T:** Make them deterministic.
- **A:**
  - The tests shared one Postgres database with leftover rows, and some touched the default Qdrant
    collections.
  - I made every run create a throwaway database and an in-memory Qdrant with a scratch prefix, and
    added a guard that refuses the real collections.
- **R:** No flakes since. The tests are also safe to run on a machine with real data.

**Q56. Tell me about a production-like failure under load. (Qdrant request size)**
- **S:** Indexing a large PDF failed with a Qdrant error.
- **T:** Find the limit and fix it generally.
- **A:** One upsert carried thousands of chunks and exceeded Qdrant's request-size limit. I batched
  the upserts (`QDRANT_UPSERT_BATCH` points per request; if a batch fails, nothing is pruned
  and the ledger keeps the previous version, so the file is retried on the next run) and added a test with a huge document.
- **R:** Large files index reliably, and the batch size is bounded independently of the file size.

**Q57. Tell me about a concurrency bug. (Drive httplib2)**
- **S:** After parallelizing the downloads, Drive indexing failed on random files with SSL errors
  (`DECRYPTION_FAILED_OR_BAD_RECORD_MAC`).
- **T:** Find the root cause rather than turning parallelism off.
- **A:**
  - The Google client shares one `httplib2.Http`, which is not thread-safe, so the threads were
    interleaving TLS records on one socket.
  - I gave each worker thread its own `AuthorizedHttp` and retried TLS errors on a fresh connection.
  - I added thread-safety tests and ran a read-only dry run against a real account.
- **R:** 0 SSL errors with 4 workers, and the `INDEX_IO_WORKERS=1` workaround was removed.

**Q58. How did you prioritize the remediation work?**
- An audit produced 38 findings. I grouped them into phases by risk: secrets and history first,
  then auth, isolation, search quality, performance, and CI/docs last.
- Each fix has a commit and a test.
- [REMEDIATION_SUMMARY.md](REMEDIATION_SUMMARY.md) maps all 38 findings.

**Q59. Tell me about a time you had to undo a mistake.**
A personal access token and a users file had been committed. I rotated the token first, then
rewrote the history to scrub them and force-pushed once, in coordination. gitleaks now runs on the
full history in CI.

**Q60. How do you work with a manager or reviewer?**
- Small phases with a written spec.
- A report per phase: what changed, the test outputs and the CI links.
- Never merge my own branch; the manager reviews and merges.
- Constraints like "never touch the owner's data" are encoded in the tests (scratch prefixes,
  guards), not just remembered.

## 10. Operations and scaling

**Q61. How would you scale to 1,000 users?**
1. Move indexing into separate worker processes; the Postgres queue already supports it.
2. Add a GPU pool for embeddings.
3. Shard or partition Qdrant by user.
4. Run several API replicas behind Caddy; rate limits are already in Redis.
5. Make auth stateless-friendly (cookie + refresh rotation).

**Q62. How do you observe it in production?**
- JSON logs with an `X-Request-ID` on every line.
- `/api/health` (liveness) and `/api/ready` (dependencies and models).
- Prometheus `/metrics`, internal only: search latency, jobs, and files by outcome.

**Q63. How do you rotate secrets?**
Each secret has a documented procedure in [OPERATIONS.md](OPERATIONS.md#key-rotation):
- **JWT key:** ends every session.
- **Fernet key:** re-encrypted with a script, with a dry run first.
- **Qdrant API key** and **database password:** documented steps.

**Q64. What is the startup time?**
- **Cold first start:** about 13.5 minutes (image builds plus about 2 GB of models).
- **Restart with the model cache:** about 30 s to ready.

The measured cold and warm numbers are in [FINAL_QA.md](FINAL_QA.md).

**Q65. What's on the roadmap?**
- Shared Drives;
- query expansion;
- cookie-based auth;
- Notion, Slack and OneDrive connectors;
- encryption at rest;
- separate indexing workers.
