"""file metadata on the ledger: size, modification time, MIME type

Filled on the next index of each file; NULL until then.

Revision ID: 0012_file_metadata
Revises: 0011_excluded_status
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_file_metadata"
down_revision = "0011_excluded_status"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column("indexed_files", sa.Column("size_bytes", sa.BigInteger()))
    op.add_column("indexed_files", sa.Column("modified_at", sa.DateTime()))
    op.add_column("indexed_files", sa.Column("mime_type", sa.Text()))


def downgrade():

    op.drop_column("indexed_files", "mime_type")
    op.drop_column("indexed_files", "modified_at")
    op.drop_column("indexed_files", "size_bytes")
