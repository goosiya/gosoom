"""Quote ORM 모델 (Story 3.3).

status Enum은 DB에 소문자 값("pending")으로 저장 — values_callable 필수.
service_request_id / pro_id는 서비스 계층에서만 설정, 요청 바디 미수용(IDOR 방지).
UNIQUE(service_request_id, pro_id): 요청당 PRO 1개 견적 DB 레벨 강제.
"""

import enum
import uuid as _uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class QuoteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CLOSED = "closed"


class Quote(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "quotes"
    __table_args__ = (
        sa.Index(
            "uq_quotes_request_pro",
            "service_request_id",
            "pro_id",
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL"),
        ),
    )

    service_request_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("service_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pro_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    price: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[QuoteStatus] = mapped_column(
        sa.Enum(
            QuoteStatus,
            name="quote_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=QuoteStatus.PENDING,
    )
