# Remediation summary

Every issue from the original audit ([QA_REPORT.md](QA_REPORT.md), 2026-10-04, kept unchanged as the
historical record) mapped to its status, the phase and commit(s) that fixed it, and how it is verified
today. Phase merges on `main`:

| Phase | Merge | Scope |
|---|---|---|
| 0 | `d49d6ac` | Baseline: config in `.env`, compose, test harness, history scrub |
| 1 | `01eb059` | Security & auth |
| 2 | `6adbc7d` | Indexing reliability |
| 3 | `33981d3` | Qdrant single index + per-user isolation |
| 4 | `46ea177` | Search quality & speed |
| 5 | `31ab00a` | Connectors |
| 6 | `2ad0a15` | Frontend |
| 7A | `bfcb7e2` | Security hardening + containerized deployment |
| 7A.5 | `118a264` | Indexing performance |
| fix | `51dfe8c` | Drive/GitHub thread safety |
| 7B | (this branch) | CI, documentation, final QA |

**Result: 38 of 38 issues fixed.** Nothing is open. Related limitations that remain by design are
listed at the end.

## Security

| ID | Issue | Status | Phase / commits | Verified by |
|---|---|---|---|---|
| SEC-01 | Unauthenticated `/delete/` with path traversal | Fixed | 1: `4ebe403` | `tests/test_files.py::test_delete_traversal_is_404`, `tests/test_paths.py` (15 traversal cases), `tests/test_auth_required.py` (every route 401 without a token) |
| SEC-02 | `/open/` ran `os.startfile` on any path | Fixed | 1: `4ebe403`, `edb7a73` | No server-side open exists any more (`app/services/open_service.py` returns a URL or a download); `tests/test_files.py` |
| SEC-03 | Search unauthenticated, not scoped per user | Fixed | 1: `3be7848` (interim); 3: `61afab5` | The single query function refuses to run without `user_id` (`app/vectorstore/query.py`); cross-user tests in `tests/test_index_v2.py`; FINAL_QA probe |
| SEC-04 | Unauthenticated upload with path traversal | Fixed | 1: `4ebe403` | `tests/test_files.py` (auth, sanitized names, size limit, per-user dir) |
| SEC-05 | Hard-coded JWT secret and DB password | Fixed | 0: `c53f6d1`; 1: `f7efd5b`; history scrubbed in Phase 0 | `tests/test_smoke.py` (production refuses weak/missing secrets); gitleaks on the full history in CI |
| SEC-06 | OAuth `state` was the user UUID (no CSRF protection) | Fixed | 1: `1cdd4a3`; 5: `73b6344`, `bda89ab` (PKCE) | `tests/test_oauth_and_tokens.py` (random, single-use, 10-minute state; UUID-as-state rejected), `tests/test_connectors.py` (Drive state + PKCE) |

## Indexing and connectors

| ID | Issue | Status | Phase / commits | Verified by |
|---|---|---|---|---|
| BUG-01 | One exception killed the worker; jobs stuck forever | Fixed | 2: `0b0310f`, `d55afc5` | `tests/test_jobs.py` (loop survives errors, restart marks interrupted jobs failed) |
| BUG-02 | Video semantic/transcript scores always 0 | Fixed | 3: `61afab5`; 6: `232e610` | `tests/test_search_v4.py` (frame time + per-video null stored, video results scored); eval visual-video P@5 0.50 (was 0) |
| BUG-03 | Qdrant and pickles out of sync; ghost results, duplicates | Fixed | 3: `f7060dd`, `4728b51` | Pickles removed; deterministic point ids; `tests/test_index_v2.py::test_reindexing_overwrites_and_prunes_stale_chunks` |
| BUG-04 | GitHub same-path files collided across repos | Fixed | 5: `0e2dd79` | Identity `owner/repo:path`; `tests/test_connectors.py` (GitHub suite) |
| BUG-05 | Every cloud file downloaded on every run | Fixed | 5: `ebf7e5b`, `73b6344` | `needs_index` before download; `tests/test_connectors.py::test_drive_second_run_downloads_nothing_and_modified_file_is_reindexed` and `::test_github_second_run_downloads_nothing_and_changed_sha_only_that_file` |
| BUG-06 | One failed Drive download aborted the run | Fixed | 2: `0b0310f`; 5: `73b6344` | Per-file isolation in `process_files`; `tests/test_connectors.py`, `tests/test_pipeline_concurrency.py` |
| BUG-11 | GitHub repo listing not paginated (max 30) | Fixed | 5: `0e2dd79` | `per_page=100` + `Link` header; `tests/test_connectors.py` |
| BUG-12 | Deleted GitHub files never removed | Fixed | 5: `ebf7e5b`, `0e2dd79` | Deletion sync after a complete listing only; `tests/test_connectors.py` |
| BUG-13 | `PlatformManager.index()` broken | Fixed (removed) | 2: `0b0310f` | Replaced by the worker + `JobContext`; no `PlatformManager` remains |
| BUG-14 | Progress numbers wrong | Fixed | 2: `0b0310f` | Separate succeeded/failed/skipped counters; `tests/test_jobs.py` |
| BUG-15 | Cancel only stopped the current platform | Fixed | 2: `0b0310f`, `d55afc5` | `tests/test_jobs.py::test_cancel_mid_run_stops_after_current_file_and_cancels_queued` |
| BUG-16 | Files with no text re-processed forever | Fixed | 3: `f7060dd` | Ledger status `no_content` / `unsupported` / `excluded` with the version; `tests/test_index_v2.py` |
| BUG-17 | Indexing cost O(n²) (pickle rewrite per file) | Fixed | 3: `f7060dd` | Pickles removed; per-file upsert; measured in `docs/perf/RESULTS.md` |
| BUG-18 | Shared temp dirs collided | Fixed | 2: `0b0310f`; 3 (frames) | Private per-job and per-file temp dirs; `tests/test_jobs.py::test_job_temp_dir_is_created_and_removed_even_on_exception` |
| BUG-19 | Scheduler / index race | Fixed | 2: `93ed4df`, `4e023e6` | One active job per user+platform (partial unique index, 409); `SELECT … FOR UPDATE SKIP LOCKED`; `tests/test_jobs.py::test_duplicate_enqueue_is_409_and_creates_nothing` |

