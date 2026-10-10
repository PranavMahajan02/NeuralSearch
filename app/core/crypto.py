"""Encryption at rest for OAuth tokens (Fernet: AES-128-CBC + HMAC-SHA256)."""

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import Text, TypeDecorator

from app.core.config import settings

_fernet = Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:

    return _fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str) -> str:

    return _fernet.decrypt(value.encode("ascii")).decode("utf-8")


def is_encrypted(value: str) -> bool:

    try:
        decrypt(value)
        return True
    except (InvalidToken, ValueError, UnicodeError):
        return False


class EncryptedText(TypeDecorator):
    """A TEXT column that is encrypted on write and decrypted on read.

    The DB type stays TEXT, so the schema (and `alembic check`) is unchanged.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):

        if value is None:
            return None

        return encrypt(value)

    def process_result_value(self, value, dialect):

        if value is None:
            return None

        return decrypt(value)
