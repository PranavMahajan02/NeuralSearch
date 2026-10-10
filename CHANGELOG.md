# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-10

The first release. It completes the remediation of all 38 findings from the initial audit
([docs/REMEDIATION_SUMMARY.md](docs/REMEDIATION_SUMMARY.md)). Release notes:
[docs/RELEASE_NOTES_v1.0.0.md](docs/RELEASE_NOTES_v1.0.0.md).

### Added
- **Multi-user accounts:**
  - registration, login, revocable JWTs, password change;
  - account export and deletion;
  - onboarding with a priority platform.
- **Connectors:**
  - **Google Drive:** OAuth web flow, state + PKCE, granted-scope check.
  - **GitHub:** OAuth, Git Trees API.
  - **Local folders:** allowed roots, traversal-safe.
- **Indexing:**
  - a Postgres job queue and a file ledger: unchanged files are skipped before download, and
    deletions are synced;
  - cancel, per-file errors, run history;
  - "Where the time went" stage timings.
- **Hybrid search:**
  - MiniLM, CLIP, Whisper and OCR evidence plus trigram file-name search;
  - calibrated evidence gates and a separate "Possible matches" tier;
  - an evaluation harness (`scripts/eval_search.py`, 83 labelled queries).
- **The React 19 frontend:** dashboard, Indexing Center, Platforms, light/dark themes, accessible
  (axe-checked).
- **Docker deployment:**
  - Caddy (TLS, strict CSP), internal data network;
  - encrypted backups with restore and dry run;
  - a GPU override.
- **Opt-in GPU OCR** (`requirements-gpu.txt`, `OCR_DEVICE`) and a parallel indexing pipeline
  (`INDEX_IO_WORKERS`, `INDEX_PREFETCH`).
- **Tooling:**
  - CI: backend, frontend, security (gitleaks, pip-audit, npm audit, CodeQL), Docker, e2e;
  - Dependabot;
  - a mypy baseline check;
  - `scripts/rotate_token_key.py`.
- **Docs:** architecture, security, evaluation, operations, final QA, project guide, interview
  Q&A, demo script; MIT license.

### Changed
- **Search:** p50 went from 1.5–2.3 s to about 0.2 s; 8 concurrent searches are no longer
  serialized.
- **Indexing:** the benchmark went from 347 s to 93 s; 50% of the files are searchable after 31 s
  instead of 191 s.
- **Storage:** Qdrant (`cogniseek_v2_*`) and Postgres are the single source of truth; the pickle
  indexes are gone.
- **Code style:** ruff lint and format across the codebase; LF line endings enforced by
  `.gitattributes`.

### Fixed
- Unauthenticated search, upload, open and delete endpoints (SEC-01 to SEC-04).
- OAuth CSRF (SEC-06); the blocking Google `connect` call.
- Path traversal in uploads, downloads and folder registration.
- Cross-user data exposure in search, the dashboard and jobs.
- A 500 on long queries; acceptance of empty names and passwords.
- Indexing wedging on a single failure; full re-downloads; orphaned and duplicate vectors.
- Drive SSL errors under parallel downloads (per-thread transports).

### Removed
- **Legacy scripts and docs:** `scripts/legacy/`, `docs/legacy/`.
- **Unused modules:** `app/database/crud.py`, `app/models/upload_models.py`.
- **Tracked runtime artifacts:** pickles, temp frames.
- **Leaked credentials:** removed from the git history; the affected secrets were rotated.

### Security
- Fernet-encrypted OAuth tokens and redacted logs.
- Rate limits (Redis in production).
- Production refuses weak or missing secrets.
- Data services are not published.

[1.0.0]: https://github.com/PranavMahajan02/NeuralSearch/releases/tag/v1.0.0
