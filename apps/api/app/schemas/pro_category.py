"""ProCategory Pydantic 스키마 (Story 3.1).

ProCategoriesUpdate: 교체 대상 category_id 배열.
ProCategoriesRead: 현재 설정된 category_id 목록 응답.
"""

from uuid import UUID

from pydantic import Field

from app.schemas.base import CamelModel


class ProCategoriesUpdate(CamelModel):
    category_ids: list[UUID] = Field(max_length=100)


class ProCategoriesRead(CamelModel):
    category_ids: list[UUID]
