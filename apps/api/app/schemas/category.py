"""category 스키마 — 안전한 카테고리 표현(Story 1.6).

`CategoryRead`: ORM `Category`를 직접 직렬화(from_attributes). `deleted_at`은 내부 마커이므로
미포함(안전 표현). JSON 경계는 camelCase(`isActive`, `createdAt`).
"""

from datetime import datetime
from uuid import UUID

from pydantic import field_validator

from app.schemas.base import CamelModel


class CategoryRead(CamelModel):
    """안전한 카테고리 표현. deleted_at 미포함(내부 마커)."""

    id: UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CategoryCreate(CamelModel):
    """카테고리 생성 요청 (Story 6.6, AC1)."""

    name: str

    @field_validator("name", mode="after")
    @classmethod
    def _name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("카테고리명은 공백일 수 없습니다.")
        return v


class CategoryUpdate(CamelModel):
    """카테고리 수정 요청 (Story 6.6, AC2). None 필드는 변경 안 함."""

    name: str | None = None

    @field_validator("name", mode="after")
    @classmethod
    def _name_not_empty(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("카테고리명은 공백일 수 없습니다.")
        return v


class CategoryAdminRead(CamelModel):
    """관리자 전용 카테고리 응답 — 비활성 포함 + 사용 여부 (Story 6.6, AC5)."""

    id: UUID
    name: str
    is_active: bool
    in_use: bool
    created_at: datetime
    updated_at: datetime
