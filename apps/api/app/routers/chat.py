"""Chat 라우터 — 채팅방 목록·메시지 전송·수신 (Story 4.4, 4.5).

GET  /api/v1/chat-rooms                          → 200 PageChatRoomListItem
POST /api/v1/chat-rooms/{chat_room_id}/messages  → 201 MessageRead
GET  /api/v1/chat-rooms/{chat_room_id}/messages  → 200 MessageListResponse
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import CurrentUser, get_db
from app.schemas.chat_room import PageChatRoomListItem
from app.schemas.message import MessageCreate, MessageListResponse, MessageRead
from app.services.chat import ChatService

router = APIRouter(prefix="/api/v1/chat-rooms", tags=["chat-rooms"])


@router.get("", response_model=PageChatRoomListItem, status_code=200)
async def list_chat_rooms(
    current_user: CurrentUser,
    mine: bool = Query(default=True),
    cursor: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
) -> PageChatRoomListItem:
    svc = ChatService(session)
    return await svc.list_my_chat_rooms(current_user, cursor)


@router.post("/{chat_room_id}/messages", response_model=MessageRead, status_code=201)
async def send_message(
    chat_room_id: uuid.UUID,
    body: MessageCreate,
    current_user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> MessageRead:
    svc = ChatService(session)
    return await svc.send_message(chat_room_id, body.content, current_user)


@router.get("/{chat_room_id}/messages", response_model=MessageListResponse, status_code=200)
async def list_messages(
    chat_room_id: uuid.UUID,
    current_user: CurrentUser,
    after: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    svc = ChatService(session)
    messages = await svc.list_messages(chat_room_id, after, current_user)
    return MessageListResponse(items=messages)
