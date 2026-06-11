---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 4.5: 채팅방 목록 조회

- **Status:** done
- **Epic:** 4 — 매칭 & 채팅 (거래 루프 완결) (FR8, FR13-18)
- **Story ID / Key:** 4-5 / 4-5-chatroom-list
- **작성일:** 2026-06-11

---

## 사용자 스토리

As a 로그인한 고객(CUSTOMER) 또는 고수(PRO),
내가 참여 중인 채팅방 목록을 조회하고 싶다.
So that 진행 중인 여러 거래의 대화에 쉽게 접근할 수 있다.

---

## 인수 기준 (BDD)

**AC1** — 채팅방 목록 조회 성공 (FR18)

- **Given** CUSTOMER로 로그인한 사용자가 1개 이상의 채팅방에 참여 중일 때
- **When** `GET /api/v1/chat-rooms?mine=true` 를 호출하면
- **Then** `{items, nextCursor}` 형식으로 본인의 채팅방 목록이 반환된다
- **And** `customer_id = 현재 사용자 ID` 기준으로 필터링된다

**AC2** — PRO 기준 필터링

- **Given** PRO로 로그인한 사용자가 채팅방에 참여 중일 때
- **When** `GET /api/v1/chat-rooms?mine=true` 를 호출하면
- **Then** `pro_id = 현재 사용자 ID` 기준으로 필터링된 채팅방만 반환된다

**AC3** — 응답에 상대방 정보·요청 정보 포함 (이메일 미노출)

- **Given** 채팅방 목록이 조회될 때
- **Then** 각 아이템에 `counterpartDisplayName` (상대방 displayName) 이 포함된다
- **And** 각 아이템에 `serviceRequest` (id, categoryId, region, description, status) 가 포함된다
- **And** 이메일 등 민감정보는 미노출이다

**AC4** — cursor 페이지네이션

- **Given** 참여 중인 채팅방이 21개 이상일 때
- **When** `GET /api/v1/chat-rooms?mine=true` 를 호출하면
- **Then** 최신 20개가 반환되고 `nextCursor` 가 마지막 아이템 id 로 설정된다
- **When** `GET /api/v1/chat-rooms?mine=true&cursor={nextCursor}` 를 호출하면
- **Then** 그 다음 페이지의 채팅방이 반환된다
- **And** 마지막 페이지에서 `nextCursor` 는 `null` 이다

**AC5** — 권한 검사

- **Given** 비인증 요청 → 401 `not_authenticated`
- **Given** `is_active=False` 계정 → `get_current_user` 에서 401 차단 (비활성 계정)

**AC6** — user-web 채팅 목록 화면

- **Given** CUSTOMER 또는 PRO가 로그인한 상태에서
- **When** `chat/` 경로에 접근하면
- **Then** 본인의 채팅방 목록이 표시된다
- **And** 각 항목에 상대방 `displayName` 과 연관 서비스 요청 정보가 표시된다
- **And** 항목 클릭 시 해당 채팅방(`/chat/[id]`)으로 이동한다
- **And** 20개 초과 시 "더 보기" 버튼으로 추가 로드된다

---

## 태스크 및 서브태스크

- [x] **Task 1:** `schemas/chat_room.py` — `ChatRoomListItem` · `PageChatRoomListItem` 추가
  - [x] `ChatRoomListItem(CamelModel)` 정의: id, service_request_id, created_at, counterpart_display_name, service_request
  - [x] `PageChatRoomListItem(CamelModel)` 정의: items, next_cursor
  - [x] `from app.schemas.service_request import ServiceRequestSummary` import 추가

- [x] **Task 2:** `repositories/chat_rooms.py` — `list_mine()` 메서드 추가
  - [x] `async list_mine(user_id, role, after_id, limit)` — 역할별 필터 + keyset cursor + ORDER BY id DESC + LIMIT

