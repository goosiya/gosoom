---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 4.4: 채팅 메시지 전송·수신 (폴링)

- **Status:** done
- **Epic:** 4 — 매칭 & 채팅 (거래 루프 완결) (FR8, FR13-18)
- **Story ID / Key:** 4-4 / 4-4-chat-messaging-polling
- **작성일:** 2026-06-11

---

## 사용자 스토리

As a 로그인한 고객(CUSTOMER) 또는 고수(PRO),
채팅방에서 텍스트 메시지를 보내고 상대의 새 메시지를 받아보고 싶다.
So that 거래 세부사항(방문 시간, 작업 범위 등)을 대화로 조율할 수 있다.

---

## 인수 기준 (BDD)

**AC1** — messages 테이블 마이그레이션 (AR6/G3)

- **Given** `chat_rooms` 테이블이 이미 존재할 때
- **When** 새 Alembic 마이그레이션이 적용되면
- **Then** `messages` 테이블이 생성된다:
  - `id` (UUIDv7 기반 UUID, PK, 시간정렬)
  - `chat_room_id` (UUID FK → `chat_rooms.id`, ON DELETE CASCADE)
  - `sender_id` (UUID FK → `users.id`, ON DELETE CASCADE)
  - `content` (TEXT, NOT NULL)
  - `created_at` (TIMESTAMPTZ, server_default=NOW())
  - 인덱스: `chat_room_id`, 복합 `(chat_room_id, id)` (폴링 쿼리 성능)

**AC2** — 메시지 전송 (FR16)

- **Given** 채팅방 참여자(고객 또는 고수)가 로그인한 상태에서
- **When** `POST /api/v1/chat-rooms/{id}/messages` 를 `{"content": "내일 오전 10시 가능한가요?"}` 와 함께 호출하면
- **Then** 메시지가 DB에 저장되고
- **And** `sender_id`는 현재 요청 사용자의 ID로 설정되며
- **And** 저장된 `MessageRead` 객체가 201로 반환된다

**AC3** — 메시지 수신: 증분 폴링 (FR17, CM1/AR13)

- **Given** 채팅방에 메시지들이 존재할 때
- **When** `GET /api/v1/chat-rooms/{id}/messages` (after 파라미터 없음)를 호출하면
- **Then** 최근 50개 메시지가 created_at ASC 순서로 반환된다
- **When** `GET /api/v1/chat-rooms/{id}/messages?after={lastMessageId}` 를 호출하면
- **Then** `lastMessageId` 이후에 생성된 신규 메시지만 증분 반환된다 (전체 재수신 금지, CM1)
- **And** 신규 메시지가 없으면 `{"items": []}` 반환

**AC4** — 권한 검사 (FR4, FR19/20)

- **Given** 비인증 요청 → 401 `not_authenticated`
- **Given** 채팅방 참여자가 아닌 사용자(타 고객·타 고수·ADMIN) → 403 `forbidden`
- **Given** 존재하지 않는 채팅방 ID → 404 `chat_room_not_found`
- **Given** `is_active=False` 계정 → `get_current_user` 에서 401 차단 (비활성 계정)
- **And** content가 빈 문자열 → 422 Unprocessable Entity

**AC5** — user-web 채팅 화면 (FR17, AR13/AR15)

- **Given** Story 4.2에서 `router.push('/chat/${chatRoom.id}')` 가 이미 구현된 상태에서
- **When** 수락 후 채팅방으로 이동하면
- **Then** `/chat/[id]` 페이지가 채팅 UI를 표시하고
- **And** TanStack Query `refetchInterval: 2000` 으로 2초마다 `GET .../messages?after=<lastId>` 를 폴링하여 신규 메시지를 자동 갱신한다
- **And** 내 메시지는 오른쪽, 상대 메시지는 왼쪽에 표시된다 (sender_id 비교)
- **And** 메시지 전송 후 즉시 화면에 반영된다 (낙관적 append)
- **And** 처리 중 전송 버튼이 비활성화된다

---

## 태스크 및 서브태스크

- [x] **Task 1:** Alembic 마이그레이션 — `add_messages_table`
  - [x] `apps/api/alembic/versions/<hash>_add_messages_table.py` 신규 생성
  - [x] `down_revision = 'a1b2c3d4e5f6'` (chat_rooms 마이그레이션 의존)
  - [x] `messages` 테이블 생성 (id, chat_room_id, sender_id, content, created_at)
  - [x] 인덱스: `ix_messages_chat_room_id` + `ix_messages_chat_room_id_id` (복합)
  - [x] `alembic upgrade head` 로 적용 확인

