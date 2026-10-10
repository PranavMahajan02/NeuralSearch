# CogniSeek v1.0.0

**One search box for your laptop, Google Drive and GitHub.** It finds documents, code, images,
audio and video by what they contain, say and show.

## Highlights

- **Multimodal, calibrated search:**
  - non-visual P@5 **0.935**;
  - nonsense queries return nothing (false positives 61 → 1);
  - p50 about **0.2 s**.
- **3.7× faster indexing:** 347 s → 93 s on the benchmark, and half the files are searchable after
  31 s. GPU OCR is opt-in.
- **Multi-user and secure by default:**
  - per-user isolation in every query;
  - encrypted OAuth tokens, revocable JWTs, rate limits;
  - a strict CSP behind Caddy, encrypted backups.
- **Production-ready deployment:** `docker compose up -d --build`, then
  [docs/OPERATIONS.md](OPERATIONS.md).
- **Verified:** 470+ backend tests, Vitest, a Playwright e2e test against the Docker stack, and
  security scanning in CI. See [FINAL_QA.md](FINAL_QA.md): 43/43 probes pass.

## Upgrading from a pre-1.0 checkout

This is the first release; earlier states were development snapshots.
1. Back up (`docker compose run --rm backup`).
2. Pull, then `docker compose up -d --build`. The migrations (0001–0015) run on start.
3. Development: `venv\Scripts\python -m alembic upgrade head`.
4. Users must reconnect Google Drive with a **Web application** OAuth client (see the README).

## Known limitations

- No Shared Drives.
- No query expansion.
- Visual-only recall: about 70% for images, 50% for video.
- Indexed text is not encrypted at rest.
- The access token is stored in `localStorage`.

Full list: the README.

## Full changelog

[CHANGELOG.md](../CHANGELOG.md)
