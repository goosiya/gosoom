"""기본 카테고리 시드 멱등성 테스트 (실 DB + 롤백, Story 1.6 AC2).

seed_categories를 db_session으로 직접 2회 호출 → DEFAULT_CATEGORIES 집합과 정확히 일치(중복 0).
시드는 env/시크릿 불요 — 관리자 시드(SEED_ADMIN_*)와 달리 항상 동작해야 한다(Epic 2/3 의존성).
"""

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.seed import DEFAULT_CATEGORIES, seed_categories

pytestmark = pytest.mark.asyncio


async def test_seed_categories_creates_default_set(
    db_session: AsyncSession,
) -> None:
    """첫 시드 → DEFAULT_CATEGORIES 전체가 활성으로 생성된다(AC2)."""
    await db_session.execute(delete(Category))
    await db_session.flush()
    message = await seed_categories(db_session)
    # 메시지 리터럴에 "신규"가 항상 포함되므로 숫자까지 단정해 created 카운트를 실제 검증.
    assert f"신규 {len(DEFAULT_CATEGORIES)}개" in message

    rows = await db_session.execute(
        select(Category.name).where(Category.deleted_at.is_(None))
    )
    names = {n for (n,) in rows.all()}
    assert names == set(DEFAULT_CATEGORIES)


async def test_seed_categories_is_idempotent(
    db_session: AsyncSession,
) -> None:
    """시드 2회 실행 → 카테고리는 중복 없이 정확히 DEFAULT_CATEGORIES 집합만 존재(AC2 멱등)."""
    await db_session.execute(delete(Category))
    await db_session.flush()
    first = await seed_categories(db_session)
    # 1회차: DEFAULT_CATEGORIES 전부 신규 생성(숫자까지 단정 — 동어반복 회피).
    assert f"신규 {len(DEFAULT_CATEGORIES)}개" in first

    second = await seed_categories(db_session)
    # 2회차: 신규 0개 + 전부 기존 skip(카운트 단정으로 멱등 회계 실증).
    assert "신규 0개" in second
    assert f"기존 {len(DEFAULT_CATEGORIES)}개" in second

    # 총 개수 = DEFAULT_CATEGORIES 개수(중복 0)
    count = await db_session.scalar(
        select(func.count())
        .select_from(Category)
        .where(Category.deleted_at.is_(None))
    )
    assert count == len(DEFAULT_CATEGORIES)

    # 각 이름이 정확히 1개씩
    for name in DEFAULT_CATEGORIES:
        n = await db_session.scalar(
            select(func.count())
            .select_from(Category)
            .where(Category.name == name, Category.deleted_at.is_(None))
        )
        assert n == 1, f"{name} 중복"


async def test_seed_categories_all_active(db_session: AsyncSession) -> None:
    """시드된 카테고리는 전부 is_active=True(조회 API가 즉시 반환 가능)."""
    await seed_categories(db_session)
    rows = await db_session.execute(select(Category.is_active))
    assert all(active for (active,) in rows.all())