- [x] **Task 3:** `services/chat.py` — `list_my_chat_rooms()` 메서드 추가
  - [x] LIMIT+1 조회로 has_more 판단 → `next_cursor` 계산
  - [x] `user_repo.list_by_ids(counterpart_ids)` 배치 조회 → `counterpart_display_name` 조립
  - [x] `sr_repo.list_by_ids(sr_ids)` 배치 조회 → `service_request: ServiceRequestSummary` 조립
  - [x] `UserRepository`, `ServiceRequestRepository` import 추가

- [x] **Task 4:** `routers/chat.py` — `GET /api/v1/chat-rooms` 엔드포인트 추가
  - [x] 함수명: `list_chat_rooms` (operationId 안정화)
  - [x] `mine: bool = Query(default=True)` 파라미터 (spec 준수, 값은 무시하고 항상 현재 사용자 기준)
  - [x] `cursor: uuid.UUID | None = None` 파라미터
  - [x] 응답 모델: `PageChatRoomListItem`, 200

- [x] **Task 5:** pytest 작성 (`apps/api/tests/test_chat_rooms_list.py`)
  - [x] AC1 CUSTOMER 목록 조회: 200, items 반환, customer_id 기준 필터링 확인
  - [x] AC2 PRO 목록 조회: 200, items 반환, pro_id 기준 필터링 확인
  - [x] AC3 counterpart_display_name 포함: CUSTOMER → pro displayName, PRO → customer displayName
  - [x] AC3 service_request 포함: id·description·region·status 필드 확인
  - [x] AC3 이메일 미노출: 응답 dict에 'email' 키 없음 확인
  - [x] AC4 cursor 페이지네이션: 21개 생성 후 첫 페이지 20개 + nextCursor 확인, 두 번째 페이지 1개 + nextCursor=null 확인
  - [x] AC5 비인증 → 401 `not_authenticated`
  - [x] 타 사용자 방은 미노출 확인 (교차 오염 방지)

- [x] **Task 6:** Orval 재생성 + api-client 업데이트
  - [x] API 서버 기동 후 `openapi.json` 덤프 → `pnpm orval`
  - [x] `useListChatRooms` 훅 생성 확인 (`packages/api-client/src/generated/chat-rooms/chat-rooms.ts`)
  - [x] `ChatRoomListItem`, `PageChatRoomListItem` 타입 생성 확인
  - [x] `packages/api-client/src/index.ts` — Story 4.4에서 이미 `export * from './generated/chat-rooms/chat-rooms'` 추가됨 → 변경 불필요

- [x] **Task 7:** `apps/user-web/src/app/chat/page.tsx` 신규 생성
  - [x] `useListChatRooms` 훅으로 채팅방 목록 fetch
  - [x] cursor 기반 "더 보기" 패턴 (quotes 페이지와 동일)
  - [x] 상대방 `counterpartDisplayName` + `serviceRequest.description` 표시
  - [x] 항목 클릭 → `router.push('/chat/${room.id}')`
  - [x] `useReadMe()` 실패 시 `/login` 리다이렉트
  - [x] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과

### Review Findings

- [x] [Review][Patch] `next_cursor` 계산 전 빈 배열 조기 반환 순서 오류 [`apps/api/app/services/chat.py:73`]
- [x] [Review][Patch] `test_ac3_service_request_fields` — `categoryId` 포함 여부 미검증 [`apps/api/tests/test_chat_rooms_list.py:101`]
- [x] [Review][Patch] `test_ac3_no_email_in_response` — 이메일 노출 검사 패턴 부정확 [`apps/api/tests/test_chat_rooms_list.py:115`]
- [x] [Review][Defer] React StrictMode 이중 실행 시 `processedCursors` 첫 페이지 유실 [`apps/user-web/src/app/chat/page.tsx`] — deferred, pre-existing
- [x] [Review][Defer] 백그라운드 refetch 시 `processedCursors`가 최신 데이터 갱신 차단 [`apps/user-web/src/app/chat/page.tsx`] — deferred, pre-existing
- [x] [Review][Defer] 컴포넌트 unmount/remount 중 inflight fetch 경쟁 조건 [`apps/user-web/src/app/chat/page.tsx`] — deferred, pre-existing

