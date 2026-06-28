from fastapi import FastAPI

from app.routes.search import router as search_router
from app.routes.index import router as index_router
from app.routes.upload import router as upload_router
from app.routes.delete import router as delete_router
from app.routes.open import router as open_router
from app.routes.scheduler import router as scheduler_router
from app.routes.dashboard import router as dashboard_router
from app.routes import platforms

app = FastAPI(
    title="CogniSeek API",
    description="Unified Semantic Search Backend",
    version="1.0.0"
)

# Register Routers
app.include_router(search_router)
app.include_router(index_router)
app.include_router(upload_router)
app.include_router(open_router)
app.include_router(scheduler_router)
app.include_router(dashboard_router)
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