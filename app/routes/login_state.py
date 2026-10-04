from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import IndexingJob
from app.auth.auth_dependency import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.get("/login-state")
def login_state(

    current_user=Depends(get_current_user),

    db: Session = Depends(get_db)

):

    jobs = (

        db.query(IndexingJob)

        .filter(

            IndexingJob.user_id == current_user["id"],

            IndexingJob.status == "completed"

        )

        .all()

    )

    return {

        "has_indexed": len(jobs) > 0,

        "platforms": [

            job.platform

            for job in jobs

        ]

    }