---

## 개발자 노트

### 1. 스키마 설계 — `ChatRoomListItem` vs `ChatRoomRead`

기존 `ChatRoomRead` 는 순수 FK(UUID)만 반환하는 단순 스키마다. 이번 스토리에서는
`counterpart_display_name` 과 `service_request` 임베딩이 필요하므로 **별도 스키마**를 추가한다.
`ChatRoomRead` 는 수정하지 않는다.

```python
# apps/api/app/schemas/chat_room.py — 기존 ChatRoomRead 아래에 추가
from datetime import datetime
import uuid
from typing import Optional

from app.schemas.base import CamelModel
from app.schemas.service_request import ServiceRequestSummary


class ChatRoomListItem(CamelModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    created_at: datetime
    counterpart_display_name: str
    service_request: Optional[ServiceRequestSummary] = None


class PageChatRoomListItem(CamelModel):
    items: list[ChatRoomListItem]
    next_cursor: Optional[uuid.UUID] = None
```

`service_request` 를 `Optional` 로 선언하는 이유: 요청이 소프트 삭제된 경우 `list_by_ids` 에서
미반환될 수 있다. `QuoteListItem.service_request` 와 동일한 패턴 (`schemas/quote.py:51`).

---

### 2. `ChatRoomRepository.list_mine()` 구현

기존 레포지터리 keyset cursor 패턴과 동일: `id < after_id` + `ORDER BY id DESC` + `LIMIT`.

```python
# apps/api/app/repositories/chat_rooms.py — get_by_id() 아래에 추가
from sqlalchemy import select

async def list_mine(
    self,
    user_id: uuid.UUID,
    role: str,        # "customer" | "pro"
    after_id: uuid.UUID | None,
    limit: int = 20,
) -> list[ChatRoom]:
    if role == "customer":
        stmt = select(ChatRoom).where(ChatRoom.customer_id == user_id)
    else:
        stmt = select(ChatRoom).where(ChatRoom.pro_id == user_id)
    if after_id is not None:
        stmt = stmt.where(ChatRoom.id < after_id)
    stmt = stmt.order_by(ChatRoom.id.desc()).limit(limit)
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

**ADMIN 처리:** ADMIN의 `user_role.value` 는 `"admin"` 이므로 `else` 분기(pro 기준)에 걸려
본인이 `pro_id` 인 방만 조회한다. ADMIN 은 실제 채팅방 참여자가 아니므로 자연스럽게 빈 목록
반환. 별도 403 처리 불필요.

**`ChatRoom` 에 소프트 삭제 없음:** `ChatRoom` 은 `SoftDeleteMixin` 을 상속하지 않는다
(`base.py` 의 `UUIDPrimaryKeyMixin` + `TimestampMixin` 만 상속). `deleted_at IS NULL` 필터
불필요.

---

### 3. `ChatService.list_my_chat_rooms()` 구현

`QuoteService.list_mine()` 패턴과 동일: LIMIT+1 조회 → has_more → next_cursor.

```python
# apps/api/app/services/chat.py — 기존 import에 추가
from app.repositories.users import UserRepository
from app.repositories.service_requests import ServiceRequestRepository
from app.schemas.chat_room import ChatRoomListItem, PageChatRoomListItem
from app.schemas.service_request import ServiceRequestSummary