## Search

| ID | Issue | Status | Phase / commits | Verified by |
|---|---|---|---|---|
| BUG-07 | Queries over 77 CLIP tokens gave HTTP 500 | Fixed | 4: `a11e0ac` | CLIP text truncated to 77 tokens; `tests/test_search_v4.py::test_max_length_query_is_accepted`; FINAL_QA |
| BUG-10 | Irrelevant/whitespace queries always returned results; duplicates | Fixed | 4: `4d6dbba` | Calibrated evidence gates; eval negatives 61 → 0 false positives (`docs/EVALUATION.md`); `tests/test_search_v4.py` |
| BUG-20 | Document scoring keyed by basename | Fixed | 3: `61afab5` | Scores per `(platform, source_id)`; `tests/test_index_v2.py::test_same_basename_in_two_folders_is_scored_independently` |
| BUG-21 | A title match could not rescue a file | Fixed | 4: `56fa835`, `4d6dbba` | Postgres trigram filename search; `tests/test_search_v4.py::test_exact_file_name_is_found_even_when_its_chunks_rank_low` |
| BUG-22 | Result limits inconsistent | Fixed | 4: `4d6dbba` | One global merge with `limit` (1–50) / `offset` and `total`; `tests/test_search_v4.py` |
| BUG-23 | Stale temp paths in results | Fixed | 4: `4d6dbba`; 7B: `1e519b8` (Linux) | `tests/test_search_v4.py::test_temporary_paths_are_never_returned` (now also on Linux) |

## Frontend

| ID | Issue | Status | Phase / commits | Verified by |
|---|---|---|---|---|
| FE-01 / BUG-08 | Results hidden client-side while re-indexing / after reload | Fixed | 2: `84f90f2` (part); 6: `9254dac` | The UI renders exactly what the API returns; Vitest suite (`frontend/src/test/search.test.tsx`) |
| FE-02 / BUG-09 | "Index local storage" called a missing endpoint | Fixed | 1: `3c3d3ee`; 6: `9254dac` | Typed API client generated from OpenAPI (`npm run gen:api`); `tsc` fails on unknown endpoints |
| FE-03 | Missing module | Fixed | 1: `3c3d3ee` | `tsc --noEmit` and `vite build` in CI |
| FE-04 | CORS / origin mismatch | Fixed | 1: `9187bd6`; 7A (same origin behind Caddy) | `FRONTEND_URL` + `CORS_ORIGINS` aligned; Docker is same-origin |
| FE-05 | Errors not shown (`console.error` only, `[object Object]`) | Fixed | 6: `9254dac` | One fetch wrapper turns FastAPI errors into messages; Vitest error tests |
| FE-06 | Open-file errors invisible | Fixed | 1: `3c3d3ee`; 6 | Toasts for open/download errors; `frontend/src/test/open-oauth.test.tsx` |
| FE-07 | Fake or broken result metadata | Fixed | 6: `cc41447`, `9254dac` | Real size, modified date, MIME type, score and match reasons from the API |
| FE-08 | Races and duplicate requests (2 pollers at 1 s) | Fixed | 2: `84f90f2`; 6: `9254dac` | AbortController per search, per-query cache keys, one adaptive poller; `frontend/src/test/indexing-platforms.test.tsx` (one poller test) |
| FE-09 | Types | Fixed | 6: `9254dac` | TypeScript strict, types generated from the backend schema; `tsc` in CI |

## Not fixed, by design (documented limitations)

These were not audit findings, but a reviewer should know them (see the README "Known limitations"
and `docs/SECURITY.md` "Known gaps"):

- Indexed text and vectors are not encrypted at rest inside Postgres/Qdrant (OAuth tokens are). Use
  volume/disk encryption.
- The access token is kept in `localStorage` (mitigated by a strict CSP; cookie + CSRF is the planned change).
- Google Shared Drives are not indexed; no query expansion.
- Several dependency advisories are allowlisted with reasons (`docs/SECURITY.md#dependency-audit`).
