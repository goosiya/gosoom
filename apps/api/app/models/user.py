"""User 모델 + UserRole enum — 첫 도메인 테이블(Story 1.3).

- `users` 테이블: 가입(customer/pro)과 시드 관리자(admin)를 담는 단일 사용자 테이블.
- `UserRole`: DB enum은 3값(customer/pro/admin). admin은 시드 전용 — signup 입력엔 불허(스키마에서 차단).
- 공통 기반은 base mixin 상속(UUIDv7 PK, created/updated/deleted_at).
"""

import enum

from sqlalchemy import Boolean, Enum, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    """사용자 역할. DB enum 타입 `user_role`의 라벨로 사용된다.

    str 혼합 enum이므로 `UserRole.CUSTOMER == "customer"`가 성립(Pydantic 직렬화 시 값 노출).
    admin은 시드 관리자 전용 — 회원가입 요청 스키마는 customer/pro만 허용(AC3).
    """

    CUSTOMER = "customer"
    PRO = "pro"
    ADMIN = "admin"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """사용자(고객/고수/시드 관리자) 단일 테이블."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    # values_callable로 DB enum 라벨을 멤버 '값'(소문자)으로 강제.
    # 미지정 시 SQLAlchemy 기본은 멤버 '이름'(대문자)을 저장 — API는 소문자라 불일치.
    # 첫 도메인 슬라이스이므로 enum 저장 규약을 여기서 소문자로 확정한다.
    user_role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    # 시드 관리자 잠금 방지 표식(AC4/FR21) — 비활성화 대상에서 제외.
    is_seed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
