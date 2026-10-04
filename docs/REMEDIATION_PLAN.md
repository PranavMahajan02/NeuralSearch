# CogniSeek AI — Remediation Plan

**Source of truth for issues:** `docs/QA_REPORT.md`. Every issue ID used here (SEC-xx, BUG-xx, FE-xx) refers to that report.
**Goal:** a secure, multi-user, deployable system that can be defended in an interview.
**Process:** each phase runs in its own engineer session. The manager reviews the engineer's report and the diff before the next phase starts. No phase begins until the previous one is accepted.

## Target architecture (decided)

These decisions are final. Engineers implement them and do not re-debate them.

| Decision | Choice |
|---|---|
| Vector + metadata store | **Qdrant only.** The pickle indexes and in-memory pickle caches are removed. Every point carries `user_id`, `platform`, `source_id`, `file`, `path`, `type`, `version` (mtime, SHA, or `modifiedTime`), and `chunk`. |
| Per-file bookkeeping | Postgres table `indexed_files` (it already exists in the models and is unused). Change detection reads this table, not Qdrant scans. |
| Tenancy | Every endpoint except register, login, health, and the OAuth callback requires a JWT. Every query and delete is filtered by `user_id`. |
| File identity | `source_id` is `abs normalized path` for local, `drive file id` for Drive, and `owner/repo:path` for GitHub. |
| Config | `pydantic-settings` reads `.env`. A committed `.env.example` documents it. No secrets in code. |
| Local-only features | `os.startfile`, tkinter, `webbrowser`, and `InstalledAppFlow` are replaced by browser-side flows (open via URL or download, folder paths typed or picked client-side, web OAuth redirect flow for Drive). |
| Run model | `docker compose up` starts postgres, qdrant, backend, and frontend (nginx). |
| Tests | `pytest` with a test Postgres and Qdrant (or Qdrant in `:memory:` mode), plus `tsc --noEmit` and `vite build` in CI (GitHub Actions). |

## Phases

| Phase | Name | Covers | Exit criteria |
|---|---|---|---|
| 0 | Baseline & safety net | repo hygiene, config, compose, test harness | Clean git state, `.env.example`, Qdrant in compose, pytest runs, backup of current data |
| 1 | Security & auth | SEC-01..06, auth gaps, CORS | Every non-public route returns 401 without a token. No path traversal. No secrets in code. Tests prove it. |
| 2 | Indexing reliability | BUG-01, 06, 13, 14, 15, 16, 18, 19 | No exception can wedge a job. Per-user queue. Accurate progress and cancel. Tests prove it. |
| 3 | Single index (Qdrant) | BUG-03, 17, 20, BUG-02 storage side | Pickles gone. `user_id` on every point. Deletes are synced. Rebuild command exists. Counts match. |
| 4 | Search quality & speed | BUG-07, 10, 20, 21, 22, 23, BUG-02 scoring | Input validation. CLIP truncation. Dedupe by identity. Thresholds tuned. One embedding per model per query. p50 under 1 s for all/all. |
| 5 | Connectors | BUG-04, 05, 11, 12, Drive items | Change check before download. Pagination. Deletion sync. Default branch. Web OAuth for Drive. |
| 6 | Frontend | FE-01..09 | No client-side hiding of results. Real scores and metadata. Errors shown. Request race handled. Single poller. `tsc` clean. |
| 7 | Deployment & interview readiness | Dockerfiles, CI, logging, docs | `docker compose up` works from a fresh clone. CI is green. README, ARCHITECTURE.md, SECURITY.md, and interview Q&A are written. |

## Rules for every engineer session

1. Work on branch `fix/phase-N-<name>`. Make small commits with clear messages.
2. Fix only the scope of the current phase. List anything else you notice under "Out-of-scope observations".
3. Do not delete user data (`data/`, `credentials/`, Postgres volume, Qdrant volume) without explicit approval.
4. Every fix must have a test, or a documented manual check if it can't be automated.
5. End the session with the **report template** below, copied exactly.
6. **Pushing to GitHub** (`origin` = https://github.com/PranavMahajan02/NeuralSearch):
   - Push the phase branch only after all tests pass.
   - Before every push, run a secret scan (`gitleaks detect` or `git diff origin/main..HEAD` reviewed for keys, tokens, passwords, `.env`, `credentials/`, `*.pkl`, `data/`). Do not push if anything is found.
   - Never force-push without explicit approval from the owner in chat.
   - Merge into `main` only after the manager accepts the phase. Merge with `git merge --no-ff`, then push `main`.

## Engineer report template

```
## Phase N report
### Branch / commits
<branch name, list of commit hashes + messages>
### Issues addressed
| ID | Status (fixed/partial/deferred) | Files changed | How verified |
### Tests
<command run + full pass/fail summary output>
### Manual verification
<curl commands / steps + actual outputs>
### Deviations from the prompt (and why)
### Out-of-scope observations
### Open questions for the manager
```