# ChatService 클래스 내에 추가
async def list_my_chat_rooms(
    self,
    current_user: User,
    cursor: uuid.UUID | None,
) -> PageChatRoomListItem:
    LIMIT = 20
    rooms = await self.chat_room_repo.list_mine(
        current_user.id,
        current_user.user_role.value,
        cursor,
        LIMIT + 1,
    )
    has_more = len(rooms) > LIMIT
    if has_more:
        rooms = rooms[:LIMIT]
    next_cursor = rooms[-1].id if has_more else None

    if not rooms:
        return PageChatRoomListItem(items=[], next_cursor=None)

    user_repo = UserRepository(self.session)
    sr_repo = ServiceRequestRepository(self.session)

    is_customer = current_user.user_role.value == "customer"
    counterpart_ids = [r.pro_id if is_customer else r.customer_id for r in rooms]
    sr_ids = [r.service_request_id for r in rooms]

    counterparts = {
        u.id: u for u in await user_repo.list_by_ids(counterpart_ids)
    }
    srs = {
        sr.id: sr for sr in await sr_repo.list_by_ids(sr_ids)
    }

    items = []
    for room in rooms:
        cp_id = room.pro_id if is_customer else room.customer_id
        cp = counterparts.get(cp_id)
        sr = srs.get(room.service_request_id)
        items.append(ChatRoomListItem(
            id=room.id,
            service_request_id=room.service_request_id,
            created_at=room.created_at,
            counterpart_display_name=cp.display_name if cp else "알 수 없음",
            service_request=ServiceRequestSummary.model_validate(sr) if sr else None,
        ))

    return PageChatRoomListItem(items=items, next_cursor=next_cursor)
```

**`UserRepository` / `ServiceRequestRepository` 기존 메서드 확인:**
- `UserRepository.list_by_ids(ids: list[UUID])` — `repositories/users.py` 에 존재 ✅
- `ServiceRequestRepository.list_by_ids(ids: list[UUID])` — `repositories/service_requests.py:72` 에 존재 ✅

**`ServiceRequestSummary.model_validate(sr)`:** `ServiceRequestSummary` 는 `CamelModel` 상속,
`model_config = ConfigDict(from_attributes=True)` 설정되어 있어 ORM 객체 직접 변환 가능.
이미 `QuoteListItem` 조립에서 검증된 패턴 (`services/quote.py`).

---

### 4. 라우터 추가

```python
# apps/api/app/routers/chat.py — 기존 import에 추가
from app.schemas.chat_room import PageChatRoomListItem

# 기존 라우터 엔드포인트들 위에 추가 (prefix 순서상 "" 경로가 먼저 와야 함)
@router.get("", response_model=PageChatRoomListItem, status_code=200)
async def list_chat_rooms(
    current_user: CurrentUser,
    mine: bool = Query(default=True),
    cursor: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_db),
) -> PageChatRoomListItem:
    svc = ChatService(session)
    return await svc.list_my_chat_rooms(current_user, cursor)
```

**`Query` import 추가 필요:** `from fastapi import APIRouter, Depends, Query`

**`mine` 파라미터:** 에픽 스펙 준수용으로 선언하되 값은 무시 (항상 현재 사용자 기준 필터링).
향후 admin 전체 조회 등 확장 여지 유지.

**operationId 예측:**
```
함수명: list_chat_rooms
FastAPI operationId: list_chat_rooms_api_v1_chat_rooms_get
orval.config.ts 정규식 제거 후: list_chat_rooms
Orval camelCase: useListChatRooms / listChatRooms
생성 파일: packages/api-client/src/generated/chat-rooms/chat-rooms.ts
생성 타입 파일:
  packages/api-client/src/generated/model/chatRoomListItem.ts
  packages/api-client/src/generated/model/pageChatRoomListItem.ts
  packages/api-client/src/generated/model/pageChatRoomListItemNextCursor.ts
  packages/api-client/src/generated/model/listChatRoomsParams.ts
