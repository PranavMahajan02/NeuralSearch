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
from app.routes import platforms

app = FastAPI(
    title="CogniSeek API",
    description="Unified Semantic Search Backend",
    version="1.0.0"
)

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
app.include_router(upload_router)
app.include_router(open_router)
app.include_router(scheduler_router)
app.include_router(dashboard_router)
app.include_router(auth_router)
app.include_router(google_drive_router)
app.include_router(github_router)
app.include_router(
    delete_router,
    prefix="/delete",
    tags=["Delete"]
)
app.include_router(platforms.router)


@app.get("/")
def home():

    return {
        "message": "CogniSeek Backend Running"
    }