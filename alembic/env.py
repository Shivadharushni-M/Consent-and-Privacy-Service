from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import configparser

config = context.config

# Disable interpolation to handle URLs with % characters (e.g., %40 for @)
# Create a no-op interpolation class that doesn't process % characters
class NoInterpolation(configparser.Interpolation):
    def before_get(self, parser, section, option, value, defaults):
        return value
    
    def before_set(self, parser, section, option, value):
        return value
    
    def before_read(self, parser, section, option, value):
        return value

if hasattr(config, 'file_config'):
    config.file_config._interpolation = NoInterpolation()

from app.config import settings
config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from app.db.database import Base
from app.models.consent import ConsentHistory
from app.models.audit import AuditLog

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
