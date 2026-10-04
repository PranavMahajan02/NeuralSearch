from fastapi import APIRouter
from fastapi import Depends

from app.auth.auth_dependency import get_current_user

from app.services.dashboard_service import (
    get_dashboard_stats
)

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats")
def dashboard_stats(

    current_user=Depends(get_current_user)

):

    return get_dashboard_stats(

        current_user["id"]

    )

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

@router.get("/stats")
def dashboard_stats(

    current_user = Depends(get_current_user)

):

    return get_dashboard_stats(

        current_user["id"]

    )

@router.get("/platforms")
def dashboard_platforms(
    current_user=Depends(get_current_user)
):
    from app.services.dashboard_service import get_dashboard_platforms

    return get_dashboard_platforms(
        current_user["id"]
    )