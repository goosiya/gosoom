"""시드 관리자 멱등성 테스트 (실 DB + 롤백, AC4).

실 DB 미가용 환경을 고려해 시드 함수를 import해 db_session으로 직접 호출한다(스크립트 미실행).
SEED_ADMIN_* 설정은 monkeypatch로 주입(실제 .env 의존 회피).
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.seed import seed_admin

pytestmark = pytest.mark.asyncio


async def test_seed_admin_is_idempotent(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """시드 2회 실행 → 관리자 1개만 존재(멱등), is_seed=True, user_role==admin(AC4)."""
    monkeypatch.setattr(settings, "seed_admin_email", "seed-admin@gosoom.local")
    monkeypatch.setattr(settings, "seed_admin_password", "seed-strong-password")
    monkeypatch.setattr(settings, "seed_admin_display_name", "관리자")

    first = await seed_admin(db_session)
    assert "생성 완료" in first

    second = await seed_admin(db_session)
    assert "skip" in second

    # 동일 이메일 관리자가 정확히 1개
    count = await db_session.scalar(
        select(func.count())
        .select_from(User)
        .where(User.email == "seed-admin@gosoom.local")
    )
    assert count == 1

    row = await db_session.execute(
        select(User).where(User.email == "seed-admin@gosoom.local")
    )
    admin = row.scalar_one()
    assert admin.is_seed is True
    assert admin.user_role is UserRole.ADMIN
    assert admin.is_active is True


async def test_seed_admin_missing_config_raises(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEED_ADMIN_* 미설정 시 명확한 에러(앱 크래시 아님)."""
    monkeypatch.setattr(settings, "seed_admin_email", None)
    monkeypatch.setattr(settings, "seed_admin_password", None)

    with pytest.raises(ValueError, match="SEED_ADMIN"):
        await seed_admin(db_session)


async def test_seed_admin_rejects_email_owned_by_regular_user(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEED_ADMIN_EMAIL을 일반 계정이 선점하면 조용히 skip하지 않고 명확히 실패."""
    monkeypatch.setattr(settings, "seed_admin_email", "taken@gosoom.local")
    monkeypatch.setattr(settings, "seed_admin_password", "seed-strong-password")
    monkeypatch.setattr(settings, "seed_admin_display_name", "관리자")

    # 동일 이메일을 일반 customer가 선점
    db_session.add(
        User(
            email="taken@gosoom.local",
            password_hash=hash_password("whatever-pass"),
            display_name="선점자",
            user_role=UserRole.CUSTOMER,
            is_active=True,
        )
    )
    await db_session.flush()

    # 시드는 admin이 아닌 행을 발견 → "이미 일반 계정" ValueError(자동 승격·조용한 skip 금지)
    with pytest.raises(ValueError, match="이미 일반 계정"):
        await seed_admin(db_session)
