"""auth 스키마 — 회원가입(Story 1.3) + 로그인/토큰(Story 1.4).

- `SignupRequest`: 역직렬화 경계. role은 customer/pro만 허용 → admin/기타 값은 Pydantic이 422 거부(AC3).
- `UserRead`: 안전한 사용자 표현. password_hash 절대 미포함(AC1).
- `LoginRequest`/`TokenResponse`/`RefreshRequest`/`RefreshResponse`(1.4): 로그인·세션 갱신 계약.
  로그인 입력은 JSON(camelCase) — form-data(`OAuth2PasswordRequestForm`)가 아니다(Orval 일관성).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.base import CamelModel


class SignupRequest(CamelModel):
    """회원가입 입력. 클라이언트는 `displayName`(camel) 전송 → populate_by_name으로 매핑."""

    email: EmailStr
    # max_length=128: 미인증 공개 엔드포인트에 초장문 password 전송 시 Argon2 해싱
    # 리소스 소진(DoS)을 막는 상한.
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=50)
    # customer/pro만 허용 — admin/기타 값은 Pydantic이 422로 거부(AC3).
    # 관리자는 자가 가입 대상이 아니다(시드 전용).
    role: Literal["customer", "pro"]

    @field_validator("email", mode="after")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        # 이메일을 소문자로 정규화 — 대소문자 차이(Alice@x.com vs alice@x.com)로 인한
        # 동일 사용자 중복 가입 방지. get_by_email도 동일 정규화 → 읽기/쓰기 경계 일관.
        return v.strip().lower()

    @field_validator("display_name", mode="after")
    @classmethod
    def _strip_display_name(cls, v: str) -> str:
        # min_length=1은 문자 수만 검사 → 공백만(" ", "\t")인 표시명이 통과한다.
        # strip 후 비어있지 않음을 강제(422).
        stripped = v.strip()
        if not stripped:
            raise ValueError("표시명은 공백일 수 없습니다.")
        return stripped


class UserRead(CamelModel):
    """안전한 사용자 표현(비밀번호 제외). ORM User 객체에서 직접 직렬화."""

    id: UUID
    email: str
    display_name: str
    user_role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(CamelModel):
    """로그인 입력(JSON, camelCase 경계). email + password로 자격 대조(AC1/2)."""

    email: EmailStr
    # 검증 자체에 길이 하한은 불요(가입이 아니라 기존 해시와의 대조)지만, max_length=128로
    # 공개 /login에 초장문 password를 보내 Argon2 자원을 소진시키는 DoS를 차단한다
    # (SignupRequest.password와 동일 상한 — 형식 단계 422라 계정 존재는 노출하지 않음).
    password: str = Field(max_length=128)

    @field_validator("email", mode="after")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        # 가입(SignupRequest)·조회(get_by_email)와 동일한 소문자 정규화 →
        # 대소문자 무관 로그인(Alice@x.com == alice@x.com) 일관성.
        return v.strip().lower()


class TokenResponse(CamelModel):
    """로그인 성공 응답(AC1). access + refresh 토큰 모두 발급.

    직렬화 경계는 `accessToken`/`refreshToken`/`tokenType`(camel).
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(CamelModel):
    """세션 갱신 입력(AC3). 보유한 refresh 토큰을 제출."""

    refresh_token: str


class RefreshResponse(CamelModel):
    """세션 갱신 응답(AC3). **새 access 토큰만** 재발급 — refresh 회전 없음(Post-MVP).

    `refresh_token`을 의도적으로 제외해 "회전 없음" 계약을 OpenAPI/Orval에 명시한다(소비는 1.7).
    """

    access_token: str
    token_type: str = "bearer"
