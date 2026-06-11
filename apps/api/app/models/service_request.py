"""ServiceRequest ORM 모델 (Story 2.1).

status Enum은 DB에 소문자 값("open")으로 저장 — values_callable 필수.
customer_id / category_id는 서비스 계층에서만 설정, 요청 바디 미수용(IDOR 방지).
"""

import enum
import uuid as _uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ServiceRequestStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServiceRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_requests"

    customer_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False, index=True
    )
    category_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("categories.id"), nullable=False
    )
    region: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    desired_schedule: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    budget: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[ServiceRequestStatus] = mapped_column(
        sa.Enum(
            ServiceRequestStatus,
            name="service_request_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ServiceRequestStatus.OPEN,
    )
