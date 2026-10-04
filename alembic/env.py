from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.database.db import Base
import app.database.models  # noqa: F401  (registers tables on Base.metadata)


config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():

    # Tests pass a URL through config.attributes; everything else uses settings.
    return config.attributes.get("database_url") or settings.DATABASE_URL


COMPARE_OPTIONS = dict(
    compare_type=True,
    compare_server_default=True
)


def run_migrations_offline():

    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **COMPARE_OPTIONS
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():

    connectable = create_engine(get_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            **COMPARE_OPTIONS
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
