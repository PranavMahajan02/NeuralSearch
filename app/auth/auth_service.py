from sqlalchemy.orm import Session

from app.database.db import SessionLocal
from app.database.models import User

from app.auth.password import (
    hash_password,
    verify_password
)

from app.auth.jwt_handler import create_access_token


def register_user(
    name,
    email,
    password
):

    db: Session = SessionLocal()

    try:

        existing = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if existing:
            raise ValueError(
                "Email already registered."
            )

        user = User(
            email=email,
            full_name=name,
            password_hash=hash_password(password)
        )

        db.add(user)

        db.commit()

        db.refresh(user)

        return {

            "id": user.id,
            "name": user.full_name,
            "email": user.email

        }

    finally:

        db.close()


def login_user(
    email,
    password
):

    db: Session = SessionLocal()

    try:

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        if user is None:

            raise ValueError(
                "Invalid email or password."
            )

        if not verify_password(
            password,
            user.password_hash
        ):

            raise ValueError(
                "Invalid email or password."
            )

        token = create_access_token(

            {

                "user_id": str(user.id),
                "email": user.email

            }

        )

        return {

            "access_token": token,
            "token_type": "bearer"

        }

    finally:

        db.close()