- [x] **Task 2:** `ChatRoomNotFoundError` 예외 추가
  - [x] `apps/api/app/core/exceptions.py` 수정
  - [x] 404 `chat_room_not_found` 예외 클래스 추가 (기존 예외 패턴 준수)

- [x] **Task 3:** `Message` ORM 모델 + `models/__init__.py` 업데이트
  - [x] `apps/api/app/models/message.py` 신규 생성
  - [x] `Message(Base, UUIDPrimaryKeyMixin)` 정의 (chat_room_id, sender_id, content, created_at)
  - [x] `apps/api/app/models/__init__.py` 에 `Message` import/export 추가

- [x] **Task 4:** 메시지 스키마 정의
  - [x] `apps/api/app/schemas/message.py` 신규 생성
  - [x] `MessageCreate(CamelModel)`: `content: str` (Field min_length=1, max_length=4096)
  - [x] `MessageRead(CamelModel)`: id, chat_room_id, sender_id, content, created_at
  - [x] `MessageListResponse(CamelModel)`: `items: list[MessageRead]`

- [x] **Task 5:** `ChatRoomRepository.get_by_id()` 추가
  - [x] `apps/api/app/repositories/chat_rooms.py` 수정
  - [x] `async get_by_id(chat_room_id: UUID) -> ChatRoom | None` 메서드 추가

- [x] **Task 6:** `MessageRepository` 구현
  - [x] `apps/api/app/repositories/messages.py` 신규 생성
  - [x] `async create(obj: Message) -> Message` — flush/refresh만, commit은 service
  - [x] `async list_after(chat_room_id, after_id, limit) -> list[Message]`
    - `after_id=None`: id DESC LIMIT 50 후 ASC 역순 반환 (created_at 동일 ms 충돌 방지)
    - `after_id` 있음: `id > after_id` AND `chat_room_id = ?` ORDER BY id ASC

- [x] **Task 7:** `ChatService` 구현
  - [x] `apps/api/app/services/chat.py` 신규 생성
  - [x] `ChatService(session)`:
    - `async send_message(chat_room_id, content, current_user) -> Message`
    - `async list_messages(chat_room_id, after_id, current_user) -> list[Message]`
  - [x] 두 메서드 공통: 채팅방 조회 (404) → 참여자 검사 (403) → 로직 실행

- [x] **Task 8:** Chat 라우터 구현 + `main.py` 등록
  - [x] `apps/api/app/routers/chat.py` 신규 생성
  - [x] `POST /api/v1/chat-rooms/{id}/messages` → `send_message` (201, MessageRead)
  - [x] `GET /api/v1/chat-rooms/{id}/messages` → `list_messages` (200, MessageListResponse)
  - [x] `apps/api/app/main.py` 에 `chat_router` 등록

- [x] **Task 9:** pytest 작성 (`apps/api/tests/test_chat_messages.py`)
  - [x] AC2 전송 성공 CUSTOMER: 201, 반환 MessageRead의 senderId = customer.id
  - [x] AC2 전송 성공 PRO: 201, 반환 MessageRead의 senderId = pro.id
  - [x] AC3 목록 초기 조회 (after 없음): 200, items 반환
  - [x] AC3 목록 증분 조회 (after=lastId): 신규 메시지만 반환, 이전 메시지 제외
  - [x] AC3 after 이후 신규 없음: 200, items=[]
  - [x] AC4 비인증 → 401 `not_authenticated`
  - [x] AC4 비참여자(타 고객) 전송 → 403 `forbidden`
  - [x] AC4 비참여자(타 고수) 전송 → 403 `forbidden`
  - [x] AC4 비참여자(ADMIN) → 403 `forbidden`
  - [x] AC4 존재하지 않는 채팅방 → 404 `chat_room_not_found`
  - [x] AC4 빈 content 전송 → 422

