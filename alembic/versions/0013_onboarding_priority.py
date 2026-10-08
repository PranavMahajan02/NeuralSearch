"""users.onboarding_completed; indexing_jobs.priority

Existing users who already have indexed files have finished onboarding.

Revision ID: 0013_onboarding_priority
Revises: 0012_file_metadata
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_onboarding_priority"
down_revision = "0012_file_metadata"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column(
        "users",
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.execute(
        "UPDATE users SET onboarding_completed = true "
        "WHERE EXISTS (SELECT 1 FROM indexed_files f WHERE f.user_id = users.id)"
    )

    op.add_column(
        "indexing_jobs",
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0"))
    )


def downgrade():

    op.drop_column("indexing_jobs", "priority")
    op.drop_column("users", "onboarding_completed")
