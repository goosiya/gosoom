"""ensure_owner_or_admin 소유권 헬퍼 단위 테스트(AC4).

순수 함수(DB·HTTP 무관)이므로 경량 User 인스턴스로 직접 호출 검증한다 — DB 시드 불요.
- 본인 자원 → 통과(예외 없음).
- 타인 자원 + customer/pro → ForbiddenError.
- 타인 자원 + admin → 통과(전체 허용).
"""

from uuid import uuid4

import pytest

from app.core.authz import ensure_owner_or_admin
from app.core.exceptions import ForbiddenError
from app.models.user import User, UserRole


def _user(user_id, role: UserRole) -> User:
    """id/user_role만 채운 경량 User 인스턴스(DB 미사용)."""
    user = User()
    user.id = user_id
    user.user_role = role
    return user


def test_owner_passes() -> None:
    """본인 소유 자원(id 일치) → 예외 없이 통과."""
    uid = uuid4()
    current = _user(uid, UserRole.CUSTOMER)
    # 예외가 발생하지 않으면 성공.
    ensure_owner_or_admin(uid, current)


def test_non_owner_customer_forbidden() -> None:
    """타인 자원 + customer → ForbiddenError(403)."""
    current = _user(uuid4(), UserRole.CUSTOMER)
    with pytest.raises(ForbiddenError):
        ensure_owner_or_admin(uuid4(), current)


def test_non_owner_pro_forbidden() -> None:
    """타인 자원 + pro → ForbiddenError(403)."""
    current = _user(uuid4(), UserRole.PRO)
    with pytest.raises(ForbiddenError):
        ensure_owner_or_admin(uuid4(), current)


def test_admin_passes_on_others_resource() -> None:
    """타인 자원 + admin → 통과(전체 허용)."""
    current = _user(uuid4(), UserRole.ADMIN)
    # 다른 소유자 id여도 admin이므로 예외 없이 통과.
    ensure_owner_or_admin(uuid4(), current)
