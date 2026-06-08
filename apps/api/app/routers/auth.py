"""auth 라우터 — 회원가입(1.3) + 로그인/세션갱신(1.4) 엔드포인트.

규약: router는 HTTP·검증·Depends만. 비즈니스/트랜잭션은 service.
operationId 안정화를 위해 함수명(`signup`/`login`/`refresh`)을 유지(Orval 함수명 직결, AR9 — 소비는 1.7).
login/refresh는 미인증 공개(보호 가드 `get_current_user`는 1.5). `/logout`은 만들지 않는다(AC4 — 무상태).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    TokenResponse,
    UserRead,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup", response_model=UserRead, status_code=201)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)) -> User:
    """역할 선택 회원가입(customer/pro). 성공 시 안전한 사용자 표현(201) 반환."""
    return await AuthService(db).signup(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """이메일+비밀번호 로그인. 성공 시 access+refresh 토큰(200), 실패 시 401."""
    return await AuthService(db).login(data)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    data: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> RefreshResponse:
    """refresh 토큰으로 새 access 재발급(200). 무효/만료/비활성 토큰은 401."""
    return await AuthService(db).refresh(data)
