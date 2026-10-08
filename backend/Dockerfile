# CogniSeek API image. Build context: the repository root.
#   docker build -f backend/Dockerfile .                         (CPU torch, default)
#   docker build -f backend/Dockerfile --build-arg TORCH_VARIANT=cu128 .   (NVIDIA GPU)
# Multi-stage: compilers and pip caches stay in the builder; the runtime image
# is python:slim + the virtualenv + poppler/ffmpeg, running as a non-root user.

ARG PYTHON_VERSION=3.12

# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ARG TORCH_VARIANT=cpu
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY requirements.in backend/requirements-linux.lock /tmp/

# torch comes from the PyTorch index matching TORCH_VARIANT (cpu | cu128), at the
# version pinned in requirements.in; everything else from the Linux lock file.
RUN set -eux; \
    TORCH_VERSION="$(sed -n 's/^torch==\([0-9.]*\).*/\1/p' /tmp/requirements.in)"; \
    test -n "$TORCH_VERSION"; \
    pip install --index-url "https://download.pytorch.org/whl/${TORCH_VARIANT}" \
        "torch==${TORCH_VERSION}" torchvision torchaudio; \
    pip install -r /tmp/requirements-linux.lock; \
    pip check

# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

# poppler: OCR of scanned PDFs (pdf2image); ffmpeg: audio/video; libgl/glib/gomp: OpenCV + Paddle.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        poppler-utils ffmpeg libgl1 libglib2.0-0 libgomp1 tini \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 cogniseek \
 && useradd --system --uid 10001 --gid cogniseek --home-dir /models --shell /usr/sbin/nologin cogniseek \
 && mkdir -p /models /var/lib/cogniseek/uploads /var/lib/cogniseek/temp \
 && chown -R cogniseek:cogniseek /models /var/lib/cogniseek

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=root:root alembic.ini ./
COPY --chown=root:root alembic ./alembic
COPY --chown=root:root app ./app
COPY --chown=root:root --chmod=0755 backend/entrypoint.sh /usr/local/bin/cogniseek-entrypoint

# Model caches (HuggingFace, faster-whisper, PaddleOCR under $HOME) live in the
# "models" volume so a container restart does not download ~2 GB again.
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/models \
    HF_HOME=/models/huggingface \
    XDG_CACHE_HOME=/models/cache \
    ENV=production \
    DATA_DIR=/var/lib/cogniseek \
    TEMP_DIR=/var/lib/cogniseek/temp \
    ALLOWED_LOCAL_ROOTS=/data

USER cogniseek
EXPOSE 8000

# Readiness (DB, Qdrant, Redis, models). The first start downloads the models
# (~2 GB), hence the long start period; it ends early once the check passes.
HEALTHCHECK --interval=15s --timeout=5s --start-period=1800s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--", "cogniseek-entrypoint"]
