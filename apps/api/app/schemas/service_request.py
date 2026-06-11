"""ServiceRequest Pydantic 스키마 (Story 2.1).

ServiceRequestCreate: 클라이언트 입력. customer_id/status 미포함 — 서버에서만 설정(IDOR/변조 방지).
ServiceRequestRead: API 응답. ORM 직렬화(from_attributes=True via CamelModel).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import CamelModel


class ServiceRequestCreate(CamelModel):
    category_id: uuid.UUID
    region: str = Field(min_length=1)
    description: str = Field(min_length=1)
    desired_schedule: str | None = None
    budget: int | None = Field(None, ge=0)

    @field_validator("region", "description", mode="before")
    @classmethod
    def strip_and_require_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("공백만 입력할 수 없습니다.")
        return stripped

    @field_validator("desired_schedule", mode="before")
    @classmethod
    def strip_desired_schedule(cls, v: str | None) -> str | None:
        if v is None:
            return None
        stripped = v.strip()
        return stripped or None


class ServiceRequestRead(CamelModel):
    id: uuid.UUID
    customer_id: uuid.UUID
    category_id: uuid.UUID
    region: str
    description: str
    desired_schedule: str | None
    budget: int | None
    status: str
    created_at: datetime
    updated_at: datetime


class ServiceRequestStatusUpdate(CamelModel):
    action: Literal["cancel", "complete"]


class ServiceRequestAdminRead(ServiceRequestRead):
    """관리자 전용 서비스 요청 응답 — deleted_at 포함 (Story 6.4)."""

    deleted_at: datetime | None = None


class ServiceRequestSummary(CamelModel):
    """견적 목록에서 대상 요청 요약 정보 (Story 3.4)."""

    id: uuid.UUID
    category_id: uuid.UUID
    region: str
    description: str
    status: str
