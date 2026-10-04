from fastapi import FastAPI
from app.auth.auth_router import router as auth_router
from app.routes.search import router as search_router
from app.routes.google_drive import router as google_drive_router
from app.routes.github import router as github_router
from app.routes.index import router as index_router
from app.routes.upload import router as upload_router
from app.routes.delete import router as delete_router
from app.routes.open import router as open_router
from app.routes.scheduler import router as scheduler_router
from app.routes.dashboard import router as dashboard_router
from fastapi.middleware.cors import CORSMiddleware
from app.cache.search_cache import initialize_search_cache
from app.database.db import Base, engine
from app.routes.login_state import router as login_state_router
from app.routes.index_status import router as index_status_router
from app.routes.local_picker import router as local_picker_router
from app.routes import platforms
from app.ai.model_manager import model_manager

app = FastAPI(
    title="CogniSeek API",
    description="Unified Semantic Search Backend",
    version="1.0.0"
)
Base.metadata.create_all(bind=engine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(search_router)
app.include_router(index_router)
app.include_router(index_status_router)
app.include_router(upload_router)
app.include_router(open_router)
app.include_router(scheduler_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(google_drive_router)
app.include_router(github_router)
app.include_router(login_state_router)
app.include_router(local_picker_router)
app.include_router(
    delete_router,
    prefix="/delete",
    tags=["Delete"]
)
app.include_router(platforms.router)



@app.on_event("startup")
def startup_event():

    initialize_search_cache()

    print("Loading AI models...")

    _ = model_manager.semantic_model
    _ = model_manager.clip_model
    _ = model_manager.clip_processor
    _ = model_manager.whisper_model
    _ = model_manager.ocr_model

    print("AI models ready.")


@app.get("/")
def home():

    return {
        "message": "CogniSeek Backend Running"
    }