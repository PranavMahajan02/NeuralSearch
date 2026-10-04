"""users.token_version for JWT revocation

Revision ID: 0002_users_token_version
Revises: 0001_baseline
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_users_token_version"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0")
        )
    )


def downgrade():

    op.drop_column("users", "token_version")
