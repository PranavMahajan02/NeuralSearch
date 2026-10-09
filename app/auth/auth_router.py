import uuid

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
    TokenResponse,
    ChangePasswordRequest,
    CurrentPasswordRequest
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
        "email": current_user["email"],
        "onboarding_completed": current_user["onboarding_completed"]
    }


def _finish_onboarding(db: Session, user_id) -> dict:

    from app.database.models import User

    user = db.get(User, uuid.UUID(str(user_id)))
    user.onboarding_completed = True
    db.commit()

    return {"onboarding_completed": True}


@router.post("/onboarding/complete")
def onboarding_complete(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """The user started indexing from the onboarding flow."""

    return _finish_onboarding(db, current_user["id"])


@router.post("/onboarding/skip")
def onboarding_skip(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """The user chose "Skip for now"; they manage platforms from the Platforms page."""

    return _finish_onboarding(db, current_user["id"])


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


# ----------------------------------------------------------------------
# Data rights: password change, export, account deletion
# ----------------------------------------------------------------------

def _require_password(db: Session, user_id, password: str):
    """403 (not 401: the session itself is valid) when the password is wrong."""

    from app.auth.password import verify_password
    from app.database.models import User

    user = db.get(User, uuid.UUID(str(user_id)))

    if user is None or not user.password_hash or not password or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect.")

    return user


@router.post("/change-password")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """New password (registration policy); every existing session ends, this one included."""

    from app.auth.password import hash_password

    user = _require_password(db, current_user["id"], body.current_password)
    user.password_hash = hash_password(body.new_password)
    db.commit()

    revoke_user_tokens(db, user.id)   # token_version + 1: all tokens, including this one

    return {"status": "success", "message": "Password changed. Please sign in again."}


@router.get("/export")
def export_data(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Everything CogniSeek stores about you as JSON: profile, connections (account
    names only, never tokens), folders, jobs and the file ledger. No vectors or contents."""

    from fastapi.responses import JSONResponse

    from app.services.account_service import export_account

    return JSONResponse(
        export_account(db, uuid.UUID(str(current_user["id"]))),
        headers={"Content-Disposition": 'attachment; filename="cogniseek-export.json"'}
    )


@router.delete("/account")
@limiter.limit(settings.AUTH_RATE_LIMIT)
def delete_my_account(
    request: Request,
    body: CurrentPasswordRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete the account and ALL its data (needs the current password). Platform grants
    are revoked at Google/GitHub; the token stops working at once (the user no longer exists)."""

    from app.services.account_service import JobStillRunning, delete_account

    user = _require_password(db, current_user["id"], body.password)

    try:
        report = delete_account(db, user.id)
    except JobStillRunning:
        raise HTTPException(
            status_code=409,
            detail="An indexing job is still running. It has been asked to stop - try again in a moment."
        )

    return {
        "status": "success",
        "deleted_files": report.ledger_rows,
        "revoked": report.revoked,
    }