- [x] **Task 10:** Orval 재생성 + api-client 업데이트
  - [x] API 서버 기동 후 `openapi.json` 덤프 → `pnpm orval`
  - [x] `useSendMessage`, `useListMessages` 훅 생성 확인 (`packages/api-client/src/generated/chat-rooms/chat-rooms.ts`)
  - [x] `MessageRead`, `MessageCreate`, `MessageListResponse` 타입 생성 확인
  - [x] `packages/api-client/src/index.ts` 에 `export * from './generated/chat-rooms/chat-rooms'` 수동 추가
  - [x] `packages/api-client/src/generated/model/index.ts` 에 새 타입 export 확인

- [x] **Task 11:** user-web 채팅 화면 구현
  - [x] `apps/user-web/src/app/chat/[id]/page.tsx` 신규 생성
  - [x] `useReadMe()` 로 현재 사용자 ID 파악
  - [x] `useReducer + useRef` 패턴으로 증분 폴링 구현 (`refetchInterval: 2000`, set-state-in-effect 린트 규칙 준수)
  - [x] 메시지 전송 폼 (input + 전송 버튼)
  - [x] 내 메시지 우측, 상대 메시지 좌측 정렬
  - [x] 새 메시지 도착 시 스크롤 하단 유지
  - [x] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과

### Review Findings

- [x] [Review][Patch] AC3 정렬 기준 수정 — spec `created_at ASC` 준수를 위해 `order_by(Message.id.desc())`를 `order_by(Message.created_at.desc())`로 변경 (KTH 2026-06-11 결정: spec 문자 준수) [apps/api/app/repositories/messages.py:43]
- [x] [Review][Patch] 증분 폴링 경로에 limit 미적용 — else branch에 `.limit(limit)` 없어 장기 오프라인 복귀 시 무제한 행 반환 가능 [apps/api/app/repositories/messages.py:49-58]
- [x] [Review][Patch] messagesReducer 중복 메시지 dedup 없음 — 낙관적 append와 2초 폴링 경쟁 조건으로 동일 메시지 두 번 렌더링 가능. id 기반 필터 추가 필요 [apps/user-web/src/app/chat/[id]/page.tsx:14-16]
- [x] [Review][Patch] ORM Message.created_at Python-side default=func.now() 오용 — func.now()는 SQLAlchemy SQL 표현식으로 Python-side default 역할을 하지 않음. server_default만 유지 [apps/api/app/models/message.py:26-31]

---

## 개발자 노트

### 핵심 설계 결정

#### 1. 라우터/서비스 파일명 — `chat.py` (아키텍처 명세 준수)

아키텍처 문서 라인 467:
```
채팅 FR15-18 | routers/chat.py, services/chat.py
```
- 라우터: `apps/api/app/routers/chat.py`
- 서비스: `apps/api/app/services/chat.py`
- (기존 `repositories/chat_rooms.py`는 그대로 유지)

`main.py` 등록:
```python
from app.routers.chat import router as chat_router
# ...
app.include_router(chat_router)   # /api/v1/chat-rooms/*
```

**operationId 예측:**
```
함수명: send_message
FastAPI operationId: send_message_api_v1_chat_rooms__id__messages_post
orval.config.ts 정규식 제거 후: send_message
Orval camelCase 변환: useSendMessage
생성 파일: packages/api-client/src/generated/chat-rooms/chat-rooms.ts

함수명: list_messages
FastAPI operationId: list_messages_api_v1_chat_rooms__id__messages_get
Orval camelCase: useListMessages
```

#### 2. 라우터 — 역할 제한 없음, 참여자 검사만

CUSTOMER·PRO 모두 채팅 가능 → `require_role` 미사용. 참여자 검사는 service 계층에서 처리.

```python
# routers/chat.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.deps import CurrentUser, get_db
from app.schemas.message import MessageCreate, MessageListResponse, MessageRead
from app.services.chat import ChatService

router = APIRouter(prefix="/api/v1/chat-rooms", tags=["chat-rooms"])


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
```

**응답 코드:** 전송은 201 (신규 리소스 생성), 목록 조회는 200.

#### 3. `Message` ORM 모델 구조

```python
# models/message.py
from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class Message(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "messages"

    chat_room_id: Mapped[UUID] = mapped_column(
        ForeignKey("chat_rooms.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), timezone=True
    )
```

**CASCADE 정책:** `chat_room_id`와 `sender_id` 모두 `ON DELETE CASCADE` — 프로젝트 표준 (project-cascade-policy 메모리).

**`updated_at` 없음:** 메시지는 전송 후 수정 불가 (불변 레코드). `TimestampMixin` 미사용.

#### 4. `ChatService` 구현 — 참여자 검사 패턴

