from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.jwt_handler import create_access_token
from app.auth.password import hash_password, verify_password
from app.database.db import SessionLocal
from app.database.models import User


def _find_by_email(db: Session, email: str):

    # Emails are stored lower-case from now on; older rows may not be.
    return db.query(User).filter(func.lower(User.email) == email.lower()).first()


def register_user(name, email, password):

    db: Session = SessionLocal()

    try:
        if _find_by_email(db, email):
            raise ValueError("Email already registered.")

        user = User(email=email, full_name=name, password_hash=hash_password(password))

        db.add(user)

        db.commit()

        db.refresh(user)

        return {"id": user.id, "name": user.full_name, "email": user.email}

    finally:
        db.close()


def login_user(email, password):

    db: Session = SessionLocal()

    try:
        user = _find_by_email(db, email)

        if user is None or not user.password_hash or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password.")

        token = create_access_token(user_id=str(user.id), token_version=user.token_version)

        return {"access_token": token, "token_type": "bearer"}

    finally:
        db.close()


def revoke_user_tokens(db: Session, user_id) -> None:
    """Invalidate every token issued to this user so far."""

    db.query(User).filter(User.id == user_id).update(
        {User.token_version: User.token_version + 1}, synchronize_session=False
    )

    db.commit()
