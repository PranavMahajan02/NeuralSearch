from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import limiter
from app.database.db import get_db
from app.scheduler.jobs import cancel_user_jobs

from app.models.auth_models import (
    RegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse
)

from app.auth.auth_service import (
    register_user,
    login_user,
    revoke_user_tokens
)

from app.auth.auth_dependency import (
    get_current_user
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def register(
    request: Request,
    body: RegisterRequest
):

    try:

        return register_user(
            body.name,
            body.email,
            body.password
        )

    except ValueError as e:

        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post(
    "/login",
    response_model=TokenResponse
)
@limiter.limit(settings.AUTH_RATE_LIMIT)
def login(
    request: Request,
    body: LoginRequest
):

    try:

        return login_user(
            body.email,
            body.password
        )

    except ValueError as e:

        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


@router.get(
    "/profile",
    response_model=UserResponse
)
def profile(
    current_user = Depends(
        get_current_user
    )
):

    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"]
    }


@router.post("/logout")
def logout(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Stop this user's indexing: queued jobs are cancelled, the running one
    # stops after its current file.
    cancel_user_jobs(
        db,
        current_user["id"]
    )

    revoke_user_tokens(
        db,
        current_user["id"]
    )

    return {
        "status": "success"
    }
