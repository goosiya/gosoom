"""ChatRoom Pydantic 스키마 (Story 4.2, 4.5).

ChatRoomRead: 견적 수락 성공 응답. ORM 직렬화(from_attributes=True via CamelModel).
ChatRoomListItem: 채팅방 목록 단건 — 상대방 displayName + 서비스 요청 임베딩.
PageChatRoomListItem: 채팅방 목록 cursor 페이지 응답.
"""

import uuid
from datetime import datetime
from typing import Optional

from app.schemas.base import CamelModel
from app.schemas.service_request import ServiceRequestSummary


class ChatRoomRead(CamelModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    customer_id: uuid.UUID
    pro_id: uuid.UUID
    quote_id: uuid.UUID
    created_at: datetime


class ChatRoomListItem(CamelModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    created_at: datetime
    counterpart_display_name: str
    service_request: Optional[ServiceRequestSummary] = None


class PageChatRoomListItem(CamelModel):
    items: list[ChatRoomListItem]
    next_cursor: Optional[uuid.UUID] = None


class ChatRoomAdminRead(CamelModel):
    """관리자 전용 채팅방 응답 — 고객·고수 표시명 포함 (Story 6.5)."""

    id: uuid.UUID
    service_request_id: uuid.UUID
    customer_id: uuid.UUID
    pro_id: uuid.UUID
    quote_id: uuid.UUID
    created_at: datetime
    customer_display_name: str
    pro_display_name: str
    service_request: Optional[ServiceRequestSummary] = None
