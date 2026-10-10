# Operations

Deploying, upgrading, backing up, rotating keys, observing and troubleshooting CogniSeek.

## Deploy (Docker)

```bash
git clone https://github.com/PranavMahajan02/NeuralSearch.git cogniseek && cd cogniseek
cp .env.example .env
python scripts/generate_secrets.py          # fills every REQUIRED secret; prints key names only
docker compose up -d --build                # first start downloads ~2 GB of models
docker compose ps                           # wait for backend "healthy" and caddy "running"
```

- **Open the app:** https://localhost. The certificate is self-signed; accept it, or trust Caddy's
  CA with `docker compose exec caddy caddy trust`.
- **Public server:** set `DOMAIN=search.example.com` and `TLS=<your e-mail>` in `.env`. Caddy
  then gets a Let's Encrypt certificate and sends HSTS. Ports 80/443 must be reachable.
- **Local folders:** the backend sees `LOCAL_DATA_DIR` (default `./sample-data`, read-only) as
  `/data`. Register `/data/...` paths in the UI.
- **Google Drive / GitHub:**
  1. Put `client_secret.json` and `github_oauth.json` in `./credentials/`.
  2. Register the callback URLs `https://<DOMAIN>/api/platforms/google-drive/callback` and
     `https://<DOMAIN>/api/platforms/github/callback`.
- **GPU:** `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build` needs the
  NVIDIA Container Toolkit. This variant is untested on the maintainer's machine.
- **Measured from a fresh clone:** about 13.5 minutes the first time (two image builds plus the
  model download). A restart with the model cache takes about 30 s to become ready.

## Upgrade

```bash
docker compose run --rm backup              # always back up first
git pull
docker compose up -d --build                # the backend runs `alembic upgrade head` on start
docker compose logs -f backend              # watch the migration and the model preload
```

**Development (non-Docker):** `venv\Scripts\python -m alembic upgrade head`, then restart the
backend. Migrations are reversible (`alembic downgrade -1`). CI runs `alembic check`, which proves
the models and the migrations agree.

## Backup and restore

```bash
docker compose run --rm backup              # ./backups/cogniseek-<UTC>.tar.enc (encrypted)
docker compose run --rm backup python3 /scripts/restore.py --dry-run /backups/<file>   # verify only
```

**Scratch restore** (safe at any time; checks the point counts):

```bash
docker compose run --rm backup sh -c 'python3 /scripts/restore.py /backups/<file> \
  --database-url "${BACKUP_DATABASE_URL%/*}/restore_check" --create-database --target-prefix restorecheck'
```

**Disaster recovery:**

```bash
docker compose stop backend caddy
docker compose run --rm backup python3 /scripts/restore.py /backups/<file> --yes
docker compose up -d
```

**Schedule:** daily backups via cron, e.g.
`30 3 * * * cd /opt/cogniseek && docker compose run --rm backup >> backups/backup.log 2>&1`
(or Windows Task Scheduler with the same command). Copy the archives off the machine, and keep
`BACKUP_ENCRYPTION_KEY` in a password manager: without it the backups cannot be restored.

## Key rotation

