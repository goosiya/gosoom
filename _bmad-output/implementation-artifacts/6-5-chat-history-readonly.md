---
baseline_commit: "ed6dcb1"
---

# Story 6.5: 채팅 내역 열람 (읽기 전용)

Status: done

## Story

As a 관리자,
I want 채팅방과 메시지 내역을 읽기 전용으로 열람하기를,
So that 문제가 된 거래의 상황을 감사·모니터링할 수 있다.

## Acceptance Criteria

1. **AC1 — 채팅방 목록 조회:** 관리자가 `GET /api/v1/admin/chat-rooms`를 호출하면 전체 채팅방이 `{items, nextCursor}` cursor 페이지네이션으로 반환된다. 각 항목에는 채팅방 ID·고객 표시명·고수 표시명·연관 요청 요약·생성일이 포함된다 (FR23).

2. **AC2 — 메시지 목록 조회:** 관리자가 `GET /api/v1/admin/chat-rooms/{id}/messages`를 호출하면 해당 채팅방의 메시지 목록이 반환된다. 각 메시지에 발신자 ID·내용·생성일이 포함된다 (FR23).

3. **AC3 — 쓰기 엔드포인트 미제공:** 관리자 채팅 라우터에는 메시지 전송·수정·삭제 엔드포인트가 존재하지 않는다 — 열람 전용 (FR23).

4. **AC4 — 관리 UI (채팅방 목록):** admin-web의 `/chats` 화면에서 채팅방 목록이 표시된다. 각 행에 고객명·고수명·연관 요청 ID·생성일이 표시되고, "상세보기" 버튼으로 해당 채팅방 메시지 화면(`/chats/[id]`)으로 이동한다.

5. **AC5 — 관리 UI (메시지 화면):** admin-web의 `/chats/[id]` 화면에서 채팅 메시지가 발신자(고객/고수 표시명)와 시간과 함께 시간 순으로 표시된다. 메시지 입력창·전송 버튼 등 쓰기 UI는 없다.

## Dev Notes

### 아키텍처 핵심 제약 (위반 시 재작업)

- **패턴 A 엄수:** admin-web은 `@gosoom/api-client`만 통해 `/api/v1`에 접근. Supabase·DB 직접 접속 절대 금지 (AR8).
- **권한 최종 시행은 서버:** AdminGuard는 UX 보조. 실제 권한 검사는 FastAPI `require_role('admin')` (AR17).
- **읽기 전용만 허용:** 관리자 채팅 엔드포인트는 GET만 — POST/PATCH/DELETE 추가 절대 금지 (FR23).
- **service 계층이 비즈니스 로직 소유:** 라우터는 HTTP 변환만. 채팅방 존재 검사·발신자 정보 조합은 service에서 (NFR4).
- **Orval 생성물 수동 수정 금지:** `packages/api-client/src/generated/` 파일 편집하지 말 것 (AR9). 백엔드 변경 후 반드시 `pnpm orval` 재실행.
- **에러는 `error.message`로 노출:** 한국어 메시지는 백엔드 envelope `message` 필드 → api-client `ApiError.message` 변환 (AR12).

### 기존 인프라 활용 (새로 구현 금지)

**기존 모델 — 그대로 재사용 (신규 마이그레이션 불필요):**
```python
# apps/api/app/models/chat_room.py
class ChatRoom(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "chat_rooms"
    service_request_id: UUID  # FK → service_requests.id
    customer_id: UUID          # FK → users.id
    pro_id: UUID               # FK → users.id
    quote_id: UUID             # FK → quotes.id (UNIQUE)
    created_at: datetime

# apps/api/app/models/message.py
class Message(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "messages"
    chat_room_id: UUID  # FK → chat_rooms.id (CASCADE)
    sender_id: UUID     # FK → users.id (CASCADE)
    content: str
    created_at: datetime
```

**`ChatRoomRepository` 기존 메서드 — 사용 가능:**
```python
# apps/api/app/repositories/chat_rooms.py
async def get_by_id(self, chat_room_id: uuid.UUID) -> ChatRoom | None:
    """PK로 채팅방 단건 조회. 이 스토리에서 메시지 조회 전 존재 확인용으로 사용."""
async def list_mine(self, user_id, role, after_id, limit) -> list[ChatRoom]:
    """참여자 필터 — admin 용도에는 부적합. 신규 list_all() 추가 필요."""
```

**`MessageRepository` 기존 메서드 — 재사용:**
```python
# apps/api/app/repositories/messages.py
async def list_after(
    self,
    chat_room_id: uuid.UUID,
    after_id: uuid.UUID | None,
    limit: int = 50,
) -> list[Message]:
    """after_id=None: 최신 50개 DESC 후 역순. after_id 있음: 이후 ASC 증분."""
```

**`UserRepository.list_by_ids` — 발신자/참여자 이름 일괄 조회:**
```python
# apps/api/app/repositories/users.py:45
async def list_by_ids(self, ids: list[UUID]) -> list[User]:
    """ID 목록으로 사용자 일괄 조회."""
```

**`ServiceRequestRepository.list_by_ids` — 연관 요청 요약 일괄 조회:**
```python
# ChatService.list_my_chat_rooms에서 이미 사용 중인 패턴
async def list_by_ids(self, ids: list[uuid.UUID]) -> list[ServiceRequest]:
```

**기존 스키마 재사용:**
```python
from app.schemas.chat_room import ChatRoomRead  # id, service_request_id, customer_id, pro_id, quote_id, created_at
from app.schemas.message import MessageRead, MessageListResponse  # 그대로 재사용
from app.schemas.service_request import ServiceRequestSummary  # 연관 요청 요약
```

**기존 예외 재사용:**
```python
from app.core.exceptions import ChatRoomNotFoundError  # 채팅방 없을 때 404
```

**기존 pagination 패턴 재사용 (Story 6.2/6.3/6.4와 동일):**
```python
from app.core.pagination import decode_cursor, encode_cursor
from app.schemas.pagination import Page
```

**재사용할 admin-web 컴포넌트 (신규 설치 금지):**
```ts
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
```

**AdminHeader.tsx에 이미 `/chats` 네비 링크 존재:**
```ts
// apps/admin-web/src/components/AdminHeader.tsx:16
{ href: "/chats", label: "채팅내역" }  // ← 이미 존재
```
→ 네비게이션 수정 불필요. `/chats` 페이지와 `/chats/[id]` 페이지만 생성.

### 구현 순서 (중요: 순차 실행)

1. 백엔드 구현 (schema → repository → service → router)
2. openapi.json 재생성
3. `pnpm orval` 실행 (api-client 훅 재생성)
4. admin-web 프론트엔드 구현

### 백엔드 구현 상세

#### 1. `apps/api/app/schemas/chat_room.py` — `ChatRoomAdminRead` 추가

파일 하단에 추가:
```python
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
```

→ `from app.schemas.service_request import ServiceRequestSummary` import가 파일 상단에 이미 있음 (기존 `ChatRoomListItem`에서 사용 중). `Optional`은 `from typing import Optional`로 이미 import됨.

#### 2. `apps/api/app/repositories/chat_rooms.py` — `list_all()` 메서드 추가

