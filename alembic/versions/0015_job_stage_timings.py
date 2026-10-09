"""indexing_jobs.stage_timings: seconds per indexing stage ("where the time went").

Revision ID: 0015_job_stage_timings
Revises: 0014_timestamptz
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0015_job_stage_timings"
down_revision = "0014_timestamptz"
branch_labels = None
depends_on = None


def upgrade():

    op.add_column("indexing_jobs", sa.Column("stage_timings", JSONB(), nullable=True))


def downgrade():

    op.drop_column("indexing_jobs", "stage_timings")