```

**라우터 엔드포인트 순서 주의:** `GET ""` 경로를 `GET "/{chat_room_id}/messages"` 보다
먼저 등록해야 FastAPI 라우팅이 올바르게 동작한다. 파일 상단부에 배치할 것.

---

### 5. 테스트 헬퍼 패턴

`tests/helpers.py` 의 기존 헬퍼 재사용:
- `_make_customer`, `_make_pro`, `_make_admin`
- `_make_category`, `_make_service_request`, `_make_quote`
- `_auth(user)`

**채팅방 생성 헬퍼 (Story 4.4 교훈):** `tests/helpers.py` 에 이미 `_make_chat_room` 이
추가됐는지 확인 후 없으면 테스트 파일 내에 로컬 정의:

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

**페이지네이션 테스트 패턴 (21개 생성):**
```python
for i in range(21):
    q = await _make_quote(db, pro, sr)
    await db.execute(update(Quote).where(Quote.id == q.id).values(status="accepted"))
    await _make_chat_room(db, customer, pro, sr, q)
    # 별개의 service_request 필요 (quote unique 제약)
```

주의: `chat_rooms.quote_id` 에 UNIQUE 제약 (`uq_quotes_accepted_per_request`)이 있으므로
21개 채팅방 생성 시 서로 다른 서비스 요청+견적 조합이 필요하다. 루프 안에서 `_make_service_request`, `_make_quote` 를 함께 호출할 것.

---

### 6. Orval 재생성 후 확인

Story 4.4에서 `packages/api-client/src/index.ts` 에 이미:
```typescript
export * from './generated/chat-rooms/chat-rooms';
```
가 추가되어 있다. 이번 스토리에서 Orval 재생성 시 동일 파일(`chat-rooms.ts`)에 `useListChatRooms` 가 추가되므로 `index.ts` 수동 수정 불필요.

생성 후 확인해야 할 훅 시그니처 (실제 생성물 기준으로 프론트엔드 코드 작성):
```typescript
// 예상 (실제 생성물 확인 필수)
export const useListChatRooms = <TData = ..., TError = unknown>(
  params?: ListChatRoomsParams,
  options?: ...
): UseQueryResult<TData, TError>
```

---

### 7. user-web `chat/page.tsx` 구현 패턴

`(pro)/quotes/page.tsx` 의 cursor pagination 패턴을 그대로 재사용:

```tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useReadMe, useListChatRooms, type ChatRoomListItem } from "@gosoom/api-client";

