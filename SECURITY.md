# Security

This document describes how CogniSeek protects its users' data, the trade-offs we
chose on purpose, and the known gaps. It covers the Docker deployment
(`docker-compose.yml`); the development setup is described in the README.

## Reporting a vulnerability

Do not open a public issue. E-mail the maintainer (see the git log) with the steps to
reproduce. We aim to answer within 7 days.

## Architecture at a glance

| Layer | Control |
|---|---|
| Edge | **Caddy is the only container with published ports (80/443).** HTTP redirects to HTTPS; `tls internal` on localhost, Let's Encrypt for a real `DOMAIN`. HSTS (1 year) only with a real certificate. Caddy's admin API is off. |
| Same origin | The frontend and the API share one origin (`https://<host>/` and `https://<host>/api/`), so the browser never makes cross-origin calls and CORS allows only that origin. |
| Networks | `data` (internal): Postgres, Qdrant, Redis, backend. `app` (internal): Caddy ↔ backend. `egress`: the backend's outbound internet (models, Google, GitHub). Caddy cannot reach the data services; nothing on `data` is reachable from the host. |
| Postgres | The app connects as a role **without** superuser/createdb/createrole (`deploy/postgres/initdb/01-app-role.sh`). The bootstrap superuser is used only for initialisation and backups. `pgcrypto` and `pg_trgm` are installed by the init script, so migrations need no elevated rights. |
| Qdrant | API key required (`QDRANT__SERVICE__API_KEY`); the backend refuses to start in production without `QDRANT_API_KEY`. Telemetry off. |
| Redis | Password-protected; holds only rate-limit counters. |
| Rate limits | Redis-backed (shared, survive restarts): login/register 5/min per IP, search 60/min per user, OAuth connect/callback 10/min. Client IPs come from Caddy's `X-Forwarded-For` (uvicorn `--proxy-headers`; only Caddy can reach the backend). |
| Containers | Backend runs as an unprivileged user (uid 10001), code owned by root (read-only for the app), `tini` as PID 1. Local folders are mounted read-only at `/data`; uploads live in a volume. |
| Headers | Caddy: strict CSP (below), `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, COOP/CORP; the `Server` header is removed. The API adds its own restrictive CSP to JSON responses. |
| Metrics | `/metrics` is served on the internal network only; Caddy answers 404 for `/api/metrics`. |

### Content Security Policy

```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:;
font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none';
form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests
```

No `'unsafe-inline'` or `'unsafe-eval'`. The production build has a single
`<script type="module" src=…>` and no inline scripts or `<style>` elements; fonts are
self-hosted (`@fontsource-variable/*`) instead of Google Fonts, so no third party sees
our users' IP addresses. React and motion set styles through the CSSOM, which CSP does
not restrict. `tests/test_deploy.py` checks the policy and the HTML.

## Authentication

- Passwords: bcrypt; 8–128 characters (at most 72 bytes) with a letter and a digit.
- Access tokens: HS256 JWT, 60 minutes, signed with a ≥32-character secret. Every token
  carries the user's `token_version`; logout, password change and account deletion bump
  or delete it, which **revokes every existing token of that user at once**.
- OAuth tokens for Drive/GitHub are encrypted at rest (Fernet, `TOKEN_ENCRYPTION_KEY`)
  and revoked at the provider on disconnect and on account deletion. The OAuth `state`
  is random, single-use, bound to the user and expires after 10 minutes.

### Why the JWT is in `localStorage` (and not a cookie)

We keep the access token in `localStorage` and send it as `Authorization: Bearer`.
This is a conscious trade-off:

- **No CSRF by construction.** The browser never attaches the token automatically, so
  a malicious site cannot make authenticated requests on the user's behalf. A cookie
  would require CSRF tokens on every state-changing endpoint.
- **The risk is XSS**: script running in our origin could read the token. We reduce
  that risk instead: strict CSP with no inline script and no third-party origins, React's
  escaping (no `dangerouslySetInnerHTML`; search highlights are built from text ranges),
  and short-lived tokens that are revocable server-side.

**Future work (not implemented):** move the token to an `HttpOnly; Secure;
SameSite=Strict` cookie scoped to `/api`, add a double-submit CSRF token (header +
cookie) checked on every non-GET request, and add refresh-token rotation so access
tokens can be shorter. Same-origin deployment behind Caddy already makes this possible
without CORS changes.

## Your data

- **Export** (Account settings → Export my data, `GET /auth/export`): profile,
  connected accounts (names only), folders, indexing history and the list of indexed
  files. No file contents, vectors, tokens or password hashes.
- **Delete account** (`DELETE /auth/account`, requires the password and a typed
  confirmation in the UI): revokes Drive/GitHub grants, deletes every vector of the user
  in every Qdrant collection (filtered by user id), the file ledger, jobs, folders,
  connections, uploads and the user row. Existing sessions stop working immediately.
  Original files are never touched. Backups taken earlier still contain the data until
  they age out (`BACKUP_KEEP`).
- **Change password** (`POST /auth/change-password`): same policy as registration;
  signs out every session.
- Users only ever see their own data: every query filters by the user id inside
  Postgres and Qdrant (not after retrieval), and local files are served only from the
  user's registered folders.

## Secrets

- `python scripts/generate_secrets.py` fills every empty REQUIRED secret in `.env`
  with a random value, never overwrites an existing one, never prints a value and sets
  the file to mode 600. `.env`, `credentials/`, `data/` and `backups/` are git-ignored
  and excluded from every Docker build context (`.dockerignore`).
- Production refuses to start without a strong `JWT_SECRET_KEY`, a valid
  `TOKEN_ENCRYPTION_KEY`, `QDRANT_API_KEY` and `REDIS_URL`; configuration errors never
  echo values.
- **Logs never contain secrets.** Every log record (including uvicorn's access log)
  passes a filter that redacts bearer tokens, JWTs, Google/GitHub token literals,
  `password=`/`token=`/`code=`/`state=` pairs and JSON secret fields, in messages and
  tracebacks (`tests/test_observability.py`). Caddy's access log drops `code`, `state`
  and `token` query parameters and the `Authorization`/`Cookie` headers. Error messages
  shown to users are sanitised the same way and never contain stack traces.
- Every response carries an `X-Request-ID` that also appears in every log line of the
  request, so a user-reported error can be traced without logging request bodies.

## Backups

- `docker compose run --rm backup` runs `scripts/backup.py` in a tools container
  (`deploy/backup/Dockerfile`, same Postgres major version as the server) on the internal
  network: `pg_dump` (custom format) plus a snapshot of every Qdrant collection, in
  one tar with SHA-256 checksums in a manifest.
- The archive is **encrypted** with `BACKUP_ENCRYPTION_KEY` (Fernet: AES-128-CBC +
  HMAC-SHA256) in authenticated 8 MiB chunks; each chunk carries its index and a
  "last" flag, so a truncated, reordered or modified archive is rejected. Files are
  written with mode 600 and only the newest `BACKUP_KEEP` (default 14) are kept.
- **Key custody:** store `BACKUP_ENCRYPTION_KEY` in a password manager, separate from
  the backups. Losing it makes every backup unreadable; leaking it together with an
  archive exposes the data.
- **Test restores:** `scripts/restore.py --dry-run` decrypts, verifies every checksum
  and parses the dump without writing anything. A full restore into a scratch database
  and collection prefix (`--database-url …/restore_check --create-database
  --target-prefix restorecheck`) checks that point counts match; restoring onto the live
  names requires `--yes`. Run a scratch restore after every upgrade and at least monthly.
- Copy the archives off the machine (they are encrypted, so any storage works).

## Dependency audit (Phase 7A, 2026-10-08)

**npm:** `npm audit` reports **0 vulnerabilities** (production and dev). Fixed:
vitest 3 → 5.0.3 (critical, via tinypool) and transitive `browserslist` /
`baseline-browser-mapping`; `depcheck` (high, via `braces`/`micromatch`, no fixed
release) is no longer installed and runs on demand via `npx`.

**Python** (`pip-audit` on `backend/requirements-linux.lock`). Fixed:
`cryptography` 48 → 50.0.0, `sentence-transformers` 5.5.1 → 5.6.0, `setuptools` 78 →
81.0.0. Remaining, with the reason:

| Package | Why it is not upgraded yet | Exposure |
|---|---|---|
| `transformers` 4.49.0 | Fixes are in 4.50–5.x. Upgrading changes model loading/preprocessing and must be re-validated against the calibrated search gates (`docs/eval/`). Planned with the next evaluation run. | Models are loaded only from pinned Hugging Face repos at startup; no user-supplied model files or `trust_remote_code`. |
| `pillow` 11.3.0 | `moviepy` 2.2.1 requires `pillow<12`; the fixes are in 12.x. | Image decoding of user files. Indexing runs in the unprivileged backend container with read-only `/data`; plan: replace moviepy with direct ffmpeg calls, then upgrade. |
| `opencv-python(-contrib)` 4.6.0.66 | `paddleocr` 2.7.3 requires `<=4.6.0.66`. | Same as above (decoding of user images/video). |
| `paddlepaddle` 2.6.2 | Fix is in 3.0, which `paddleocr` 2.7 does not support (requires the PaddleOCR 3 migration). | OCR of user images/PDF pages. |
| `python-jose` 3.5.0 / `ecdsa` 0.19.2 | No fixed release. The advisories concern ECDSA (timing side channel); we only use HS256. | Not reachable. Plan: switch to PyJWT. |
| `setuptools` 81.0.0 | One advisory is fixed in 83, but torch 2.11 requires `setuptools<82`. | Build/packaging tool; not used by the running app. |
| `imgaug` 0.4.0 | No fixed release; pulled in by `paddleocr`, used for training-time augmentation only. | Not called at runtime. |

The Windows development venv (`requirements.txt`) pins the same versions where they
apply to both platforms.

### Updating the Docker lock file

`requirements.txt` is the Windows dev venv freeze and cannot be installed on Linux.
`backend/requirements-linux.lock` is resolved from `requirements.in` inside
`python:3.12-slim` with CPU torch:

```bash
docker run --rm -v "$PWD:/w" -w /w python:3.12-slim sh -c '
  apt-get update && apt-get install -y build-essential &&
  python -m venv /v && . /v/bin/activate &&
  pip install --index-url https://download.pytorch.org/whl/cpu torch==<ver> torchvision torchaudio &&
  grep -vE "^torch==|^--extra-index-url" requirements.in > /tmp/req.in && pip install -r /tmp/req.in &&
  pip check && pip freeze --exclude torch --exclude torchvision --exclude torchaudio'
```

Paste the output below the header of `backend/requirements-linux.lock`; the image
build runs `pip check`.

## Owner actions

- The development containers from before Phase 7A (`cogniseek-postgres`,
  `cogniseek-qdrant`) were created with ports bound to `0.0.0.0`. `docker-compose.dev.yml`
  now binds `127.0.0.1` only; recreate them to apply it (data volumes are kept):
  `docker compose -f docker-compose.dev.yml up -d --force-recreate`.
- Run `alembic upgrade head` on the development database (migration 0014 converts
  timestamps to `timestamptz`) and restart the backend.
