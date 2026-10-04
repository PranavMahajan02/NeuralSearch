"""baseline: schema as it existed before Alembic (Phase 1)

Existing databases are stamped at this revision (`alembic stamp 0001_baseline`);
fresh databases are created by it.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
GEN_UUID = sa.text("gen_random_uuid()")
NOW = sa.text("CURRENT_TIMESTAMP")


def upgrade():

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "users",
        sa.Column("id", UUID, server_default=GEN_UUID, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.Column("last_login", sa.DateTime(), server_default=NOW),
        sa.Column("password_hash", sa.Text()),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        sa.UniqueConstraint("email", name="users_email_key")
    )

    op.create_table(
        "platform_connections",
        sa.Column("id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("platform", sa.String()),
        sa.Column("account_email", sa.String()),
        sa.Column("account_name", sa.String()),
        sa.Column("access_token", sa.Text()),
        sa.Column("refresh_token", sa.Text()),
        sa.Column("token_json", sa.Text()),
        sa.Column("token_type", sa.Text()),
        sa.Column("connected", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name="platform_connections_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="platform_connections_user_id_fkey"
        )
    )

    op.create_table(
        "indexing_jobs",
        sa.Column("id", UUID, server_default=GEN_UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column(
            "status", sa.String(30),
            server_default=sa.text("'not_started'::character varying")
        ),
        sa.Column("total_files", sa.Integer(), server_default=sa.text("0")),
        sa.Column("indexed_files", sa.Integer(), server_default=sa.text("0")),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("last_index_time", sa.DateTime()),
        sa.Column("needs_reindex", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("current_file", sa.Text(), server_default=sa.text("''::text")),
        sa.PrimaryKeyConstraint("id", name="indexing_jobs_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="indexing_jobs_user_id_fkey", ondelete="CASCADE"
        )
    )

    op.create_table(
        "local_storage_folders",
        sa.Column("id", UUID, server_default=GEN_UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("folder_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=NOW),
        sa.PrimaryKeyConstraint("id", name="local_storage_folders_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="local_storage_folders_user_id_fkey", ondelete="CASCADE"
        )
    )

    op.create_table(
        "indexed_files",
        sa.Column("id", UUID, server_default=GEN_UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("external_file_id", sa.Text()),
        sa.Column("file_path", sa.Text()),
        sa.Column("file_name", sa.Text()),
        sa.Column("file_hash", sa.Text()),
        sa.Column("modified_time", sa.DateTime()),
        sa.Column("indexed_at", sa.DateTime(), server_default=NOW),
        sa.PrimaryKeyConstraint("id", name="indexed_files_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="indexed_files_user_id_fkey", ondelete="CASCADE"
        )
    )

    op.create_table(
        "search_cache",
        sa.Column("id", UUID, server_default=GEN_UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("file_id", UUID),
        sa.Column("embedding_path", sa.Text()),
        sa.Column("cache_updated_at", sa.DateTime(), server_default=NOW),
        sa.PrimaryKeyConstraint("id", name="search_cache_pkey"),
        sa.ForeignKeyConstraint(
            ["file_id"], ["indexed_files.id"],
            name="search_cache_file_id_fkey", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="search_cache_user_id_fkey", ondelete="CASCADE"
        )
    )

    op.create_table(
        "indexing_history",
        sa.Column("id", UUID, server_default=GEN_UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("files_indexed", sa.Integer(), server_default=sa.text("0")),
        sa.Column("status", sa.String(30)),
        sa.Column("remarks", sa.Text()),
        sa.PrimaryKeyConstraint("id", name="indexing_history_pkey"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="indexing_history_user_id_fkey", ondelete="CASCADE"
        )
    )


def downgrade():

    for table in (
        "indexing_history",
        "search_cache",
        "indexed_files",
        "local_storage_folders",
        "indexing_jobs",
        "platform_connections",
        "users"
    ):
        op.drop_table(table)
