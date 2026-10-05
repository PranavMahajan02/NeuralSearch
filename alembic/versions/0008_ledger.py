"""indexed_files becomes the per-file ledger; drop unused search_cache

Both tables were unused and empty (checked before writing this migration),
so indexed_files is recreated in its new shape.

Revision ID: 0008_ledger
Revises: 0007_one_active_job
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_ledger"
down_revision = "0007_one_active_job"
branch_labels = None
depends_on = None


STATUS_CHECK = "status IN ('indexed', 'no_content', 'failed', 'unsupported')"


def upgrade():

    op.drop_table("search_cache")
    op.drop_table("indexed_files")

    op.create_table(
        "indexed_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("display_path", sa.Text(), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("version", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error", sa.Text()),
        sa.Column("owner", sa.Text()),
        sa.Column("repo", sa.Text()),
        sa.Column("indexed_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="indexed_files_pkey"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="indexed_files_user_id_fkey", ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "platform", "source_id", name="uq_indexed_files_source"),
        sa.CheckConstraint(STATUS_CHECK, name="ck_indexed_files_status"),
    )
    op.create_index("ix_indexed_files_user_platform", "indexed_files", ["user_id", "platform"])


def downgrade():

    op.drop_index("ix_indexed_files_user_platform", table_name="indexed_files")
    op.drop_table("indexed_files")

    op.create_table(
        "indexed_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("external_file_id", sa.Text()),
        sa.Column("file_path", sa.Text()),
        sa.Column("file_name", sa.Text()),
        sa.Column("file_hash", sa.Text()),
        sa.Column("modified_time", sa.DateTime()),
        sa.Column("indexed_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="indexed_files_pkey"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="indexed_files_user_id_fkey", ondelete="CASCADE"),
    )
    op.create_table(
        "search_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("file_id", postgresql.UUID(as_uuid=True)),
        sa.Column("embedding_path", sa.Text()),
        sa.Column("cache_updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id", name="search_cache_pkey"),
        sa.ForeignKeyConstraint(["file_id"], ["indexed_files.id"], name="search_cache_file_id_fkey", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="search_cache_user_id_fkey", ondelete="CASCADE"),
    )
