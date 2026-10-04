import re

from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID


BCRYPT_MAX_BYTES = 72


def _normalize_email(value):

    return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(BaseModel):

    name: str
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):

        return _normalize_email(value)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:

        value = value.strip()

        if not 1 <= len(value) <= 100:
            raise ValueError("Name must be 1-100 characters.")

        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:

        if not 8 <= len(value) <= 128:
            raise ValueError("Password must be 8-128 characters.")

        if len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError(
                f"Password must be at most {BCRYPT_MAX_BYTES} bytes "
                "(fewer characters if you use non-ASCII characters)."
            )

        if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
            raise ValueError("Password must contain at least one letter and one digit.")

        return value


class LoginRequest(BaseModel):

    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):

        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:

        # Same bcrypt limit as registration: reject cleanly instead of crashing.
        if not value or len(value.encode("utf-8")) > BCRYPT_MAX_BYTES:
            raise ValueError("Invalid password.")

        return value


class UserResponse(BaseModel):

    id: UUID
    name: str
    email: EmailStr


class TokenResponse(BaseModel):

    access_token: str
    token_type: str
