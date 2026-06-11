"""Quote Pydantic 스키마 (Story 3.3/3.4/4.1).

QuoteCreate: 클라이언트 입력. service_request_id/pro_id/status 미포함 — 서버에서만 설정(IDOR/변조 방지).
QuoteRead: API 응답. ORM 직렬화(from_attributes=True via CamelModel).
QuoteListItem: 내 견적 목록 응답 아이템. service_request 필드 포함 (Story 3.4).
ProInfoSummary: 견적 비교 고수 기본 정보. 이메일 미포함(개인정보 최소화) (Story 4.1).
QuoteWithProInfo: 고객 측 견적 비교 응답 아이템. pro 필드 포함 (Story 4.1).
금액(price)은 정수 KRW(원 단위), 소수점 없음.
ServiceRequestSummary는 schemas/service_request.py에 정의됨 — re-export.
"""

import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.base import CamelModel
from app.schemas.service_request import ServiceRequestSummary  # noqa: F401 — re-export


class QuoteCreate(CamelModel):
    price: int = Field(ge=0, le=2_147_483_647)
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_message(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("공백만 입력할 수 없습니다.")
        return stripped


class QuoteRead(CamelModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    pro_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime


class QuoteListItem(CamelModel):
    """내 견적 목록 응답 아이템 (Story 3.4). service_request 필드 포함."""

    id: uuid.UUID
    service_request_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    service_request: ServiceRequestSummary | None = None


class ProInfoSummary(CamelModel):
    """견적 비교 고수 기본 정보 (Story 4.1). 이메일 미포함(개인정보 최소화)."""

    id: uuid.UUID
    display_name: str
    category_ids: list[uuid.UUID]


class QuoteWithProInfo(CamelModel):
    """고객 측 견적 비교 응답 아이템 (Story 4.1). pro 필드 포함."""

    id: uuid.UUID
    pro_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    pro: ProInfoSummary