```python
# services/chat.py
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ChatRoomNotFoundError, ForbiddenError
from app.models.message import Message
from app.models.user import User
from app.repositories.chat_rooms import ChatRoomRepository
from app.repositories.messages import MessageRepository


class ChatService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chat_room_repo = ChatRoomRepository(session)
        self.message_repo = MessageRepository(session)

    async def _get_room_and_check_participant(self, chat_room_id: UUID, current_user: User):
        """채팅방 조회 + 참여자 검사 — 두 엔드포인트 공통 가드."""
        chat_room = await self.chat_room_repo.get_by_id(chat_room_id)
        if chat_room is None:
            raise ChatRoomNotFoundError()
        if current_user.id not in (chat_room.customer_id, chat_room.pro_id):
            raise ForbiddenError()
        return chat_room

    async def send_message(self, chat_room_id: UUID, content: str, current_user: User) -> Message:
        await self._get_room_and_check_participant(chat_room_id, current_user)
        msg = Message(
            chat_room_id=chat_room_id,
            sender_id=current_user.id,
            content=content,
        )
        return await self.message_repo.create(msg)

    async def list_messages(
        self, chat_room_id: UUID, after_id: UUID | None, current_user: User
    ) -> list[Message]:
        await self._get_room_and_check_participant(chat_room_id, current_user)
        return await self.message_repo.list_after(chat_room_id, after_id)
```

**`send_message` 는 commit 불필요?**: `MessageRepository.create()` 는 `flush/refresh` 만 하므로 service 에서 `commit()` 필요. Story 4.2 의 `ChatRoomRepository.create()` 는 accept 트랜잭션 안에 있었기 때문에 service 가 commit 을 관리했다. 여기서도 동일하게 `service.send_message()` 내에서 `await self.session.commit()` 후 `refresh` 필요:

```python
async def send_message(self, chat_room_id: UUID, content: str, current_user: User) -> Message:
    await self._get_room_and_check_participant(chat_room_id, current_user)
    msg = Message(chat_room_id=chat_room_id, sender_id=current_user.id, content=content)
    await self.message_repo.create(msg)  # flush+refresh
    await self.session.commit()
    await self.session.refresh(msg)
    return msg
```

#### 5. `MessageRepository` — 폴링 쿼리

```python
# repositories/messages.py
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: Message) -> Message:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def list_after(
        self,
        chat_room_id: UUID,
        after_id: UUID | None,
        limit: int = 50,
    ) -> list[Message]:
        if after_id is None:
            # 초기 로드: 최신 50개를 DESC로 가져와서 ASC로 역순 반환
            stmt = (
                select(Message)
                .where(Message.chat_room_id == chat_room_id)
                .order_by(Message.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            msgs = list(result.scalars().all())
            return list(reversed(msgs))
        else:
            # 증분 폴링: after_id 이후 메시지만
            stmt = (
                select(Message)
                .where(
                    Message.chat_room_id == chat_room_id,
                    Message.id > after_id,  # UUIDv7은 바이트 비교로 시간 순 보장
                )
                .order_by(Message.id.asc())
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
```

**UUIDv7 비교 안전성:** PostgreSQL 은 UUID 를 128비트 정수로 비교한다. UUIDv7 의 상위 48비트가 밀리초 타임스탬프이므로 `id > after_id` 는 시간 순 비교와 동일하다. SQLAlchemy UUID 컬럼의 `>` 연산자는 PostgreSQL UUID 타입의 비교 연산자로 변환된다.

#### 6. `ChatRoomRepository.get_by_id()` 추가

```python
# repositories/chat_rooms.py — 기존 create() 아래에 추가
async def get_by_id(self, chat_room_id: UUID) -> ChatRoom | None:
    result = await self.session.get(ChatRoom, chat_room_id)
    return result
```

`session.get()` 은 PK 조회 단축 메서드 — `select().where()` 보다 간결하다. 이미 다른 레포지터리(예: quote.py 의 `get_by_id`)에서 사용하는 패턴인지 확인 후 동일하게 적용.

#### 7. Alembic 마이그레이션

