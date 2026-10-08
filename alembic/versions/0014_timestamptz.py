"""Every timestamp column becomes timestamptz.

Existing values were written as UTC (Python utcnow() and CURRENT_TIMESTAMP in a
UTC server), so they are read AT TIME ZONE 'UTC'. API timestamps then carry an
offset ("2026-10-08T08:00:00+00:00").

Revision ID: 0014_timestamptz
Revises: 0013_onboarding_priority
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_timestamptz"
down_revision = "0013_onboarding_priority"
branch_labels = None
depends_on = None


def _columns(data_type):

    rows = op.get_bind().execute(sa.text(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND data_type = :t AND table_name <> 'alembic_version' "
        "ORDER BY table_name, column_name"
    ), {"t": data_type})
    return list(rows)


def upgrade():

    for table, column in _columns("timestamp without time zone"):
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
            f'TYPE timestamptz USING "{column}" AT TIME ZONE \'UTC\''
        )


def downgrade():

    for table, column in _columns("timestamp with time zone"):
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
            f'TYPE timestamp USING "{column}" AT TIME ZONE \'UTC\''
        )
