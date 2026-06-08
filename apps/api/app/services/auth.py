"""AuthService — 회원가입/로그인/세션갱신 비즈니스 로직(첫 도메인 service).

규약(architecture#Structure Patterns):
- service가 트랜잭션(commit/rollback)을 소유한다. repository는 flush까지만.
- signup/login/refresh는 미인증 공개 행위(권한 검사 없음) — 소유권/역할 가드는 보호 엔드포인트(1.5+).
- login/refresh는 읽기 전용 → commit 호출 금지(쓰기 없음).

⚠️ 이름 충돌: 도메인 예외 `InvalidTokenError`와 PyJWT 베이스 `jwt.InvalidTokenError`가 동명.
`import jwt`로 모듈 접근(`jwt.InvalidTokenError`)해 except에서 구분하고, raise는 도메인 예외를 쓴다.
"""

from uuid import UUID

import jwt
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    DuplicateEmailError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    dummy_verify_password,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.users import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    SignupRequest,
    TokenResponse,
)


class AuthService:
    """인증/가입 도메인 서비스."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def signup(self, data: SignupRequest) -> User:
        """이메일+비밀번호+표시명+역할로 사용자 생성(AC1). 중복 이메일은 409(AC2).

        ① 선검사로 중복 차단 → ② Argon2 해싱 → ③ 생성/flush → ④ commit.
        ⑤ 동시 가입 race(선검사 통과 후 unique 위반)는 IntegrityError를 잡아 409로 변환.
        """
        existing = await self.users.get_by_email(data.email)
        if existing is not None:
            raise DuplicateEmailError()

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            user_role=UserRole(data.role),
        )
        try:
            await self.users.create(user)
            await self.session.commit()
        except IntegrityError as exc:
            # 동시 가입 race: 선검사 통과 후 다른 트랜잭션이 먼저 커밋 → unique 위반.
            await self.session.rollback()
            raise DuplicateEmailError() from exc

        # expire_on_commit=False라 commit 후에도 속성 접근 가능(response_model 직렬화 OK).
        return user

    async def login(self, data: LoginRequest) -> TokenResponse:
        """이메일+비밀번호 검증 후 access+refresh 토큰 발급(AC1).

        실패는 미존재·비번불일치·비활성 **모두 동일 일반 401**(anti-enumeration, NFR3).
        읽기 전용 — commit 없음.
        """
        user = await self.users.get_by_email(data.email)
        # 미존재 사용자: 더미 verify로 Argon2 비용을 동일하게 치러 타이밍 기반
        # 이메일 열거를 차단(NFR3 anti-enumeration) 후 동일 일반 401.
        if user is None:
            dummy_verify_password()
            raise InvalidCredentialsError()
        # 비밀번호 불일치 → 일반 401
        if not verify_password(data.password, user.password_hash):
            raise InvalidCredentialsError()
        # 비활성 계정 차단(FR19/20) — 동일 일반 401(상태 추론 방지)
        if not user.is_active:
            raise InvalidCredentialsError()
        return TokenResponse(
            access_token=create_access_token(user.id, user.user_role),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, data: RefreshRequest) -> RefreshResponse:
        """refresh 토큰을 검증·재조회해 새 access만 재발급(AC3, 회전 없음).

        재조회하는 이유는 부수 조회가 아니라 보안 의도(FR19/20): 발급 후 비활성화·삭제된
        계정이 새 access를 발급받지 못하게 한다. 디코드 실패·type 불일치·비활성/삭제는 401.
        """
        # 서명/만료 검증 — PyJWT 베이스 예외를 도메인 예외로 변환
        try:
            payload = decode_token(data.refresh_token)
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError() from exc
        # 토큰 혼동 가드: access 토큰을 refresh로 오용 차단
        if payload.get("type") != "refresh":
            raise InvalidTokenError()
        # payload 형식 가드: 서명은 유효하나 user_id 누락(KeyError)·비-UUID(ValueError)·
        # 비문자열(TypeError)인 변조/이상 토큰은 500이 아니라 동일 도메인 401로 변환.
        try:
            user_id = UUID(payload["user_id"])
        except (KeyError, ValueError, TypeError) as exc:
            raise InvalidTokenError() from exc
        # 현재 상태 재조회(FR19/20 증명) — 삭제(deleted_at)·비활성 계정은 거부
        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError()
        # 재조회한 현재 role을 반영한 새 access만 재발급
        return RefreshResponse(access_token=create_access_token(user.id, user.user_role))
