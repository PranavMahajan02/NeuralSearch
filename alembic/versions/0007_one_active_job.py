"""at most one queued/running job per (user, platform)

A partial unique index makes the 409 on duplicate enqueue race-free.

Revision ID: 0007_one_active_job
Revises: 0006_job_queue
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_one_active_job"
down_revision = "0006_job_queue"
branch_labels = None
depends_on = None


def upgrade():

    op.create_index(
        "uq_indexing_jobs_one_active",
        "indexing_jobs",
        ["user_id", "platform"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')")
    )


def downgrade():

    op.drop_index("uq_indexing_jobs_one_active", table_name="indexing_jobs")
