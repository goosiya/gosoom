"""테스트 공통 픽스처.

- `client`(기존): get_db를 가짜 세션으로 override해 실 DB 없이 헬스 라우트(SELECT 1)를 격리 검증.
- `db_session`/`client_db`(Story 1.3 추가): 실 DB + 트랜잭션 롤백.
  도메인 테스트는 실 DB로 검증한다(이메일 unique 등 DB 레벨 제약을 실제로 확인 — fake repo 금지).

  ⚠️ 핵심 함정: signup service가 `session.commit()`을 호출한다. 단순 롤백 픽스처는 commit이
  실제 반영되어 DB 오염·격리 붕괴. SQLAlchemy 2.0의 `join_transaction_mode="create_savepoint"`가
  세션 commit을 SAVEPOINT에 가두고, 바깥 트랜잭션을 롤백하면 테스트가 깨끗이 정리된다.
"""

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db import get_db
from app.main import app


class _FakeSession:
    """헬스 라우트의 `execute(text("SELECT 1"))`만 흉내내는 최소 가짜 세션."""

    async def execute(self, *_args: object, **_kwargs: object) -> None:
        return None


async def _override_get_db() -> AsyncIterator[_FakeSession]:
    yield _FakeSession()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """실 DB 연결에 외부 트랜잭션을 깔고, 세션 commit을 SAVEPOINT에 가둔 뒤 테스트 종료 시 전체 롤백."""
    # pytest-asyncio는 테스트마다 새 이벤트 루프를 만든다. 모듈 수준 prod 엔진을 재사용하면
    # 풀에 남은 이전(닫힌) 루프의 커넥션을 다시 쓰려다 "Event loop is closed"로 실패한다.
    # → 테스트마다 NullPool 전용 엔진을 만들어(현재 루프 바인딩) 끝나면 dispose.
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    connection = await test_engine.connect()
    trans = await connection.begin()
    # expire_on_commit=False로 SessionLocal과 동일하게: commit 후에도 ORM 속성 접근 가능
    # (미설정 시 commit 후 속성 만료 → response_model 직렬화가 lazy 로드 시도 → MissingGreenlet).
    session = AsyncSession(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()
        await test_engine.dispose()


@pytest.fixture
async def client_db(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """라우터가 롤백 세션(db_session)을 쓰도록 get_db override + AsyncClient."""

    async def _override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
