"""비동기 DB 접근 계층 (SQLAlchemy 2.0 async + asyncpg).

- `engine`: 앱 단일 async 엔진. 모듈 import 시 생성되지만 실제 커넥션은 지연(lazy)된다.
- `get_db`: FastAPI `Depends`용 세션 의존성.
- `Base`: 모든 모델의 선언적 베이스. Alembic env.py가 `Base.metadata`를 target으로 참조.

이식성(NFR6): Phase1(Supabase)→Phase2(Railway) 이관은 `DATABASE_URL`만 변경.
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# async 엔진 (asyncpg). pool_pre_ping으로 풀러 끊긴 커넥션 자동 회복.
engine = create_async_engine(settings.database_url, pool_pre_ping=True)

# 세션 팩토리. expire_on_commit=False로 커밋 후 ORM 객체 접근 가능.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """모든 SQLAlchemy 모델의 선언적 베이스 (메타데이터 단일 소스)."""


async def get_db() -> AsyncIterator[AsyncSession]:
    """요청 스코프 async 세션 의존성 (FastAPI Depends용)."""
    async with SessionLocal() as session:
        yield session
