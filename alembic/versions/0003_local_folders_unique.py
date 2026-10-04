"""unique (user_id, folder_path) on local_storage_folders

Revision ID: 0003_local_folders_unique
Revises: 0002_users_token_version
"""

from alembic import op


revision = "0003_local_folders_unique"
down_revision = "0002_users_token_version"
branch_labels = None
depends_on = None


def upgrade():

    op.create_unique_constraint(
        "uq_local_storage_folders_user_path",
        "local_storage_folders",
        ["user_id", "folder_path"]
    )


def downgrade():

    op.drop_constraint(
        "uq_local_storage_folders_user_path",
        "local_storage_folders",
        type_="unique"
    )