```python
# alembic/versions/<hash>_add_messages_table.py
"""add messages table

Revision ID: <generated_hash>
Revises: a1b2c3d4e5f6
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "<generated_hash>"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chat_room_id"], ["chat_rooms.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_chat_room_id", "messages", ["chat_room_id"])
    op.create_index(
        "ix_messages_chat_room_id_id",
        "messages",
        ["chat_room_id", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_chat_room_id_id", table_name="messages")
    op.drop_index("ix_messages_chat_room_id", table_name="messages")
    op.drop_table("messages")
```

**실제 hash 는 `alembic revision --autogenerate -m "add messages table"` 실행 시 자동 생성.** 위 스켈레톤을 바탕으로 자동 생성된 파일을 수정하거나, `alembic revision` 으로 빈 파일 생성 후 위 내용을 채운다. 핵심은 `down_revision = 'a1b2c3d4e5f6'` 이다.

#### 8. 프론트엔드 — 증분 폴링 패턴 (CM1 준수)

**핵심 원칙:** `lastId` 를 TanStack Query 의 쿼리 키에 포함시키면 안 된다. 쿼리 키가 바뀌면 새 쿼리가 생성되어 `refetchInterval` 이 리셋된다.

**올바른 패턴 (useRef 기반):**
```tsx
"use client";
import { useRef, useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listMessages,          // Orval 생성 함수
  sendMessage,           // Orval 생성 함수
  useReadMe,
  type MessageRead,
} from "@gosoom/api-client";

export default function ChatRoomPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: me } = useReadMe();

  const lastIdRef = useRef<string | undefined>(undefined);
  const [allMessages, setAllMessages] = useState<MessageRead[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [content, setContent] = useState("");

  // 증분 폴링 쿼리 — 쿼리 키는 chatRoomId 만 (lastId 포함 금지)
  const { data: pollData } = useQuery({
    queryKey: ["chat-messages", id],
    queryFn: () => listMessages(id, { after: lastIdRef.current }),
    refetchInterval: 2000,
    enabled: !!id,
  });

  // 새 메시지 도착 시 누적
  useEffect(() => {
    if (pollData?.items?.length) {
      setAllMessages(prev => [...prev, ...pollData.items]);
      lastIdRef.current = pollData.items[pollData.items.length - 1].id;
    }
  }, [pollData]);

  // 새 메시지 시 스크롤 하단 유지
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allMessages]);

  const sendMutation = useMutation({
    mutationFn: (c: string) => sendMessage(id, { content: c }),
    onSuccess: (newMsg) => {
      // 전송 즉시 낙관적 반영
      setAllMessages(prev => [...prev, newMsg]);
      lastIdRef.current = newMsg.id;
      setContent("");
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    sendMutation.mutate(content.trim());
  };

  return (
    <div className="flex flex-col h-screen">
      {/* 메시지 목록 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {allMessages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.senderId === me?.id ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-xs px-3 py-2 rounded-lg text-sm ${
                msg.senderId === me?.id
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-900"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 전송 폼 */}
      <form onSubmit={handleSend} className="p-4 border-t flex gap-2">
        <input
          type="text"
          value={content}
          onChange={e => setContent(e.target.value)}
          placeholder="메시지를 입력하세요"
          className="flex-1 border rounded-md px-3 py-2 text-sm"
          disabled={sendMutation.isPending}
        />
        <button
          type="submit"
          disabled={sendMutation.isPending || !content.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm disabled:opacity-50"
        >
          {sendMutation.isPending ? "전송 중…" : "전송"}
        </button>
      </form>

      {sendMutation.isError && (
        <p className="text-red-600 text-xs px-4 pb-2" role="alert">
          메시지 전송에 실패했습니다.
        </p>
      )}
    </div>
  );
}
```

**`useReadMe()` 활용:** 현재 사용자 ID 와 메시지의 `senderId` 를 비교하여 좌/우 정렬 결정.

**인증 미처리 시 동작:** `useReadMe()` 가 실패하면 `me` 는 undefined. `router.push('/login')` 리다이렉트 추가 권장.

#### 9. api-client index.ts 수동 업데이트

Orval 은 `index.ts` 를 자동 갱신하지 않는다. Orval 실행 후 수동으로 추가:

```typescript
// packages/api-client/src/index.ts — 기존 줄 아래에 추가
export * from './generated/chat-rooms/chat-rooms';
```

**Orval 생성 파일 위치 예측:**
```
packages/api-client/src/generated/
  chat-rooms/
    chat-rooms.ts        # useSendMessage, useListMessages 훅
  model/
    messageCreate.ts
    messageRead.ts
    messageListResponse.ts
    index.ts             # 새 타입 자동 추가됨 (Orval 재생성 시)
```

