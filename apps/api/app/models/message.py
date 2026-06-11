"""Message ORM 모델 (Story 4.4).

불변 레코드 — 전송 후 수정 불가. updated_at 미사용.
"""

import uuid as _uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class Message(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "messages"

    chat_room_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
