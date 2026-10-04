from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.auth_dependency import get_current_user
from app.core.errors import AppError
from app.core.ownership import resolve_user_file
from app.database.db import get_db


router = APIRouter(
    prefix="/files",
    tags=["Files"]
)


@router.get("/local")
def download_local_file(
    path: str = Query(..., min_length=1),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    resolved = resolve_user_file(db, current_user["id"], path)

    if resolved is None:
        # 404 (not 403) so the endpoint does not reveal which files exist.
        raise AppError(404, "File not found.")

    return FileResponse(
        resolved,
        filename=resolved.name,
        content_disposition_type="attachment"
    )