---

### 알려진 함정

#### 1. `chat_room_id` 가 메시지 목록 쿼리 키에 있어야 함 ✅

여러 채팅방을 열어두는 경우(향후), 각 방의 폴링이 독립적이어야 한다. 쿼리 키에 `id` (chatRoomId) 를 반드시 포함해야 한다: `["chat-messages", id]`.

#### 2. `UUIDv7` 비교 — `id > after_id` ✅

PostgreSQL UUID 타입은 바이트 비교를 수행한다. UUIDv7 상위 6바이트 = 타임스탬프이므로 시간 순과 동일. 단, **동일 밀리초 내 복수 메시지**가 있을 경우 하위 랜덤 비트 때문에 순서가 불안정할 수 있다. 이 경우 `created_at` 을 추가 정렬 키로 사용하거나, 동일 ms 내 메시지가 누락될 수 있음을 허용하는 것이 MVP 허용 범위다.

#### 3. 프론트엔드 메모리 누수 — `refetchInterval` 과 언마운트 ⚠️

TanStack Query 는 컴포넌트 언마운트 시 `refetchInterval` 을 자동으로 정리한다. 별도 cleanup 불필요.

#### 4. 빈 폴링 응답 (`items: []`) 처리 ✅

`after` 이후 신규 메시지가 없으면 `{ items: [] }` 반환. `pollData?.items?.length` 체크로 빈 배열을 무시하고 `lastIdRef` 를 갱신하지 않는다. 정상 동작.

#### 5. `content` 최대 길이 — Pydantic 검증 ✅

`MessageCreate.content` 에 `Field(min_length=1, max_length=4096)` 를 적용한다. DB는 TEXT (무제한)이지만 API 계층에서 제한. 빈 문자열 전송 시 422 반환.

#### 6. `send_message` 후 `commit` + `refresh` 필수 ⚠️

`MessageRepository.create()` 는 `flush()+refresh()` 만 수행한다 (기존 레포지터리 패턴). 따라서 `ChatService.send_message()` 에서 반드시 `await self.session.commit()` 후 `await self.session.refresh(msg)` 를 추가해야 `created_at` 서버 기본값이 응답에 포함된다.

#### 7. `chat` 라우터 prefix 확인 ⚠️

`router = APIRouter(prefix="/api/v1/chat-rooms", tags=["chat-rooms"])` 로 설정한다. `/api/v1` prefix 는 라우터 자체에 포함시킨다 (`main.py` 에서 별도 prefix 없이 등록).

기존 라우터 등록 패턴 확인:
```python
# main.py 기존 패턴
app.include_router(quotes_router)  # prefix는 quotes.py 내에 정의됨
```
`chat_router` 도 동일하게 prefix 없이 `app.include_router(chat_router)`.

#### 8. `models/__init__.py` 에 `Message` 추가 ✅

```python
from app.models.message import Message
```
이를 누락하면 Alembic autogenerate 시 Message 모델이 인식되지 않는다.

#### 9. `/chat/[id]` 라우트 그룹 고려 ⚠️

현재 `(customer)` 와 `(pro)` 는 각각의 레이아웃 그룹. 채팅방은 양쪽 모두 접근하므로 루트 `app/` 아래에 `chat/[id]/page.tsx` 를 생성한다. 루트 레이아웃 파일(`app/layout.tsx`)에 인증 가드가 없다면, 페이지 내부에서 `useReadMe()` 실패 시 `router.push('/login')` 리다이렉트 추가 권장.

---

### 구현 세부 사항

#### `schemas/message.py` 전체

```python
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
```

#### `test_chat_messages.py` 헬퍼 재사용

`tests/helpers.py` 의 헬퍼를 그대로 재사용:
- `_make_customer`, `_make_pro`, `_make_admin`
- `_make_category`, `_make_service_request`, `_make_quote`
- `_auth(user)`

**테스트용 ChatRoom 생성 헬퍼 필요:**
```python
from app.models.chat_room import ChatRoom

async def _make_chat_room(db, customer, pro, sr, quote) -> ChatRoom:
    cr = ChatRoom(
        service_request_id=sr.id,
        customer_id=customer.id,
        pro_id=pro.id,
        quote_id=quote.id,
    )
    db.add(cr)
    await db.flush()
    await db.refresh(cr)
    return cr
```

