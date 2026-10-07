"""ledger status 'excluded' (generated/noise files: *.log, *.lock, *.min.js, *.map)

Revision ID: 0011_excluded_status
Revises: 0010_connectors
"""

from alembic import op


revision = "0011_excluded_status"
down_revision = "0010_connectors"
branch_labels = None
depends_on = None


OLD_STATUSES = "status IN ('indexed', 'no_content', 'failed', 'unsupported', 'too_large')"
NEW_STATUSES = "status IN ('indexed', 'no_content', 'failed', 'unsupported', 'too_large', 'excluded')"


def upgrade():

    op.drop_constraint("ck_indexed_files_status", "indexed_files", type_="check")
    op.create_check_constraint("ck_indexed_files_status", "indexed_files", NEW_STATUSES)


def downgrade():

    op.execute("UPDATE indexed_files SET status = 'unsupported' WHERE status = 'excluded'")
    op.drop_constraint("ck_indexed_files_status", "indexed_files", type_="check")
    op.create_check_constraint("ck_indexed_files_status", "indexed_files", OLD_STATUSES)
