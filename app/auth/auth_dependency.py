import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_token
from app.database.db import get_db
from app.database.models import User

# auto_error=False so a missing header yields our 401 (not a 403).
security = HTTPBearer(auto_error=False)


def _unauthorized(detail: str):

    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):

    if credentials is None or not credentials.credentials:
        raise _unauthorized("Not authenticated.")

    payload = verify_token(credentials.credentials)

    if payload is None:
        raise _unauthorized("Invalid or expired token.")

    try:
        user_id = uuid.UUID(str(payload.get("user_id")))
    except ValueError:
        raise _unauthorized("Invalid or expired token.") from None

    user = db.get(User, user_id)

    if user is None:
        raise _unauthorized("Invalid or expired token.")

    # Logout bumps token_version, which revokes every older token.
    if payload.get("tv") != user.token_version:
        raise _unauthorized("Token has been revoked.")

    return {
        "id": str(user.id),
        "name": user.full_name,
        "email": user.email,
        "onboarding_completed": bool(user.onboarding_completed)
    }
