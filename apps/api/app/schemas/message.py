"""Message 스키마 (Story 4.4)."""

import uuid
from datetime import datetime

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