**증분 폴링 검증 핵심:**
```python
# 메시지 1 전송
resp1 = await client_db.post(f"/api/v1/chat-rooms/{cr.id}/messages",
    json={"content": "첫 메시지"}, headers=_auth(customer))
msg1_id = resp1.json()["id"]

# 메시지 2 전송
await client_db.post(...)  # "두 번째 메시지"

# after=msg1_id → msg2 만 반환
resp = await client_db.get(
    f"/api/v1/chat-rooms/{cr.id}/messages?after={msg1_id}",
    headers=_auth(customer)
)
assert len(resp.json()["items"]) == 1
assert resp.json()["items"][0]["content"] == "두 번째 메시지"
```

---

## 파일 구조 요약

### 신규 파일 (NEW)

```
apps/api/alembic/versions/<hash>_add_messages_table.py   # messages 테이블 마이그레이션
apps/api/app/models/message.py                            # Message ORM 모델
apps/api/app/schemas/message.py                           # MessageCreate, MessageRead, MessageListResponse
apps/api/app/repositories/messages.py                    # MessageRepository
apps/api/app/services/chat.py                             # ChatService (send, list)
apps/api/app/routers/chat.py                              # 채팅 라우터 (POST/GET messages)
apps/api/tests/test_chat_messages.py                      # 11개 pytest 케이스
apps/user-web/src/app/chat/[id]/page.tsx                  # 채팅 UI 페이지
```

### 수정 파일 (UPDATE)

```
apps/api/app/core/exceptions.py           # ChatRoomNotFoundError 추가
apps/api/app/models/__init__.py           # Message import 추가
apps/api/app/repositories/chat_rooms.py  # get_by_id() 메서드 추가
apps/api/app/main.py                      # chat_router 등록
openapi.json                              # Orval 입력 갱신
packages/api-client/src/index.ts          # chat-rooms re-export 수동 추가
packages/api-client/src/generated/        # Orval 재생성 결과물 (chat-rooms/, model/)
```

### 수정 없는 파일 (NO CHANGE)

```
apps/api/app/models/chat_room.py          # ChatRoom 모델 변경 없음
apps/api/app/schemas/chat_room.py         # ChatRoomRead 변경 없음
apps/api/app/services/quote.py            # 변경 없음
apps/api/app/routers/quotes.py            # 변경 없음
```

---

## 수동 체크포인트 (⚡)

**신규 환경변수 없음.** Railway/Supabase 설정 변경 없음.

**필수 수동 작업:**
1. `alembic upgrade head` 실행 (messages 테이블 생성)
2. Orval 재생성 후 `packages/api-client/src/index.ts` 에 `export * from './generated/chat-rooms/chat-rooms'` 수동 추가

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `pytest apps/api/tests/test_chat_messages.py` — 11/11 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과 (특히 `test_quotes_accept.py` 재확인)
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과 (apps/user-web)
- [ ] Orval 생성물 커밋 포함 (`packages/api-client/src/generated/chat-rooms/` 신규 파일)
- [ ] user-web `/chat/[id]` 채팅 화면 동작 확인:
  - CUSTOMER 수락 → 채팅방 이동 → 메시지 전송 확인
  - PRO 채팅방 접근 → 메시지 전송/수신 확인
  - 2초 폴링으로 상대 메시지 자동 갱신 확인
  - 전송 중 버튼 비활성화 확인
  - 에러 시 메시지 표시 확인

---

## 이전 스토리 인텔리전스 (Story 4.3 교훈)

1. **`CamelModel.from_attributes=True` 자동 처리:** 라우터의 `response_model` 이 ORM → Pydantic 변환을 처리. `model_validate()` 명시 불필요. `Message` ORM 객체를 반환하면 `MessageRead` 직렬화 자동.

2. **`session.refresh()` 필수:** commit 후 `created_at` 등 서버 기본값 반영. `send_message()` 에서 `commit()` 후 반드시 `refresh(msg)` 호출.

3. **`main.py` 에 이미 등록된 라우터 확인:** 현재 chat 라우터 없음 — `main.py` 에 신규 `include_router` 반드시 추가 필요. 누락 시 404 응답.

4. **Orval 재생성 후 훅 파라미터 확인 필수:** `useSendMessage`, `useListMessages` 의 실제 파라미터 구조를 생성된 `chat-rooms.ts` 에서 확인 후 프론트엔드 코드 작성.

