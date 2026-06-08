"""FastAPI 의존성 — 인증/인가 경계(Story 1.5, AR8/FR4).

- `get_current_user`: `Authorization: Bearer <access_jwt>`를 검증하고, 토큰의 user_id로
  현재 사용자를 **매 요청 DB 재조회**해 반환한다. 재조회는 부수 조회가 아니라 보안 의도 —
  발급 후 비활성화(`is_active=False`)·소프트삭제(`deleted_at`)된 계정을 **다음 요청에서 즉시**
  차단한다(FR19/20을 인증 경계 한 곳에서 중앙 시행, NFR4).
- `require_role`: `get_current_user` 위에 합성되는 역할 가드 팩토리(401이 403보다 선행).
- `CurrentUser`: 보호 라우트가 `current_user: CurrentUser`로 간결히 주입하는 타입 별칭.

권한·소유권의 최종 시행은 service 계층이 단일 관리한다(NFR4). 소유권 헬퍼는 core/authz.py.

⚠️ 이름 충돌: 도메인 예외 `InvalidTokenError`와 PyJWT 베이스 `jwt.InvalidTokenError`가 동명.
`import jwt`로 모듈 접근(`jwt.InvalidTokenError`)해 except에서 구분하고, raise는 도메인 예외를 쓴다
(services/auth.py와 동일 해법).
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.exceptions import (
    ForbiddenError,
    InvalidTokenError,
    NotAuthenticatedError,
)
from app.core.security import decode_token, oauth2_scheme
from app.models.user import User, UserRole
from app.repositories.users import UserRepository


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """access 토큰을 검증하고 현재 사용자를 반환(AC1/AC2).

    단계:
    ① 토큰 누락(헤더 부재) → 401 not_authenticated.
    ② 서명/만료/형식 디코드 실패 → 401 invalid_token.
    ③ type != "access"(refresh 토큰 오용) → 401 invalid_token.
    ④ payload 형식 오류(user_id 누락·비-UUID) → 401 invalid_token(500 누수 방지).
    ⑤ 재조회 실패·비활성 계정 → 401 invalid_token(비활성/삭제 즉시 차단).
    """
    # ① 헤더 누락 또는 값이 빈/공백: auto_error=False라 토큰 미전송 시 None이,
    # `Authorization: Bearer `(값 없음)처럼 스킴만 있고 값이 비면 빈 문자열("")이 들어온다.
    # 둘 다 "토큰을 보내지 않은 것"으로 보아 not_authenticated로 통일(invalid_token 아님) —
    # 1.7 인터셉터가 "로그인 필요"와 "세션 만료→refresh"를 code로 구분하므로 의미가 중요.
    if token is None or not token.strip():
        raise NotAuthenticatedError()

    # ② 서명·만료·exp부재 검증. PyJWT 베이스 예외를 도메인 예외로 변환.
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError() from exc

    # ③ 토큰 혼동 가드: refresh 토큰을 access로 오용 차단(1.4 refresh의 대칭).
    if payload.get("type") != "access":
        raise InvalidTokenError()

    # ④ payload 형식 가드: 서명은 유효하나 변조된 user_id를 500이 아니라 동일 401로 정규화.
    # UUID()가 입력 타입별로 다른 예외를 던진다 — 모두 포착해야 한다(1.4 패턴 계승):
    #   누락 → KeyError / 비-UUID 문자열 → ValueError / None → TypeError /
    #   int·list·dict·float·bool 등 그 외 비문자열 → AttributeError(no attribute 'replace').
    # AttributeError를 빠뜨리면 비문자열 user_id가 전역 핸들러로 새어 500이 된다.
    try:
        user_id = UUID(payload["user_id"])
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise InvalidTokenError() from exc

    # ⑤ 매 요청 재조회로 현재 상태 반영(AC2/FR19/20). get_by_id는 deleted_at IS NULL 내장.
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError()
    return user


def require_role(*allowed: UserRole) -> Callable[..., object]:
    """허용 역할 가드 의존성을 반환하는 팩토리(AC3).

    `get_current_user`에 의존하므로 인증(401)이 역할 검사(403)보다 항상 선행한다 —
    보호 라우트는 `Depends(require_role(...))` 하나만 붙여도 인증+인가가 동시 적용된다.

    호출 예:
        Depends(require_role(UserRole.ADMIN))
        Depends(require_role(UserRole.CUSTOMER, UserRole.PRO))
    인자는 `UserRole` enum으로 받는다(문자열 아님 — 타입 안전·오타 방지).
    """
    # fail-fast: 허용 역할이 비면 모든 사용자가 403이 되어 라우트가 영구 차단된다.
    # 런타임에 조용히 막히지 않도록 정의(모듈 import) 시점에 즉시 오류로 알린다.
    if not allowed:
        raise ValueError("require_role에는 최소 하나의 UserRole이 필요합니다.")

    async def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.user_role not in allowed:
            raise ForbiddenError()
        return current_user

    return _guard


# 보호 라우트 주입용 타입 별칭 — `current_user: CurrentUser`로 간결히 사용(다운스트림 ergonomics).
# 모든 역할이 접근 가능한(인증만 필요한) 라우트는 이 별칭을, 역할 제한 라우트는 require_role(...)를 쓴다.
CurrentUser = Annotated[User, Depends(get_current_user)]
