import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from app.core.config import settings


SECRET_KEY = settings.JWT_SECRET_KEY

ALGORITHM = settings.JWT_ALGORITHM

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(user_id: str, token_version: int) -> str:
    """Claims: user_id, tv (token_version for revocation), jti, iat, exp."""

    now = datetime.now(timezone.utc)

    payload = {
        "user_id": str(user_id),
        "tv": int(token_version),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_token(token: str):

    try:

        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    except JWTError:

        return None
