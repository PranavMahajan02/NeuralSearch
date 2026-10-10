from fastapi import APIRouter, Depends

from app.auth.auth_dependency import get_current_user
from app.models import response_models as rm
from app.services.dashboard_service import get_dashboard_platforms, get_dashboard_stats, get_recent_files

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/stats", response_model=rm.DashboardStats, response_model_exclude_unset=True)
def dashboard_stats(
    current_user=Depends(get_current_user)
):

    return get_dashboard_stats(
        current_user["id"]
    )


@router.get("/recent", response_model=rm.RecentResponse)
def dashboard_recent(
    current_user=Depends(get_current_user)
):

    return {"files": get_recent_files(current_user["id"])}


@router.get("/platforms", response_model=dict[str, rm.PlatformDetail], response_model_exclude_unset=True)
def dashboard_platforms(
    current_user=Depends(get_current_user)
):

    return get_dashboard_platforms(
        current_user["id"]
    )
