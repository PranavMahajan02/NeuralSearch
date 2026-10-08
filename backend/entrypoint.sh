#!/bin/sh
# Container entrypoint: migrate, then serve.
set -eu

echo "cogniseek: applying database migrations"
alembic upgrade head

# WORKERS defaults to 1 on purpose: the indexing worker runs inside the API
# process (one per process would mean several workers competing for the queue
# and loading every model again), and the models (GPU memory) are loaded once
# per process. Scale with a bigger machine, not more uvicorn workers.
# --proxy-headers: the client IP comes from Caddy's X-Forwarded-For (rate
# limits per client). Only Caddy can reach this port (internal network).
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WORKERS:-1}" \
    --proxy-headers \
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
    --no-server-header
