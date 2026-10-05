"""pg_trgm + GIN trigram index on indexed_files.file_name (filename search)

Lets search find files by (near-)matching names even when their content
ranks low in the vector search (BUG-21).

Revision ID: 0009_file_name_trigram
Revises: 0008_ledger
"""

from alembic import op


revision = "0009_file_name_trigram"
down_revision = "0008_ledger"
branch_labels = None
depends_on = None


def upgrade():

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(
        "ix_indexed_files_file_name_trgm",
        "indexed_files",
        ["file_name"],
        postgresql_using="gin",
        postgresql_ops={"file_name": "gin_trgm_ops"}
    )


def downgrade():

    op.drop_index("ix_indexed_files_file_name_trgm", table_name="indexed_files")