export default function ChatListPage() {
  const router = useRouter();
  const { data: me, isError: meError } = useReadMe();
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allRooms, setAllRooms] = useState<ChatRoomListItem[]>([]);
  const processedCursors = useRef(new Set<string>());

  useEffect(() => {
    if (meError) router.push("/login");
  }, [meError, router]);

  const { data, isFetching } = useListChatRooms({ mine: true, cursor });

  useEffect(() => {
    if (isFetching || !data?.items) return;
    const key = cursor ?? "__initial__";
    if (processedCursors.current.has(key)) return;
    processedCursors.current.add(key);
    setAllRooms((prev) =>
      cursor === undefined ? data.items : [...prev, ...data.items]
    );
  }, [data, cursor, isFetching]);

  return (
    <div className="max-w-2xl mx-auto p-4">
      <h1 className="text-xl font-bold mb-4">채팅 목록</h1>
      <ul className="space-y-2">
        {allRooms.map((room) => (
          <li
            key={room.id}
            onClick={() => router.push(`/chat/${room.id}`)}
            className="border rounded-lg p-4 cursor-pointer hover:bg-gray-50"
          >
            <p className="font-medium">{room.counterpartDisplayName}</p>
            {room.serviceRequest && (
              <p className="text-sm text-gray-600 mt-1 truncate">
                {room.serviceRequest.description}
              </p>
            )}
          </li>
        ))}
      </ul>
      {data?.nextCursor && (
        <button
          onClick={() => setCursor(data.nextCursor!)}
          disabled={isFetching}
          className="mt-4 w-full py-2 border rounded-lg text-sm disabled:opacity-50"
        >
          {isFetching ? "로딩 중…" : "더 보기"}
        </button>
      )}
      {!isFetching && allRooms.length === 0 && (
        <p className="text-center text-gray-500 mt-8">
          참여 중인 채팅방이 없습니다.
        </p>
      )}
    </div>
  );
}
```

**`useListChatRooms` 파라미터 타입 확인 필수:** `ListChatRoomsParams.cursor` 가 `string`
인지 `string | null` 인지는 생성된 `listChatRoomsParams.ts` 파일로 확인 후 조정.
`undefined` 를 넘기면 쿼리 파라미터가 생략되므로 일반적으로 안전하다.

---

### 알려진 함정

#### 1. `GET ""` 라우터 순서 ⚠️

`router = APIRouter(prefix="/api/v1/chat-rooms", ...)` 에서 `GET ""` 경로와
`GET "/{chat_room_id}/messages"` 경로가 공존한다.
FastAPI는 정의 순서대로 매칭하므로 `GET ""` 을 **반드시 먼저** 등록해야 한다.
순서를 바꾸면 `GET /api/v1/chat-rooms?mine=true` 요청이 `/{chat_room_id}/messages`
에 잘못 라우팅될 수 있다.

#### 2. `ChatRoom` 에 `SoftDeleteMixin` 없음 ✅

`ChatRoom` 모델은 `UUIDPrimaryKeyMixin` + `TimestampMixin` 만 상속한다.
`deleted_at IS NULL` 필터가 없어야 정상이다. 다른 레포지터리에서 복붙 시 필터 추가 주의.

#### 3. 페이지네이션 테스트 — `quote_id` UNIQUE 제약 ⚠️

`chat_rooms.quote_id` 에 UNIQUE 제약이 있다. 21개 채팅방 생성 테스트에서는
각 채팅방마다 다른 `quote_id` 가 필요하다. 루프에서 `_make_service_request()` +
`_make_quote()` + `_make_chat_room()` 세 헬퍼를 함께 호출할 것. 동일 `quote_id` 로
2개 이상 채팅방 생성 시도 시 `IntegrityError` 발생.

#### 4. Orval `nextCursor` 타입 — `string | null` vs `uuid` ⚠️

Python 스키마: `next_cursor: Optional[uuid.UUID] = None`
JSON 직렬화: UUID는 `string` 으로 직렬화됨 → OpenAPI 스펙에서 `type: string, format: uuid`
Orval 생성 TypeScript 타입: `nextCursor?: string | null`

프론트에서 `data.nextCursor` 를 `setCursor()` 에 전달할 때 `null | undefined` 조심:
```tsx
setCursor(data.nextCursor ?? undefined);
// data.nextCursor!  ← non-null assertion 사용 시 타입 불일치 가능 → setCursor(data.nextCursor ?? undefined) 권장
```

#### 5. `counterpart_display_name` — 삭제된 사용자 처리 ✅

`user_repo.list_by_ids()` 는 `deleted_at IS NULL` 필터를 적용한다.
탈퇴한 상대방은 `counterparts.get(cp_id)` 에서 `None` 반환 → `"알 수 없음"` 폴백.
MVP 수준에서 허용.

#### 6. `processedCursors.current.has(key)` 초기 렌더 패턴 ⚠️

`key = cursor ?? "__initial__"` 에서 `"__initial__"` 은 실제 cursor 값과 충돌하지 않는
sentinel 이다 (UUID 형식 아님). `cursor === undefined` 로 초기화 시 중복 처리 방지.
quotes 페이지 동일 패턴 (`(pro)/quotes/page.tsx`) — 검증된 패턴.

#### 7. `useListChatRooms` 훅 훅 파라미터 확인 ⚠️

Orval 생성 훅의 파라미터 구조(필수/선택 여부, 파라미터 이름)는 생성된 파일에서 반드시 확인
후 사용. `useListMyQuotes`, `useListChatRooms` 등은 Orval이 OpenAPI query param 기준으로
자동 생성하므로 스키마가 바뀌면 훅 시그니처도 바뀐다.

---

## 파일 구조 요약

### 신규 파일 (NEW)

```
apps/api/tests/test_chat_rooms_list.py          # pytest 채팅방 목록 테스트
apps/user-web/src/app/chat/page.tsx             # 채팅방 목록 화면
packages/api-client/src/generated/model/chatRoomListItem.ts
packages/api-client/src/generated/model/pageChatRoomListItem.ts
packages/api-client/src/generated/model/pageChatRoomListItemNextCursor.ts  (Orval 자동, 있을 수 있음)
packages/api-client/src/generated/model/listChatRoomsParams.ts
```

### 수정 파일 (UPDATE)

```
apps/api/app/schemas/chat_room.py               # ChatRoomListItem, PageChatRoomListItem 추가
apps/api/app/repositories/chat_rooms.py         # list_mine() 메서드 추가
apps/api/app/services/chat.py                   # list_my_chat_rooms() 메서드, import 추가
apps/api/app/routers/chat.py                    # GET /api/v1/chat-rooms 엔드포인트 추가, Query import 추가
openapi.json                                    # API 스펙 갱신 (Orval 입력)
packages/api-client/src/generated/chat-rooms/chat-rooms.ts  # useListChatRooms 훅 추가 (Orval 자동)
packages/api-client/src/generated/model/index.ts            # 새 타입 export (Orval 자동)
_bmad-output/implementation-artifacts/sprint-status.yaml    # 4-5 상태 업데이트
```

### 수정 없는 파일 (NO CHANGE)

```
apps/api/app/models/chat_room.py                # 변경 없음
apps/api/app/schemas/chat_room.py               # ChatRoomRead 는 변경 없음 (새 스키마만 추가)
apps/api/app/core/exceptions.py                 # ChatRoomNotFoundError 이미 존재
apps/api/app/repositories/users.py              # list_by_ids() 이미 존재
apps/api/app/repositories/service_requests.py   # list_by_ids() 이미 존재
packages/api-client/src/index.ts                # chat-rooms re-export 이미 Story 4.4에서 추가됨
```

---

## 수동 체크포인트 (⚡)

**신규 환경변수 없음.** Railway/Supabase 설정 변경 없음.
**신규 Alembic 마이그레이션 없음.** DB 스키마 변경 없음.

**필수 수동 작업:**
1. API 서버 기동 후 `openapi.json` 덤프: `python -c "import json; from app.main import app; print(json.dumps(app.openapi()))" > openapi.json`
   또는 서버 실행 후 `curl http://localhost:8000/openapi.json > openapi.json`
