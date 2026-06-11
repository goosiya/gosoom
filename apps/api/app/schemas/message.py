"""Message 스키마 (Story 4.4)."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base import CamelModel


class MessageCreate(CamelModel):
    content: str = Field(min_length=1, max_length=4096)


class MessageRead(CamelModel):
    id: uuid.UUID
    chat_room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime


class MessageListResponse(CamelModel):
    items: list[MessageRead]


class MessagePageResponse(CamelModel):
    """관리자 전용 메시지 페이지 응답 — before cursor 포함 (Story 6.5 patch)."""

    items: list[MessageRead]
    next_cursor: Optional[uuid.UUID] = None
