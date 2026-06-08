"""소유권 검사 단일 시행 지점(Story 1.5, NFR4/AR8).

`ensure_owner_or_admin`는 권한 규칙을 한 곳에 캡슐화하는 순수 함수다(DB·HTTP 무관).
Epic 2(요청)·3(견적)·4(채팅) service가 자원 소유자 id와 current_user를 넘겨 호출한다 —
권한을 라우터/클라이언트에 분산하지 않는다(anti-pattern: architecture.md line 342).

⚠️ 과설계 금지(architecture.md line 288): 클래스·정책 레지스트리 없이 함수 하나로 시작.
자원별 가시성 등 더 복잡한 정책이 필요해지면 그때 확장한다 — 이 스토리는 최소 프리미티브만.
"""

from uuid import UUID

from app.core.exceptions import ForbiddenError
from app.models.user import User, UserRole


def ensure_owner_or_admin(resource_owner_id: UUID, current_user: User) -> None:
    """현재 사용자가 자원 소유자이거나 관리자인지 검사. 아니면 ForbiddenError(403, AC4).

    - 관리자(`UserRole.ADMIN`): 전체 자원 허용 → 무반환(통과).
    - 그 외(customer/pro): 본인 소유 자원(`current_user.id == resource_owner_id`)만 허용.
    - 불일치: 403 ForbiddenError.

    통과 시 무반환 — service 메서드 내부에서 권한 게이트로 호출한다.
    """
    if current_user.user_role == UserRole.ADMIN:
        return
    if current_user.id != resource_owner_id:
        raise ForbiddenError()
