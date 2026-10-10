from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.auth_dependency import get_current_user
from app.database.db import get_db
from app.models import response_models as rm
from app.scheduler.jobs import indexed_platforms

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login-state", response_model=rm.LoginStateResponse)
def login_state(current_user=Depends(get_current_user), db: Session = Depends(get_db)):

    # A platform counts as indexed once any job finished successfully,
    # regardless of what is queued or running now.
    platforms = indexed_platforms(db, current_user["id"])

    return {"has_indexed": len(platforms) > 0, "platforms": platforms}
