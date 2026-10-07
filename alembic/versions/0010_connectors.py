"""connector metadata: default branch, Drive link, too_large status,
downloaded_files job counter, PKCE code verifier on oauth_states

Revision ID: 0010_connectors
Revises: 0009_file_name_trigram
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_connectors"
down_revision = "0009_file_name_trigram"
branch_labels = None
depends_on = None


OLD_STATUSES = "status IN ('indexed', 'no_content', 'failed', 'unsupported')"
NEW_STATUSES = "status IN ('indexed', 'no_content', 'failed', 'unsupported', 'too_large')"


def upgrade():

    op.add_column("indexed_files", sa.Column("default_branch", sa.Text()))
    op.add_column("indexed_files", sa.Column("web_view_link", sa.Text()))

    op.drop_constraint("ck_indexed_files_status", "indexed_files", type_="check")
    op.create_check_constraint("ck_indexed_files_status", "indexed_files", NEW_STATUSES)

    op.add_column(
        "indexing_jobs",
        sa.Column("downloaded_files", sa.Integer(), nullable=False, server_default=sa.text("0"))
    )

    op.add_column("oauth_states", sa.Column("code_verifier", sa.Text()))


def downgrade():

    op.drop_column("oauth_states", "code_verifier")
    op.drop_column("indexing_jobs", "downloaded_files")

    op.execute("UPDATE indexed_files SET status = 'unsupported' WHERE status = 'too_large'")
    op.drop_constraint("ck_indexed_files_status", "indexed_files", type_="check")
    op.create_check_constraint("ck_indexed_files_status", "indexed_files", OLD_STATUSES)

    op.drop_column("indexed_files", "web_view_link")
    op.drop_column("indexed_files", "default_branch")
