"""data: encrypt existing platform_connections tokens at rest

Idempotent: values that already decrypt with TOKEN_ENCRYPTION_KEY are skipped.
Requires the same TOKEN_ENCRYPTION_KEY the app runs with.

Revision ID: 0005_encrypt_platform_tokens
Revises: 0004_oauth_states
"""

from alembic import op
import sqlalchemy as sa

from app.core.crypto import decrypt, encrypt, is_encrypted


revision = "0005_encrypt_platform_tokens"
down_revision = "0004_oauth_states"
branch_labels = None
depends_on = None


COLUMNS = ("access_token", "refresh_token", "token_json")


def _transform(convert, should_convert):

    bind = op.get_bind()

    rows = bind.execute(
        sa.text(
            "SELECT id, access_token, refresh_token, token_json "
            "FROM platform_connections"
        )
    ).mappings().all()

    for row in rows:

        updates = {
            column: convert(row[column])
            for column in COLUMNS
            if row[column] is not None and should_convert(row[column])
        }

        if not updates:
            continue

        assignments = ", ".join(f"{column} = :{column}" for column in updates)

        bind.execute(
            sa.text(f"UPDATE platform_connections SET {assignments} WHERE id = :id"),
            {**updates, "id": row["id"]}
        )


def upgrade():

    _transform(encrypt, lambda value: not is_encrypted(value))


def downgrade():

    _transform(decrypt, is_encrypted)
