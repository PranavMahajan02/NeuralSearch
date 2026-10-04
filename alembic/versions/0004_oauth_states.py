"""oauth_states table (single-use OAuth CSRF state)

Revision ID: 0004_oauth_states
Revises: 0003_local_folders_unique
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_oauth_states"
down_revision = "0003_local_folders_unique"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "oauth_states",
        sa.Column("state", sa.String(128), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("state", name="oauth_states_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="oauth_states_user_id_fkey", ondelete="CASCADE"
        )
    )


def downgrade():

    op.drop_table("oauth_states")