2. `pnpm orval` 실행 → 생성물 확인

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `pytest apps/api/tests/test_chat_rooms_list.py` — 모든 케이스 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과 (apps/user-web)
- [ ] Orval 생성물 커밋 포함 (`ChatRoomListItem`, `PageChatRoomListItem`, `useListChatRooms`)
- [ ] user-web `chat/` 채팅 목록 화면 동작 확인:
  - CUSTOMER 로그인 → 채팅 목록 접근 → 본인 채팅방만 표시
  - PRO 로그인 → 채팅 목록 접근 → 본인 채팅방만 표시
  - 항목 클릭 → `/chat/[id]` 이동 확인
  - 21개 초과 시 "더 보기" 버튼 동작 확인

---

## 이전 스토리 인텔리전스 (Story 4.4 교훈)

1. **`CamelModel.from_attributes=True` 자동 처리:** `response_model` 이 ORM → Pydantic 변환 처리. `model_validate()` 명시 불필요. 단, Python 레벨 조립(`ChatRoomListItem(...)`) 시에는 ORM 객체가 아니므로 `model_validate` 불필요.

2. **`main.py` 에 이미 `chat_router` 등록됨 (Story 4.4):** 이번 스토리에서 `main.py` 변경 불필요. 기존 `chat_router` 에 새 엔드포인트만 추가하면 된다.

3. **`packages/api-client/src/index.ts` 수동 업데이트 불필요 (이번 스토리):** Story 4.4에서 `export * from './generated/chat-rooms/chat-rooms'` 가 이미 추가됨. Orval 재생성 시 동일 파일에 `useListChatRooms` 가 자동 추가된다.

