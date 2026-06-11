"""ChatRoom ORM 모델 (Story 4.2).

불변 레코드 — 생성 후 내용 변경 없음.
quote_id UNIQUE: 견적 1개당 채팅방 1개 DB 레벨 강제.
"""

import uuid as _uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class ChatRoom(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "chat_rooms"

    service_request_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("service_requests.id"), nullable=False, index=True
    )
    customer_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pro_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quote_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("quotes.id"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )
