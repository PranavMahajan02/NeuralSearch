from fastapi import Depends
from fastapi import HTTPException

from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer

from sqlalchemy.orm import Session

from app.auth.jwt_handler import verify_token

from app.database.db import get_db
from app.database.models import User


security = HTTPBearer()


def get_current_user(

    credentials: HTTPAuthorizationCredentials = Depends(security),

    db: Session = Depends(get_db)

):

    token = credentials.credentials

    payload = verify_token(token)

    if payload is None:

        raise HTTPException(

            status_code=401,

            detail="Invalid or expired token."

        )

    email = payload.get("email")

    user = (

        db.query(User)

        .filter(User.email == email)

        .first()

    )

    if user is None:

        raise HTTPException(

            status_code=401,

            detail="User not found."

        )

    return {

        "id": str(user.id),

        "name": user.full_name,

        "email": user.email

    }