4. **`react-hooks/set-state-in-effect` 린트 규칙:** `useEffect` 내 `setState` 호출은 ESLint 경고를 발생시킨다. 이번 스토리에서는 메시지 폴링이 아닌 단순 목록 로드이므로 `useReducer` 없이 `useState` + `useEffect` 조합으로 충분하다. quotes 페이지 패턴 그대로 적용.

5. **`useListChatRooms` 는 폴링 불필요:** 채팅 목록은 실시간 갱신이 필요 없다. `refetchInterval` 없음. 사용자가 "더 보기" 버튼을 클릭하거나 페이지 포커스 복귀 시 TanStack Query 기본 `staleTime=0` 으로 자동 갱신.

---

## Dev Agent Record

### Completion Notes

- Task 1: `ChatRoomListItem` + `PageChatRoomListItem` 스키마를 `schemas/chat_room.py`에 추가. `ChatRoomRead`는 변경 없이 기존 스키마 하단에 신규 스키마 추가.
- Task 2: `ChatRoomRepository.list_mine()` — 역할별 필터(`customer_id` 또는 `pro_id`), keyset cursor(`id < after_id`), `ORDER BY id DESC`, `LIMIT` 구현.
- Task 3: `ChatService.list_my_chat_rooms()` — LIMIT+1 패턴으로 `next_cursor` 계산. `UserRepository.list_by_ids()`, `ServiceRequestRepository.list_by_ids()` 배치 조회로 상대방 displayName·서비스 요청 조립.
- Task 4: `GET /api/v1/chat-rooms` 엔드포인트를 `routers/chat.py` 상단에 추가. `GET ""` 경로가 `GET /{id}/messages`보다 먼저 등록되어 라우팅 충돌 없음.
- Task 5: 9개 테스트 작성·통과 (AC1~5 + 교차 오염 방지). Story 4.4 기존 버그(`MessageRepository.list_after`에서 `created_at.desc()` 비결정적 정렬) 부수 수정: `id.desc()`로 교체해 전체 221개 테스트 통과.
- Task 6: 루트 `openapi.json` 재생성 후 `pnpm orval` 실행. `useListChatRooms`, `ChatRoomListItem`, `PageChatRoomListItem`, `pageChatRoomListItemNextCursor`, `listChatRoomsParams` 생성 확인.
- Task 7: `apps/user-web/src/app/chat/page.tsx` — quotes 페이지 cursor 패턴 재사용. `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과. `/chat` 라우트 정적 페이지로 빌드됨.

### File List

**신규 파일 (NEW)**
- `apps/api/tests/test_chat_rooms_list.py`
- `apps/user-web/src/app/chat/page.tsx`
- `packages/api-client/src/generated/model/chatRoomListItem.ts`
- `packages/api-client/src/generated/model/chatRoomListItemServiceRequest.ts`
- `packages/api-client/src/generated/model/pageChatRoomListItem.ts`
- `packages/api-client/src/generated/model/pageChatRoomListItemNextCursor.ts`
- `packages/api-client/src/generated/model/listChatRoomsParams.ts`

**수정 파일 (UPDATE)**
- `apps/api/app/schemas/chat_room.py`
- `apps/api/app/repositories/chat_rooms.py`
- `apps/api/app/repositories/messages.py` (Story 4.4 버그 수정: `created_at.desc()` → `id.desc()`)
- `apps/api/app/services/chat.py`
- `apps/api/app/routers/chat.py`
- `openapi.json` (루트)
- `packages/api-client/src/generated/chat-rooms/chat-rooms.ts`
- `packages/api-client/src/generated/model/index.ts`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-06-11: Story 4.5 스토리 파일 작성 완료
- 2026-06-11: Story 4.5 구현 완료 — 채팅방 목록 API + user-web 페이지 + Orval 재생성
