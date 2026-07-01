from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from app.auth.jwt_handler import verify_token
from app.auth.auth_service import get_user_by_email


security = HTTPBearer()


def get_current_user(

    credentials: HTTPAuthorizationCredentials = Depends(
        security
    )

):

    token = credentials.credentials

    payload = verify_token(token)

    if payload is None:

        raise HTTPException(

            status_code=401,

            detail="Invalid or expired token."

        )

    email = payload.get("email")

    user = get_user_by_email(email)

    if user is None:

        raise HTTPException(

            status_code=401,

            detail="User not found."

        )

    return user