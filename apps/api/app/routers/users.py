"""users 라우터 — 현재 사용자 조회(Story 1.5).

규약: router는 HTTP·검증·Depends만. `get_current_user`를 소비하는 첫 실 보호 엔드포인트다.
operationId 안정화를 위해 함수명(`read_me`)을 유지(Orval 함수명 직결, AR9 — 소비는 1.7).
`/me`는 인증만 필요(모든 역할 자기 정보 접근) — 역할 제한 없음(require_role 미적용).
"""

from fastapi import APIRouter

from app.deps import CurrentUser
from app.models.user import User
from app.schemas.auth import UserRead

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(current_user: CurrentUser) -> User:
    """현재 인증된 사용자의 안전한 표현(UserRead — 비밀번호 제외) 반환(AC5).

    미인증/무효 토큰은 get_current_user가 401로 차단(AC1). 1.7 user-web가 로그인 사용자
    식별(displayName 등)에 소비한다.
    """
    return current_user
