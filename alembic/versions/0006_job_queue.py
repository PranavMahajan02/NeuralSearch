"""DB-backed job queue: job status state machine, counters, errors table

- indexing_jobs.status limited to queued|running|completed|completed_with_errors|failed|cancelled
  (old "indexing" -> running, then failed by startup recovery;
   old "queued"/"not_started" -> cancelled, since the in-memory queue is gone)
- counters: processed/succeeded/failed/skipped_files, error_message,
  cancel_requested, created_at, heartbeat_at
- indexing_job_errors (per-file errors, capped at 200 per job in code)
- index used by the worker to claim the oldest queued job

Revision ID: 0006_job_queue
Revises: 0005_encrypt_platform_tokens
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_job_queue"
down_revision = "0005_encrypt_platform_tokens"
branch_labels = None
depends_on = None


STATUSES = ("queued", "running", "completed", "completed_with_errors", "failed", "cancelled")

STATUS_CHECK = "status IN (" + ", ".join(f"'{s}'" for s in STATUSES) + ")"


def upgrade():

    for column in ("processed_files", "succeeded_files", "failed_files", "skipped_files"):
        op.add_column(
            "indexing_jobs",
            sa.Column(column, sa.Integer(), nullable=False, server_default=sa.text("0"))
        )

    op.add_column("indexing_jobs", sa.Column("error_message", sa.Text()))
    op.add_column(
        "indexing_jobs",
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.add_column(
        "indexing_jobs",
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    )
    op.add_column("indexing_jobs", sa.Column("heartbeat_at", sa.DateTime()))

    # Existing rows: keep their original order, map legacy statuses.
    op.execute("UPDATE indexing_jobs SET created_at = COALESCE(started_at, created_at)")
    op.execute("UPDATE indexing_jobs SET status = 'running' WHERE status = 'indexing'")
    # Legacy queued rows belonged to the old in-memory queue, which no longer
    # exists. Leaving them queued would make the new worker start indexing on
    # the next boot, so they are closed instead.
    op.execute(
        "UPDATE indexing_jobs SET status = 'cancelled', "
        "error_message = 'Superseded by the database job queue (Phase 2 migration)' "
        "WHERE status IS NULL OR status IN ('queued', 'not_started')"
    )
    op.execute("UPDATE indexing_jobs SET processed_files = indexed_files, succeeded_files = indexed_files "
               "WHERE indexed_files IS NOT NULL")

    op.alter_column(
        "indexing_jobs", "status",
        existing_type=sa.String(30),
        nullable=False,
        server_default=sa.text("'queued'::character varying")
    )
    op.create_check_constraint("ck_indexing_jobs_status", "indexing_jobs", STATUS_CHECK)

    op.create_index(
        "ix_indexing_jobs_status_created_at",
        "indexing_jobs",
        ["status", "created_at"]
    )
    op.create_index(
        "ix_indexing_jobs_user_platform",
        "indexing_jobs",
        ["user_id", "platform"]
    )

    op.create_table(
        "indexing_job_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_ref", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="indexing_job_errors_pkey"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["indexing_jobs.id"],
            name="indexing_job_errors_job_id_fkey", ondelete="CASCADE"
        )
    )
    op.create_index("ix_indexing_job_errors_job_id", "indexing_job_errors", ["job_id"])


def downgrade():

    op.drop_index("ix_indexing_job_errors_job_id", table_name="indexing_job_errors")
    op.drop_table("indexing_job_errors")

    op.drop_index("ix_indexing_jobs_user_platform", table_name="indexing_jobs")
    op.drop_index("ix_indexing_jobs_status_created_at", table_name="indexing_jobs")
    op.drop_constraint("ck_indexing_jobs_status", "indexing_jobs", type_="check")

    op.alter_column(
        "indexing_jobs", "status",
        existing_type=sa.String(30),
        nullable=True,
        server_default=sa.text("'not_started'::character varying")
    )
    op.execute("UPDATE indexing_jobs SET status = 'indexing' WHERE status = 'running'")
    op.execute("UPDATE indexing_jobs SET status = 'completed' WHERE status = 'completed_with_errors'")
    op.execute("UPDATE indexing_jobs SET status = 'not_started' WHERE status IN ('failed', 'cancelled')")

    for column in (
        "heartbeat_at", "created_at", "cancel_requested", "error_message",
        "skipped_files", "failed_files", "succeeded_files", "processed_files"
    ):
        op.drop_column("indexing_jobs", column)