```python
async def list_all(
    self,
    after_id: uuid.UUID | None,
    limit: int,
) -> list[ChatRoom]:
    """모든 채팅방 조회 (관리자 전용). id DESC cursor 페이지네이션."""
    stmt = select(ChatRoom)
    if after_id is not None:
        stmt = stmt.where(ChatRoom.id < after_id)
    stmt = stmt.order_by(ChatRoom.id.desc()).limit(limit)
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

→ 기존 `list_mine`과 동일한 패턴. `from sqlalchemy import select` 이미 import됨.

#### 3. `apps/api/app/services/admin.py` — `AdminChatService` 클래스 추가

파일 상단 imports에 추가:
```python
from app.core.exceptions import ChatRoomNotFoundError  # 추가
from app.models.chat_room import ChatRoom              # 추가
from app.repositories.chat_rooms import ChatRoomRepository  # 추가
from app.repositories.messages import MessageRepository     # 추가
from app.repositories.users import UserRepository           # 추가
from app.schemas.chat_room import ChatRoomAdminRead        # 추가
from app.schemas.message import MessageListResponse, MessageRead  # 추가
from app.schemas.service_request import ServiceRequestSummary     # 추가
```

파일 하단에 새 클래스 추가 (`AdminServiceRequestService` 아래):
```python
class AdminChatService:
    """채팅 내역 열람 (Story 6.5) — 읽기 전용, 참여자 검사 없는 관리자 전용."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.chat_room_repo = ChatRoomRepository(session)
        self.message_repo = MessageRepository(session)

    async def list_chat_rooms(
        self,
        cursor: str | None,
        limit: int,
    ) -> "Page[ChatRoomAdminRead]":
        """전체 채팅방 목록 조회 — cursor id DESC 페이지네이션 + 참여자 이름 포함."""
        if limit < 1:
            raise ValueError("limit must be >= 1")
        after_id: UUID | None = None
        if cursor:
            try:
                after_id = UUID(decode_cursor(cursor))
            except (ValueError, AttributeError) as exc:
                raise InvalidCursorError() from exc
        rooms = await self.chat_room_repo.list_all(after_id, limit + 1)
        has_more = len(rooms) > limit
        page = rooms[:limit]
        next_cursor = encode_cursor(str(page[-1].id)) if has_more else None

        if not page:
            return Page(items=[], next_cursor=None)

        user_repo = UserRepository(self.session)
        sr_repo = ServiceRequestRepository(self.session)

        all_user_ids = list({r.customer_id for r in page} | {r.pro_id for r in page})
        sr_ids = [r.service_request_id for r in page]

        users = {u.id: u for u in await user_repo.list_by_ids(all_user_ids)}
        srs = {sr.id: sr for sr in await sr_repo.list_by_ids(sr_ids)}

        items = []
        for room in page:
            customer = users.get(room.customer_id)
            pro = users.get(room.pro_id)
            sr = srs.get(room.service_request_id)
            items.append(
                ChatRoomAdminRead(
                    id=room.id,
                    service_request_id=room.service_request_id,
                    customer_id=room.customer_id,
                    pro_id=room.pro_id,
                    quote_id=room.quote_id,
                    created_at=room.created_at,
                    customer_display_name=customer.display_name if customer else "알 수 없음",
                    pro_display_name=pro.display_name if pro else "알 수 없음",
                    service_request=ServiceRequestSummary.model_validate(sr) if sr else None,
                )
            )
        return Page(items=items, next_cursor=next_cursor)

    async def list_messages(
        self,
        chat_room_id: UUID,
        after_id: UUID | None,
    ) -> MessageListResponse:
        """채팅방 메시지 목록 조회 — 참여자 검사 없는 관리자 전용.

        after_id=None: 최신 50개(DESC 후 역순 반환). after_id 있음: 이후 증분 ASC.
        기존 MessageRepository.list_after 재사용.
        """
        room = await self.chat_room_repo.get_by_id(chat_room_id)
        if room is None:
            raise ChatRoomNotFoundError()
        messages = await self.message_repo.list_after(chat_room_id, after_id)
        return MessageListResponse(
            items=[MessageRead.model_validate(m) for m in messages]
        )
```

**imports 추가 위치:** 파일 상단 기존 imports 블록에 편입. 중복 import 주의. `UserRepository`·`ServiceRequestRepository`는 이미 import되어 있으므로 확인 후 추가.

#### 4. `apps/api/app/routers/admin.py` — 엔드포인트 2개 추가

기존 imports에 추가:
```python
from app.schemas.chat_room import ChatRoomAdminRead
from app.schemas.message import MessageListResponse
from app.services.admin import AdminChatService, AdminServiceRequestService, AdminUserService
```

라우터 하단에 추가:
```python
@router.get("/chat-rooms", response_model=Page[ChatRoomAdminRead])
async def list_admin_chat_rooms(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[ChatRoomAdminRead]:
    return await AdminChatService(db).list_chat_rooms(cursor, limit)


@router.get("/chat-rooms/{chat_room_id}/messages", response_model=MessageListResponse)
async def list_admin_chat_messages(
    chat_room_id: UUID,
    after: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> MessageListResponse:
    return await AdminChatService(db).list_messages(chat_room_id, after)
```

⚠️ **route collision 주의:** `/chat-rooms`와 `/chat-rooms/{id}/messages` 경로가 기존 사용자용 `/api/v1/chat-rooms`와 path가 다름 (admin prefix `/api/v1/admin/` 하위이므로 충돌 없음).

#### 5. openapi.json 재생성 (백엔드 구현 완료 후)

`apps/api` 디렉토리에서 실행:
```bash
uv run python -c "
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app.main import app
print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
" > ../../openapi.json
```

⚠️ **Windows cp949 이슈:** Story 6.4에서 stdout 직접 쓰기 대신 파일로 저장하면 인코딩 오류 발생. 위 방식 또는 아래 방식 사용:
```bash
uv run python -c "
from app.main import app
import json
with open('../../openapi.json', 'w', encoding='utf-8') as f:
    json.dump(app.openapi(), f, ensure_ascii=False, indent=2)
print('openapi.json 재생성 완료')
"
```

확인: `openapi.json`에 `/api/v1/admin/chat-rooms` 경로 2개 + `ChatRoomAdminRead` 스키마 포함 여부.

#### 6. pnpm orval — API 클라이언트 재생성

프로젝트 루트에서:
```bash
pnpm orval
```

생성/변경 결과 확인:
- `packages/api-client/src/generated/admin/admin.ts` — 신규 훅 2개:
  - `useListAdminChatRooms({ cursor?, limit? })` → `Page<ChatRoomAdminRead>`
  - `useListAdminChatMessages({ chatRoomId, after? })` → `MessageListResponse`
- `packages/api-client/src/generated/model/chatRoomAdminRead.ts` — 신규 생성
- `packages/api-client/src/generated/model/index.ts` — AUTO-UPDATED

⚠️ **Orval 훅명은 operationId에서 추출.** 생성된 파일에서 export 이름 반드시 확인 후 import.

### 프론트엔드 구현 상세

#### 7. `apps/admin-web/src/app/(admin)/chats/page.tsx` — 신규 생성

**페이지 구조:**
```
/chats 페이지
├─ 헤더: "채팅 내역" 제목
└─ ChatRoomsTable
   ├─ Table: 채팅방ID | 고객 | 고수 | 요청 | 생성일 | 액션
   └─ LoadMore: nextCursor 있을 때 "더 보기" 버튼
```

**구현 패턴 (훅명은 생성 후 확인):**
```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  useListAdminChatRooms,
  type ChatRoomAdminRead,
} from "@gosoom/api-client";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

export default function ChatsPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">채팅 내역</h1>
      <ChatRoomsTable />
    </main>
  );
}

function ChatRoomsTable() {
  const router = useRouter();
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<ChatRoomAdminRead[]>([]);

  const { data, isLoading, isFetching } = useListAdminChatRooms({
    limit: 20,
    cursor,
  });

  // Story 6.2~6.4와 동일한 cursor 누적 패턴
  useEffect(() => {
    if (!data?.items) return;
    if (!cursor) {
      setAllItems(data.items);
    } else {
      setAllItems((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        return [...prev, ...data.items.filter((i) => !existingIds.has(i.id))];
      });
    }
  }, [data]);

  const formatDate = (iso: string) => new Date(iso).toLocaleDateString("ko-KR");

  if (isLoading && allItems.length === 0) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="animate-pulse bg-muted rounded h-12" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>채팅방 ID</TableHead>
            <TableHead>고객</TableHead>
            <TableHead>고수</TableHead>
            <TableHead>연관 요청</TableHead>
            <TableHead>생성일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                채팅 내역이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((room) => (
              <TableRow key={room.id}>
                <TableCell className="font-mono text-xs">
                  {String(room.id).substring(0, 8)}
                </TableCell>
                <TableCell>{room.customerDisplayName}</TableCell>
                <TableCell>{room.proDisplayName}</TableCell>
                <TableCell className="font-mono text-xs">
                  {room.serviceRequest
                    ? String(room.serviceRequest.id).substring(0, 8)
                    : String(room.serviceRequestId).substring(0, 8)}
                </TableCell>
                <TableCell>{formatDate(room.createdAt)}</TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/chats/${room.id}`)}
                  >
                    상세보기
                  </Button>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {data?.nextCursor && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => setCursor(data.nextCursor ?? undefined)}
            disabled={isFetching}
          >
            {isFetching ? "불러오는 중..." : "더 보기"}
          </Button>
        </div>
      )}
    </div>
  );
}
```

#### 8. `apps/admin-web/src/app/(admin)/chats/[id]/page.tsx` — 신규 생성

**페이지 구조:**
```
/chats/[id] 페이지
├─ 뒤로가기 버튼 → /chats
├─ 헤더: "채팅 내역 (ID: {id 앞 8자리})" + 고객명·고수명 표시
├─ 메시지 목록 (시간 순 오름차순, 스크롤)
│  ├─ 각 메시지: [발신자명] [시간] 내용
│  └─ 고객 메시지와 고수 메시지 구분 표시 (정렬 방향 또는 배경색)
└─ 입력창 없음 (읽기 전용)
```

**구현 패턴 (훅명은 생성 후 확인):**
```tsx
"use client";
import { use } from "react";
import Link from "next/link";
import {
  useListAdminChatRooms,
  useListAdminChatMessages,
  type ChatRoomAdminRead,
  type MessageRead,
} from "@gosoom/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  params: Promise<{ id: string }>;
}

export default function ChatDetailPage({ params }: Props) {
  const { id } = use(params);
  return <ChatDetail chatRoomId={id} />;
}

function ChatDetail({ chatRoomId }: { chatRoomId: string }) {
  // 채팅방 목록에서 해당 방 정보를 찾아 고객/고수 이름 표시
  // 단순화: 첫 페이지만 조회 (목록 화면에서 진입하므로 대부분 데이터가 캐시에 있음)
  const roomsData = useListAdminChatRooms({ limit: 100 });
  const messagesData = useListAdminChatMessages({ chatRoomId });

  const room = roomsData.data?.items?.find((r: ChatRoomAdminRead) => r.id === chatRoomId);
  const messages: MessageRead[] = messagesData.data?.items ?? [];

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleString("ko-KR", {
      month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });

  const getSenderName = (senderId: string): string => {
    if (!room) return senderId.substring(0, 8);
    if (senderId === room.customerId) return room.customerDisplayName;
    if (senderId === room.proId) return room.proDisplayName;
    return senderId.substring(0, 8);
  };

  const isCustomer = (senderId: string): boolean =>
    room ? senderId === room.customerId : false;

  if (messagesData.isLoading) {
    return (
      <main className="max-w-screen-xl mx-auto p-6">
        <div className="animate-pulse bg-muted rounded h-64" />
      </main>
    );
  }

  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <div className="mb-4">
        <Link href="/chats">
          <Button variant="ghost" size="sm">← 목록으로</Button>
        </Link>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-xl">
            채팅방 상세 — <span className="font-mono text-base">{chatRoomId.substring(0, 8)}</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {room && (
            <div className="flex gap-6 text-sm text-muted-foreground">
              <span>고객: <strong className="text-foreground">{room.customerDisplayName}</strong></span>
              <span>고수: <strong className="text-foreground">{room.proDisplayName}</strong></span>
              <span>
                연관 요청:{" "}
                <strong className="font-mono text-foreground">
                  {room.serviceRequest
                    ? room.serviceRequest.id.substring(0, 8)
                    : room.serviceRequestId.substring(0, 8)}
                </strong>
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3 max-h-[60vh] overflow-y-auto border rounded-md p-4 bg-muted/20">
        {messages.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">메시지가 없습니다.</p>
        ) : (
          messages.map((msg) => {
            const customer = isCustomer(msg.senderId);
            return (
              <div
                key={msg.id}
                className={`flex flex-col ${customer ? "items-start" : "items-end"}`}
              >
                <span className="text-xs text-muted-foreground mb-1">
                  {getSenderName(msg.senderId)} · {formatTime(msg.createdAt)}
                </span>
                <div
                  className={`max-w-[70%] rounded-lg px-3 py-2 text-sm ${
                    customer
                      ? "bg-background border"
                      : "bg-primary text-primary-foreground"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}
      </div>

      <p className="mt-4 text-xs text-muted-foreground text-center">
        읽기 전용 — 메시지 전송 불가
      </p>
    </main>
  );
}
```

⚠️ **주의사항:**
- `useListAdminChatRooms`의 반환 타입 `items`가 `ChatRoomAdminRead[]`인지 생성 파일 확인 필수.
- `useListAdminChatMessages`의 파라미터명 (`chatRoomId` vs `chatRoomId`) — 생성 파일에서 확인.
- `params`는 Next.js 15에서 `Promise<{id: string}>` 타입. `use(params)`로 unwrap 필요. `apps/admin-web/AGENTS.md` 주석 참고 (Next.js breaking changes 주의).
- camelCase 변환: 백엔드 `customer_display_name` → Orval이 `customerDisplayName`으로 변환 (CamelModel이 alias_generator 사용). 생성 파일 확인 필수.
- `useListAdminChatRooms({ limit: 100 })` 를 detail 페이지에서 호출 시, 실제 환경에서 채팅방이 100개 초과라면 해당 방 정보를 못 찾을 수 있음. **더 안전한 대안:** `GET /api/v1/admin/chat-rooms/{id}` 단건 조회 엔드포인트를 추가하거나, 메시지 응답에 채팅방 정보를 포함하는 방식. 현재 스코프에서는 목록에서 진입 가정(캐시 히트)으로 처리. 만약 구현 중 문제가 된다면 `useListAdminChatRooms({ limit: 100, cursor: undefined })`를 `useListAdminChatRooms({ limit: 100 })`로 충분.

### 기존 코드 패턴 참조

| 패턴 | 참조 파일 |
|------|----------|
| Cursor 페이지네이션 service | `apps/api/app/services/admin.py:list_requests` (162-184행) |
| list_all 패턴 | `apps/api/app/repositories/service_requests.py:list_all` |
| 참여자 이름 일괄 조회 | `apps/api/app/services/chat.py:list_my_chat_rooms` (63-105행) |
| cursor 누적 패턴 (useEffect) | `apps/admin-web/src/app/(admin)/requests/page.tsx` |
| Table + LoadMore 패턴 | `apps/admin-web/src/app/(admin)/requests/page.tsx` |
| ChatRoomRepository | `apps/api/app/repositories/chat_rooms.py` |
| MessageRepository.list_after | `apps/api/app/repositories/messages.py` |

### Story 6.4 주요 학습사항 (적용 필수)

- **Orval 훅명:** 실제 생성 파일(`packages/api-client/src/generated/admin/admin.ts`)에서 export 이름 반드시 확인.
- **Windows cp949 인코딩 이슈:** `openapi.json` 재생성 시 stdout 대신 `open(..., encoding='utf-8')` 파일 직접 쓰기.
- **TypeScript 타입체크:** `node_modules/.bin/tsc --noEmit -p apps/admin-web/tsconfig.json`
- **ruff lint 확인:** `uv run ruff check app/` — 미사용 import (F401) 제거 필수.
- **camelCase alias:** Orval은 `customer_display_name` → `customerDisplayName`으로 변환. 생성 파일 타입 확인 필수.
- **Orval 파라미터 snake_case:** Orval이 쿼리 파라미터를 반드시 camelCase로 변환하지 않을 수 있음 (Story 6.4의 `include_hidden` 사례). 생성 파일 확인 후 사용.
- **commit 후 model_validate:** `AdminChatService`의 `list_messages`도 기존 패턴 준수. `MessageRead.model_validate(m)` 패턴 그대로 사용.
- **Next.js 15 params:** `use(params)` unwrap 패턴 사용 (`async function`으로 선언하거나 `use()` hook 사용). `apps/admin-web/AGENTS.md` 참조 필수.

## 파일 구조 (이 스토리에서 생성/수정)

```
apps/api/app/
├─ schemas/chat_room.py           ← MODIFY: ChatRoomAdminRead 클래스 추가
├─ repositories/chat_rooms.py     ← MODIFY: list_all() 메서드 추가
├─ services/admin.py              ← MODIFY: imports 추가 + AdminChatService 클래스 추가
└─ routers/admin.py               ← MODIFY: imports 추가 + GET /chat-rooms 엔드포인트 2개 추가

openapi.json                      ← REGENERATE: ChatRoomAdminRead + /admin/chat-rooms 경로 2개

packages/api-client/src/
└─ generated/
   ├─ admin/admin.ts              ← AUTO-UPDATED: 신규 훅 2개 추가
   ├─ model/chatRoomAdminRead.ts  ← AUTO-CREATED
   └─ model/index.ts              ← AUTO-UPDATED

apps/admin-web/src/
└─ app/(admin)/chats/
   ├─ page.tsx                    ← CREATE: 채팅방 목록 화면
   └─ [id]/
      └─ page.tsx                 ← CREATE: 채팅방 메시지 상세 화면 (읽기 전용)
```

## Tasks / Subtasks

- [x] Task 1 — 백엔드: Schema 추가 (AC1)
  - [x] 1.1: `apps/api/app/schemas/chat_room.py` 하단에 `ChatRoomAdminRead` 클래스 추가 — `customer_display_name`, `pro_display_name`, `service_request: Optional[ServiceRequestSummary]` 필드 포함

- [x] Task 2 — 백엔드: Repository 메서드 추가 (AC1)
  - [x] 2.1: `apps/api/app/repositories/chat_rooms.py`에 `list_all(after_id, limit)` 메서드 추가 — deleted_at 없이 전체 채팅방 id DESC 페이지네이션

- [x] Task 3 — 백엔드: AdminChatService 구현 (AC1, AC2, AC3)
  - [x] 3.1: `apps/api/app/services/admin.py` 상단 imports에 `ChatRoomNotFoundError`, `ChatRoomRepository`, `MessageRepository`, `ChatRoomAdminRead`, `MessageListResponse`, `MessageRead`, `ServiceRequestSummary` 추가
  - [x] 3.2: `AdminChatService` 클래스 추가 — `list_chat_rooms(cursor, limit)` 메서드 (cursor 페이지네이션, 참여자 이름 조회 포함)
  - [x] 3.3: `list_messages(chat_room_id, after_id)` 메서드 추가 — `get_by_id`로 채팅방 존재 확인, `list_after` 재사용, 참여자 검사 없음

- [x] Task 4 — 백엔드: 라우터 엔드포인트 추가 (AC1, AC2, AC3)
  - [x] 4.1: `apps/api/app/routers/admin.py`에 `ChatRoomAdminRead`, `MessageListResponse`, `AdminChatService` imports 추가
  - [x] 4.2: `GET /chat-rooms` 엔드포인트 추가 — cursor, limit 쿼리 파라미터, `Page[ChatRoomAdminRead]` 응답
  - [x] 4.3: `GET /chat-rooms/{chat_room_id}/messages` 엔드포인트 추가 — after (UUID) 쿼리 파라미터, `MessageListResponse` 응답 (쓰기 엔드포인트 미추가 — AC3 준수)

- [x] Task 5 — openapi.json 재생성 및 api-client 갱신 (AC1, AC2)
  - [x] 5.1: `apps/api` 디렉토리에서 `open(..., encoding='utf-8')` 방식으로 openapi.json 재생성 (Windows cp949 이슈 회피)
  - [x] 5.2: openapi.json에 `ChatRoomAdminRead` 스키마 + `customerDisplayName`/`proDisplayName` 필드 포함 확인
  - [x] 5.3: openapi.json에 `/api/v1/admin/chat-rooms` (GET) + `/api/v1/admin/chat-rooms/{id}/messages` (GET) 경로 확인
  - [x] 5.4: 프로젝트 루트에서 `pnpm orval` 실행
  - [x] 5.5: 생성된 `packages/api-client/src/generated/admin/admin.ts`에서 훅명 2개 확인 — `useListAdminChatRooms`, `useListAdminChatMessages`
  - [x] 5.6: `packages/api-client/src/generated/model/chatRoomAdminRead.ts` 생성 확인

- [x] Task 6 — admin-web: 채팅방 목록 페이지 구현 (AC4)
  - [x] 6.1: `apps/admin-web/src/app/(admin)/chats/page.tsx` 신규 생성 — `"use client"` 선언
  - [x] 6.2: `ChatRoomsTable` 컴포넌트 구현 — `useListAdminChatRooms` 훅 + cursor 누적 패턴 (Story 6.2~6.4와 동일)
  - [x] 6.3: 테이블 열 구성: 채팅방ID(앞8자리) | 고객 | 고수 | 연관요청ID | 생성일 | 액션
  - [x] 6.4: "상세보기" 버튼 — `router.push('/chats/${room.id}')` 로 메시지 화면 이동
  - [x] 6.5: cursor 기반 "더 보기" 버튼 — `data.nextCursor` 있을 때 표시

- [x] Task 7 — admin-web: 메시지 상세 페이지 구현 (AC5)
  - [x] 7.1: `apps/admin-web/src/app/(admin)/chats/[id]/page.tsx` 신규 생성
  - [x] 7.2: `use(params)`로 `id` 파라미터 unwrap (Next.js 15 Breaking Change)
  - [x] 7.3: `useListAdminChatMessages(chatRoomId)` 훅으로 메시지 목록 조회
  - [x] 7.4: 채팅방 정보 표시 (고객명·고수명·연관요청 ID)
  - [x] 7.5: 메시지 목록 시간 순 표시 — 발신자 이름 + 시간 + 내용 (고객/고수 시각적 구분)
  - [x] 7.6: 입력창·전송 버튼 없음 확인 (AC5, FR23 준수)
  - [x] 7.7: "← 목록으로" 뒤로가기 버튼 (`Link href="/chats"`)
  - [x] 7.8: "읽기 전용" 안내 문구 표시

- [x] Task 8 — 타입체크 및 lint 확인 (AC1~AC5)
  - [x] 8.1: `uv run ruff check app/` → All checks passed
  - [x] 8.2: `node_modules/.bin/tsc --noEmit -p apps/admin-web/tsconfig.json` → 오류 없음

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Orval 훅 시그니처 확인: `useListAdminChatMessages(chatRoomId: string, params?)` — path param이 첫 번째 인자로 분리됨 (story spec과 다름, 생성 파일 직접 확인 후 수정)
- `ChatRoomAdminReadServiceRequest = ServiceRequestSummary | null` — serviceRequest 필드 null 허용 타입 확인

### Completion Notes List

- `ChatRoomAdminRead` 스키마 추가 (customer_display_name, pro_display_name, service_request 포함)
- `ChatRoomRepository.list_all()` 추가 — 전체 채팅방 id DESC cursor 페이지네이션
- `AdminChatService` 구현 — list_chat_rooms (참여자 이름 일괄 조회), list_messages (참여자 검사 없음)
- `GET /api/v1/admin/chat-rooms`, `GET /api/v1/admin/chat-rooms/{chat_room_id}/messages` 엔드포인트 추가. 쓰기 엔드포인트 없음 (AC3 준수)
- openapi.json 재생성 + pnpm orval로 `useListAdminChatRooms`, `useListAdminChatMessages` 훅 생성
- `/chats/page.tsx` — cursor 누적 패턴 + 상세보기 버튼
- `/chats/[id]/page.tsx` — Next.js 15 `use(params)` unwrap, 메시지 고객/고수 시각적 구분, 읽기 전용 안내

### File List

- `apps/api/app/schemas/chat_room.py` — ChatRoomAdminRead 클래스 추가
- `apps/api/app/repositories/chat_rooms.py` — list_all() 메서드 추가
- `apps/api/app/services/admin.py` — imports 추가, AdminChatService 클래스 추가
- `apps/api/app/routers/admin.py` — imports 추가, GET /chat-rooms 엔드포인트 2개 추가
- `openapi.json` — 재생성
- `packages/api-client/src/generated/admin/admin.ts` — AUTO-UPDATED (훅 2개 추가)
- `packages/api-client/src/generated/model/chatRoomAdminRead.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/chatRoomAdminReadServiceRequest.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/listAdminChatRoomsParams.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/listAdminChatMessagesParams.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/index.ts` — AUTO-UPDATED
- `apps/admin-web/src/app/(admin)/chats/page.tsx` — 신규 생성
- `apps/admin-web/src/app/(admin)/chats/[id]/page.tsx` — 신규 생성

### Review Findings

- [x] [Review][Decision→Patch] 채팅방 상세 페이지 단건 조회 우회 — `GET /api/v1/admin/chat-rooms/{chat_room_id}` 단건 엔드포인트 + `AdminChatService.get_chat_room` + `useGetAdminChatRoom` 훅으로 교체. 적용 완료.
- [x] [Review][Decision→Patch] 메시지 목록 50개 제한 — `MessagePageResponse(items, next_cursor)` admin 전용 스키마 + `MessageRepository.list_before` + `before` cursor 페이지네이션 + "이전 메시지 보기" UI 추가. 적용 완료.
- [x] [Review][Patch] `list_chat_rooms` 가드 순서 역전 — `if not page` early return을 `next_cursor` 계산 이전으로 이동. 적용 완료. [`apps/api/app/services/admin.py`]
- [x] [Review][Patch] 에러 상태 UI 없음 — `isError`/`error.message` 분기 추가. 적용 완료. [`apps/admin-web/src/app/(admin)/chats/page.tsx`, `apps/admin-web/src/app/(admin)/chats/[id]/page.tsx`]
- [x] [Review][Defer] `useEffect` deps에서 `cursor` 제외 [`apps/admin-web/src/app/(admin)/chats/page.tsx`] — deferred, pre-existing (6.2~6.4 기존 패턴과 일관성)
- [x] [Review][Defer] UUID7 기반 cursor 페이지네이션 — `id < after_id` 비교는 UUID7 단조성 가정 [`apps/api/app/repositories/chat_rooms.py`] — deferred, pre-existing (프로젝트 전체 기존 패턴)

## Change Log

- 2026-06-12: Story 6.5 스토리 파일 생성
- 2026-06-12: Story 6.5 구현 완료 — 백엔드 읽기 전용 채팅방/메시지 API 2개 + admin-web 채팅 목록/상세 페이지 구현