5. **`packages/api-client/src/index.ts` 수동 업데이트:** Orval 이 `index.ts` 를 갱신하지 않는다. 신규 `chat-rooms` 모듈 수동 추가 필수 (누락 시 `useListMessages` 등 훅이 외부에서 import 불가).

6. **helpers.py 에 `_make_chat_room` 없음 확인 ⚠️:** 현재 `tests/helpers.py` 에 채팅방 생성 헬퍼가 없다. 테스트 파일 내에 로컬 헬퍼를 추가하거나 `helpers.py` 에 추가한다.

---

## Dev Agent Record

### Completion Notes

Story 4.4 전체 구현 완료 (2026-06-11).

**백엔드 (FastAPI):**
- `messages` 테이블 Alembic 마이그레이션 생성 및 적용 (revision: 217b0b5d93d4)
- `ChatRoomNotFoundError` 예외 추가 (404)
- `Message` ORM 모델 (UUIDPrimaryKeyMixin, ON DELETE CASCADE)
- `MessageCreate/MessageRead/MessageListResponse` 스키마
- `ChatRoomRepository.get_by_id()` 추가
- `MessageRepository.create()` + `list_after()` — 초기 로드 id DESC + reverse, 증분 id > after_id
- `ChatService` — 공통 가드 `_get_room_and_check_participant()` + send/list 메서드
- Chat 라우터 (`/api/v1/chat-rooms/{id}/messages` POST/GET) + main.py 등록

**알려진 결정 사항:**
- 초기 로드 정렬: `created_at DESC` 대신 `id DESC` 사용 — 동일 밀리초 내 UUIDv7 충돌 방지
- `MessageRepository.create()` 는 flush/refresh 만; service 에서 commit + refresh 재수행 (created_at 서버 기본값 반영)

**테스트:** 11/11 통과, 전체 212 테스트 회귀 없음

**프론트엔드 (Next.js):**
- Orval 재생성 → `chat-rooms/chat-rooms.ts` (useSendMessage, useListMessages, list_messages, send_message)
- `packages/api-client/src/index.ts` 수동 export 추가
- `/chat/[id]/page.tsx` — `useReducer` + `useRef` 패턴으로 증분 폴링 구현
  - `react-hooks/set-state-in-effect` 린트 규칙: `useEffect` 내 `setState` 대신 `useReducer`의 `dispatch` 사용
  - `refetchInterval: 2000`, 쿼리 키는 `["chat-messages", id]` (lastId 미포함)
  - 내 메시지 우측(blue), 상대 메시지 좌측(gray)
  - 전송 성공 시 낙관적 append + 스크롤 하단
- typecheck / lint / build 전체 통과

### File List

**신규 (NEW):**
- `apps/api/alembic/versions/217b0b5d93d4_add_messages_table.py`
- `apps/api/app/models/message.py`
- `apps/api/app/schemas/message.py`
- `apps/api/app/repositories/messages.py`
- `apps/api/app/services/chat.py`
- `apps/api/app/routers/chat.py`
- `apps/api/tests/test_chat_messages.py`
- `apps/user-web/src/app/chat/[id]/page.tsx`
- `packages/api-client/src/generated/chat-rooms/chat-rooms.ts`
- `packages/api-client/src/generated/model/listMessagesParams.ts`
- `packages/api-client/src/generated/model/messageCreate.ts`
- `packages/api-client/src/generated/model/messageListResponse.ts`
- `packages/api-client/src/generated/model/messageRead.ts`

**수정 (UPDATE):**
- `apps/api/app/core/exceptions.py` — ChatRoomNotFoundError 추가
- `apps/api/app/models/__init__.py` — Message import/export 추가
- `apps/api/app/repositories/chat_rooms.py` — get_by_id() 추가
- `apps/api/app/main.py` — chat_router 등록
- `packages/api-client/src/index.ts` — chat-rooms re-export 추가
- `packages/api-client/src/generated/model/index.ts` — 새 타입 export (Orval 자동)
- `openapi.json` — API 스펙 갱신
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 4-4 상태 업데이트

### Change Log

- 2026-06-11: Story 4.4 스토리 파일 작성 완료
- 2026-06-11: Story 4.4 구현 완료 — messages 테이블, 채팅 API (POST/GET), 11개 테스트 통과, user-web 채팅 UI
