import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware

from app.auth.auth_router import router as auth_router
from app.routes.search import router as search_router
from app.routes.google_drive import router as google_drive_router
from app.routes.github import router as github_router
from app.routes.index import router as index_router
from app.routes.upload import router as upload_router
from app.routes.delete import router as delete_router
from app.routes.open import router as open_router
from app.routes.files import router as files_router
from app.routes.dashboard import router as dashboard_router
from app.cache.search_cache import initialize_search_cache
from app.routes.login_state import router as login_state_router
from app.routes import platforms
from app.ai.model_manager import model_manager
from app.database.db import SessionLocal
from app.scheduler.jobs import recover_interrupted_jobs
from app.scheduler.worker import worker as indexing_worker


logging.basicConfig(level=logging.INFO)


logger = logging.getLogger("cogniseek")


def preload_models():

    if os.getenv("COGNISEEK_SKIP_MODEL_PRELOAD") == "1":
        print("Skipping AI model preload (COGNISEEK_SKIP_MODEL_PRELOAD=1).")
        return

    print("Loading AI models...")

    _ = model_manager.semantic_model
    _ = model_manager.clip_model
    _ = model_manager.clip_processor
    _ = model_manager.whisper_model
    _ = model_manager.ocr_model

    print("AI models ready.")


@asynccontextmanager
async def lifespan(_app: FastAPI):

    initialize_search_cache()

    preload_models()

    # A job still "running" was cut off by the previous shutdown.
    with SessionLocal() as db:
        recovered = recover_interrupted_jobs(db)

    if recovered:
        logger.warning("Marked %s interrupted job(s) as failed.", recovered)

    run_worker = os.getenv("COGNISEEK_DISABLE_WORKER") != "1"

    if run_worker:
        indexing_worker.start()

    try:
        yield
    finally:
        if run_worker:
            indexing_worker.stop()


# Interactive docs and the schema are development-only.
DOCS_ENABLED = not settings.is_production

app = FastAPI(
    title="CogniSeek API",
    description="Unified Semantic Search Backend",
    version="1.0.0",
    docs_url="/docs" if DOCS_ENABLED else None,
    redoc_url="/redoc" if DOCS_ENABLED else None,
    openapi_url="/openapi.json" if DOCS_ENABLED else None,
    lifespan=lifespan
)

app.state.limiter = limiter

register_error_handlers(app)

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    # Lets the browser read the download file name from /files/local.
    expose_headers=["Content-Disposition"],
)

# Register Routers
app.include_router(search_router)
app.include_router(index_router)
app.include_router(upload_router)
app.include_router(open_router)
app.include_router(files_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(google_drive_router)
app.include_router(github_router)
app.include_router(login_state_router)
app.include_router(
    delete_router,
    prefix="/delete",
    tags=["Delete"]
)
app.include_router(platforms.router)

# The tkinter folder picker opens a dialog on the machine running the backend,
# so it only exists in development. In production, folder paths are typed in.
if settings.ENV == "development":

    from app.routes.local_picker import router as local_picker_router

    app.include_router(local_picker_router)


@app.get("/")
def home():

    return {
        "message": "CogniSeek Backend Running"
    }