Overview and effects: [SECURITY.md](SECURITY.md#secrets-and-rotation).

**JWT signing key:**
1. `python -c "import secrets; print(secrets.token_urlsafe(48))"`
2. Put the result in `.env` as `JWT_SECRET_KEY`.
3. `docker compose up -d backend`. Every session ends.

**Token encryption key (Fernet), with re-encryption:**
1. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. `docker compose stop backend`
3. Set `OLD_TOKEN_ENCRYPTION_KEY` and `NEW_TOKEN_ENCRYPTION_KEY` in the environment, then run
   `scripts/rotate_token_key.py --dry-run`, then without `--dry-run`. In Docker:
   `docker compose run --rm -e OLD_TOKEN_ENCRYPTION_KEY -e NEW_TOKEN_ENCRYPTION_KEY --entrypoint python backend scripts/rotate_token_key.py`
   (bind-mount `scripts/` if the image predates the script).
4. Set `TOKEN_ENCRYPTION_KEY` in `.env` to the new key.
5. `docker compose up -d backend`

**Qdrant API key:** set a new `QDRANT_API_KEY` in `.env`, then `docker compose up -d`. This
recreates Qdrant (which reads `QDRANT__SERVICE__API_KEY`) and the backend.

**Database password (app role):**
1. `docker compose exec postgres psql -U postgres -c "ALTER ROLE cogniseek PASSWORD '<new>'"`
2. Update `POSTGRES_PASSWORD` in `.env`.
3. `docker compose up -d backend`

## Logs and metrics

- **Logs:**
  - JSON lines in production (`docker compose logs backend`).
  - Every line carries the request's `X-Request-ID`; the response returns the same id, so a
    user-reported error can be found.
  - Tokens, JWTs, OAuth codes/state and passwords are redacted, and Caddy logs JSON without query
    secrets.
- **Health:**
  - `GET /api/health` is liveness (the process answers).
  - `GET /api/ready` checks Postgres, Qdrant, Redis and the models (503 with booleans if not).
  - The compose healthchecks use readiness.
- **Metrics:** `GET /metrics` (Prometheus) is reachable only on the Docker network; Caddy answers
  404 for `/api/metrics`. Scrape `backend:8000/metrics` from a Prometheus container on the `data`
  network. It exposes:
  - HTTP latency and counts;
  - `cogniseek_search_seconds`;
  - `cogniseek_index_jobs_total{platform,status}`;
  - `cogniseek_index_files_total{platform,outcome}`.
- **Where the time went:** every finished job stores seconds per stage (`stage_timings`). The
  Indexing Center shows them as a bar list.

## Tuning

| Setting | Default | Notes |
|---|---|---|
| `INDEX_IO_WORKERS` | 4 | Files indexed at once. Lower it on small machines (CPU OCR with 4 workers peaked at 4.8 GB RSS). `1` = sequential. |
| `INDEX_PREFETCH` | 8 | Upper bound on files in flight |
| `OCR_DEVICE` | auto | GPU when the CUDA build of Paddle is installed |
| `WHISPER_BATCH_SIZE` | 0 | Batched Whisper was measured slower end-to-end on a 4 GB GPU |
| `GPU_SERIALIZE` | false | One lock for all GPU models; measured slower (115 s vs 93 s) |
| `WORKERS` | 1 | Keep 1: the indexing worker and the models live in the API process |
| `PRELOAD_MODELS` | true | False = load models on first use (faster start, slow first request) |

## Troubleshooting

**Port 3000 already in use (Vite fails to start).** The dev server uses `strictPort`: it fails
instead of moving to another port, because the OAuth return URL and CORS expect exactly
`http://127.0.0.1:3000`. Stop the other process, or run on another port and change `FRONTEND_URL`
and `CORS_ORIGINS` to match.

**OAuth "redirect_uri_mismatch" (Google) or "redirect_uri is not associated" (GitHub).** The
callback URL must match the provider console exactly: scheme, host, port and path.
- **Development:** `http://127.0.0.1:8000/platforms/google-drive/callback` (Google, via
  `GOOGLE_REDIRECT_URI`) and `http://127.0.0.1:8000/platforms/github/callback` (GitHub, from
  `BACKEND_PUBLIC_URL`).
- **Docker:** `https://<DOMAIN>/api/...`.
- `localhost` and `127.0.0.1` are different hosts to the providers.
- The Google client must be of type **Web application** (a "Desktop app" client does not work).

**"Google Drive: Please allow 'See and download your Google Drive files'".** Google's consent
screen has a checkbox per permission. If the Drive box is not ticked, the app receives a token
without `drive.readonly`. CogniSeek checks the scopes Google actually granted, revokes that token
and stores nothing. Connect again and tick the Drive checkbox.

**Logged out after the OAuth return, or "logged in" in one tab but not another.** The login token
lives in `localStorage`, which is per origin: `http://localhost:3000` and `http://127.0.0.1:3000`
are different origins. Open the app on the same host as `FRONTEND_URL` (default
`http://127.0.0.1:3000`), because the OAuth callback redirects there.

**A copied venv: `pip.exe` / `alembic.exe` / `uvicorn.exe` run the wrong Python or fail.** The
Windows launcher executables embed the absolute path of the venv they were created in. A copied
folder (e.g. "omniseach-ai - Copy") still points at the original. Always call the modules through
the venv's own interpreter:

```powershell
venv\Scripts\python -m pip install -r requirements-dev.txt
venv\Scripts\python -m alembic upgrade head
venv\Scripts\python -m uvicorn app.main:app --port 8000
```

**Windows: `WinError 127` loading `shm.dll` / torch fails after Paddle.** torch must load its CUDA
DLLs before Paddle's. `app/ai/model_manager.py` always imports torch first; keep that order in any
script that uses both. On Linux, importing `paddleocr` before torch/OpenCV can segfault in zlib
(`inflateReset2`), and the same ordering avoids it.

**GPU OCR (opt-in): install and roll back.**

```powershell
venv\Scripts\python -m pip uninstall -y paddlepaddle
venv\Scripts\python -m pip install -r requirements-gpu.txt          # paddlepaddle-gpu 2.6.2 (CUDA 12) + cuDNN 8
# rollback:
venv\Scripts\python -m pip uninstall -y paddlepaddle-gpu nvidia-cudnn-cu12
venv\Scripts\python -m pip install paddlepaddle==2.6.2
```

`OCR_DEVICE=auto` picks the GPU when the CUDA build is present, and the startup log says
"Loading PaddleOCR (GPU)". On Windows the cuDNN 8 DLLs come from the `nvidia-cudnn-cu12` wheel and
the CUDA 12 runtime from torch's `lib` folder; the app registers both. Measured: OCR 72.0 s →
9.3 s on 37 inputs, with +482 MB of VRAM.

**FFmpeg warnings `[h264 @ …] mmco: unref short failure`.** These are harmless decoder messages
about frame references in some H.264 streams, printed by OpenCV's FFmpeg backend while seeking.
The frames are decoded correctly, and the frame-extraction tests check pixel equality.

**Drive indexing failed on random files with SSL errors** (`DECRYPTION_FAILED_OR_BAD_RECORD_MAC`,
`WRONG_VERSION_NUMBER`). **Fixed** in the Drive thread-safety fix (merge `51dfe8c`). Parallel
downloads shared one `httplib2` connection, which is not thread-safe; each worker thread now has
its own transport, and TLS errors are retried on a fresh connection. If you added
`INDEX_IO_WORKERS=1` to `.env` as a workaround, remove it. To check a Drive connection without
indexing anything: `venv\Scripts\python scripts\drive_download_dryrun.py --email <you> --workers 4`.

**Search returns nothing for a file you know exists.**
1. Check the Indexing Center for errors. "No content" files had no extractable text.
2. Check that the file type is supported and not excluded (`INDEX_EXCLUDE_GLOBS`).
3. Remember that visual-only search finds about 70% of relevant images; a file-name or content word
   always works.

**The backend refuses to start in production.** It needs `JWT_SECRET_KEY` (≥ 32 characters), a
valid `TOKEN_ENCRYPTION_KEY`, `QDRANT_API_KEY` and `REDIS_URL`. Run
`python scripts/generate_secrets.py`. The error names the missing setting, never its value.

**`/api/ready` stays 503 on the first start.** The models (about 2 GB) are downloading; follow
`docker compose logs -f backend`. The healthcheck allows up to 30 minutes for this.
