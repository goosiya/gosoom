"""category 스키마 — 안전한 카테고리 표현(Story 1.6).

`CategoryRead`: ORM `Category`를 직접 직렬화(from_attributes). `deleted_at`은 내부 마커이므로
미포함(안전 표현). JSON 경계는 camelCase(`isActive`, `createdAt`).
"""

from datetime import datetime
from uuid import UUID

from app.schemas.base import CamelModel


class CategoryRead(CamelModel):
    """안전한 카테고리 표현. deleted_at 미포함(내부 마커)."""

    id: UUID
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
