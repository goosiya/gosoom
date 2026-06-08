import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 앱 설정(.env)에서 DB URL을 주입 — alembic.ini의 리터럴 sqlalchemy.url에 시크릿을 두지 않는다.
from app.core.config import settings
from app.core.db import Base

# 도메인 모델을 Base.metadata에 등록(autogenerate용). Story 1.3+에서 모델 추가 시
# app/models/__init__.py가 각 모델 모듈을 import하면 여기서 자동 반영된다.
import app.models  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# .env의 DATABASE_URL을 런타임 주입(시크릿 커밋 금지).
# 주의: config.set_main_option()은 ConfigParser에 값을 쓰므로 URL에 리터럴 '%'가
# 있으면 보간 오류(ValueError)가 난다. 따라서 ini를 거치지 않고 settings에서 직접 사용한다.

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# autogenerate / 마이그레이션 target = 앱 선언적 베이스 메타데이터
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # ini 섹션을 가져온 뒤 URL만 dict에 직접 주입 — ConfigParser '%' 보간을 우회.
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
