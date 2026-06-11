---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 4.2: 견적 수락 & 채팅방 생성

- **Status:** done
- **Epic:** 4 — 매칭 & 채팅 (거래 루프 완결) (FR8, FR13-18)
- **Story ID / Key:** 4-2 / 4-2-accept-quote-create-chatroom
- **작성일:** 2026-06-10

---

## 사용자 스토리

As a 로그인한 고객(CUSTOMER),
내 요청에 들어온 견적 중 하나를 수락하고 싶다.
So that 선택한 고수와 채팅방이 만들어져 거래 세부사항을 바로 조율할 수 있다.

---

## 인수 기준 (BDD)

**AC1** — 단일 트랜잭션 원자적 수락 (FR13)

- **Given** 본인 `open` 요청의 `pending` 견적이 있을 때
- **When** 고객이 `POST /api/v1/quotes/{id}/accept`를 호출하면
- **Then** 단일 트랜잭션 안에서:
  - ① 서비스 요청 상태가 `open` → `matched` 로 전환
  - ② 해당 고객-고수 간 `chat_room`이 생성(`service_request_id`, `customer_id`, `pro_id`, `quote_id`)
  - ③ 수락된 견적이 `pending` → `accepted` 로 전환
  - ④ 같은 요청의 **나머지 `pending` 견적**이 모두 `closed` 로 전환
- **And** 응답으로 생성된 채팅방 정보(`chatRoomId` 포함)가 반환된다

**AC2** — 동시 수락 race 차단 (AR7, NFR7)

- **Given** 두 요청이 동시에 같은 요청의 서로 다른 견적을 수락하려 할 때
- **When** accept 트랜잭션이 실행되면
- **Then** `SELECT ... FOR UPDATE`로 요청 행이 잠기고
- **And** `uq_quotes_accepted_per_request` partial unique index가 두 번째 수락을 거부하여
- **And** 요청당 정확히 하나의 견적만 수락된다

**AC3** — 거부 케이스 (원자성 보장)

- **Given** 이미 `matched` 상태인 요청의 견적을 수락하려 할 때
- **Then** 409 `service_request_already_matched` 반환, 어떤 상태도 변경되지 않음
- **Given** 본인 요청이 아닌 견적을 수락하려 할 때
- **Then** 403 `forbidden` 반환
- **Given** 견적이 `pending` 상태가 아닐 때 (`accepted`/`rejected`/`closed`)
- **Then** 409 `quote_not_pending` 반환
- **Given** 견적 id가 존재하지 않을 때
- **Then** 404 `quote_not_found` 반환

**AC4** — 권한 제어

- **Then** 비인증 요청 → 401 `not_authenticated`
- **Then** PRO 역할 → 403 `forbidden`
- **Then** ADMIN 역할 → 403 `forbidden`

**AC5** — user-web 요청 상세 화면

- **Given** Story 4.1에서 비활성화(`disabled`) 상태로 렌더링된 수락/거절 버튼이 있을 때
- **When** 고객이 "수락하기" 버튼을 클릭하면
- **Then** `POST /api/v1/quotes/{id}/accept` 가 호출되고
- **And** 성공 시 요청·견적·채팅방 관련 TanStack Query 캐시가 무효화·갱신되며
- **And** 고객이 새 채팅방 페이지(`/chat/{chatRoomId}`)로 이동한다
- **And** 처리 중에는 버튼이 `disabled` + 로딩 텍스트로 표시된다
- **And** 에러 시 에러 메시지가 표시된다

---

## 태스크 및 서브태스크

- [x] **Task 1:** Alembic 마이그레이션 — `chat_rooms` 테이블 + `uq_quotes_accepted_per_request` index
  - [x] `apps/api/alembic/versions/<rev>_add_chat_rooms_table.py` 신규 생성
  - [x] `chat_rooms` 테이블: `id UUID PK`, `service_request_id FK`, `customer_id FK`, `pro_id FK`, `quote_id FK`, `created_at`
  - [x] `uq_quotes_accepted_per_request` partial unique index: `quotes(service_request_id) WHERE status='accepted' AND deleted_at IS NULL`
  - [x] downgrade: `chat_rooms` drop, index drop

- [x] **Task 2:** `ChatRoom` ORM 모델 신규 생성
  - [x] `apps/api/app/models/chat_room.py` 신규 생성
  - [x] `UUIDPrimaryKeyMixin` + `created_at` 직접 정의 (에픽 스펙: `id`, `service_request_id`, `customer_id`, `pro_id`, `quote_id`, `created_at` 만 정의)
  - [x] `apps/api/app/models/__init__.py` — `ChatRoom` import 추가

- [x] **Task 3:** `ChatRoomRepository` 신규 생성
  - [x] `apps/api/app/repositories/chat_rooms.py` 신규 생성
  - [x] `create(obj: ChatRoom) -> ChatRoom` 메서드 (flush/refresh, commit은 service에서)

- [x] **Task 4:** `ServiceRequestRepository.get_by_id_for_update()` 추가
  - [x] `apps/api/app/repositories/service_requests.py` 수정
  - [x] `SELECT ... FOR UPDATE` (`with_for_update()`) + `deleted_at IS NULL`

- [x] **Task 5:** `QuoteRepository.close_pending_except()` 추가
  - [x] `apps/api/app/repositories/quotes.py` 수정
  - [x] `UPDATE quotes SET status='closed' WHERE service_request_id=? AND status='pending' AND id!=? AND deleted_at IS NULL`
  - [x] SQLAlchemy `update()` bulk 방식 (`execution_options(synchronize_session=False)`)

- [x] **Task 6:** 신규 예외 3개 추가
  - [x] `apps/api/app/core/exceptions.py` 수정
  - [x] `QuoteNotFoundError` (404, `quote_not_found`)
  - [x] `QuoteNotPendingError` (409, `quote_not_pending`)
  - [x] `ServiceRequestAlreadyMatchedError` (409, `service_request_already_matched`)

- [x] **Task 7:** `ChatRoomRead` Pydantic 스키마 신규 생성
  - [x] `apps/api/app/schemas/chat_room.py` 신규 생성
  - [x] `ChatRoomRead(CamelModel)`: `id`, `serviceRequestId`, `customerId`, `proId`, `quoteId`, `createdAt`

- [x] **Task 8:** `QuoteService.accept()` 구현
  - [x] `apps/api/app/services/quote.py` 수정
  - [x] 단일 트랜잭션 원자적 처리 (AC1 4단계 + IntegrityError race 차단)
  - [x] `ChatRoomRepository` + `ServiceRequestRepository.get_by_id_for_update` 활용

- [x] **Task 9:** 라우터에 `POST /{quote_id}/accept` 엔드포인트 추가
  - [x] `apps/api/app/routers/quotes.py` 수정
  - [x] `_q_router.post("/{quote_id}/accept", ...)` — CUSTOMER 역할 한정

- [x] **Task 10:** pytest 작성 (`apps/api/tests/test_quotes_accept.py`)
  - [x] AC1 수락 성공: 200, chat_room 생성, sr→matched, 수락 견적→accepted, 나머지 pending→closed
  - [x] AC1 타 pending 견적 closed 전환 확인
  - [x] AC3 이미 matched 요청 → 409 `service_request_already_matched`
  - [x] AC3 소유권: 타 고객 견적 수락 → 403
  - [x] AC3 견적 not pending → 409 `quote_not_pending` (`rejected` 견적으로 테스트)
  - [x] AC3 존재하지 않는 견적 → 404 `quote_not_found`
  - [x] AC4 비인증 → 401
  - [x] AC4 PRO → 403
  - [x] AC4 ADMIN → 403

- [x] **Task 11:** Orval 재생성 + api-client 확인
  - [x] API 서버 기동 후 `openapi.json` 덤프 → `pnpm orval`
  - [x] `useAcceptQuote` 훅 생성 확인 (`_q_router.post("/{quote_id}/accept")`)
  - [x] `ChatRoomRead` 타입 생성 확인

- [x] **Task 12:** user-web `(customer)/requests/[id]/page.tsx` 수락 버튼 활성화
  - [x] `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` 수정
  - [x] `useAcceptQuote` mutation 훅 추가
  - [x] "수락하기" 버튼 `disabled` 해제, `onClick` 핸들러 배선
  - [x] 수락 성공 후 캐시 무효화 + `/chat/{chatRoomId}` 라우팅
  - [x] 처리 중 버튼 `disabled` + 에러 메시지 표시

---

## 개발자 노트

### 핵심 설계 결정

#### 1. 엔드포인트 위치 — `_q_router` (quotes.py)

`POST /api/v1/quotes/{quote_id}/accept`는 **`_q_router`** (`/api/v1/quotes`)에 추가한다.

```python
# routers/quotes.py — _q_router에 추가
@_q_router.post("/{quote_id}/accept", response_model=ChatRoomRead, status_code=200)
async def accept_quote(
    quote_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ChatRoomRead:
    svc = QuoteService(session)
    return await svc.accept(quote_id, current_user)
```

**이유:** `GET /api/v1/quotes` (내 견적 목록, `_q_router`)와 동일 네임스페이스. 견적 ID를 path param으로 받는 견적 액션이므로 `_q_router`가 자연스러운 위치. `main.py` 변경 불필요 — `quotes_router`는 이미 등록됨.

**operationId 예측:**
```
함수명: accept_quote
FastAPI operationId: accept_quote_api_v1_quotes__quote_id__accept_post
orval.config.ts 정규식 제거 후: accept_quote
Orval camelCase 변환: useAcceptQuote
생성 파일: packages/api-client/src/generated/quotes/quotes.ts
```

#### 2. 단일 트랜잭션 구현 패턴 (AR7)

```python
# services/quote.py — accept() 추가
async def accept(self, quote_id: UUID, current_user: User) -> ChatRoom:
    # 1. 견적 조회 (존재 확인)
    quote = await self.quote_repo.get_by_id(quote_id)
    if quote is None:
        raise QuoteNotFoundError()

    # 2. 서비스 요청 행 잠금 (SELECT ... FOR UPDATE) — race 차단
    request = await self.sr_repo.get_by_id_for_update(quote.service_request_id)
    if request is None:
        raise ServiceRequestNotFoundError()

    # 3. 소유권 검사 — 본인 요청의 견적만
    if request.customer_id != current_user.id:
        raise ForbiddenError()

    # 4. 요청 상태 검사
    if request.status != ServiceRequestStatus.OPEN:
        raise ServiceRequestAlreadyMatchedError()

    # 5. 견적 상태 검사
    if quote.status != QuoteStatus.PENDING:
        raise QuoteNotPendingError()

    # 6. ① 요청 → matched
    request.status = ServiceRequestStatus.MATCHED

    # 7. ② 채팅방 생성
    chat_room = ChatRoom(
        service_request_id=quote.service_request_id,
        customer_id=request.customer_id,
        pro_id=quote.pro_id,
        quote_id=quote.id,
    )
    chat_room_repo = ChatRoomRepository(self.session)
    self.session.add(chat_room)

    # 8. ③ 수락 견적 → accepted
    quote.status = QuoteStatus.ACCEPTED

    # 9. ④ 나머지 pending 견적 → closed (bulk update)
    await self.quote_repo.close_pending_except(quote.service_request_id, quote.id)

    # 10. flush → partial unique index 검증 (concurrent accept 차단) → commit
    try:
        await self.session.flush()
        await self.session.refresh(chat_room)
        await self.session.commit()
    except IntegrityError:
        await self.session.rollback()
        raise ServiceRequestAlreadyMatchedError()

    return chat_room
```

**⚠️ flush 순서 주의:** `close_pending_except` (bulk UPDATE)는 반드시 `flush()` **전에** 실행한다. flush 후 bulk update는 이미 flush된 세션 내 객체와 DB 상태 불일치를 일으킬 수 있음.

**⚠️ `synchronize_session=False` 필수:** bulk update는 ORM 세션 캐시를 자동 갱신하지 않는다. 세션 내 Quote 객체의 `status`가 stale 상태로 남을 수 있으나, 이 메서드에서 그 객체를 다시 읽지 않으므로 안전.

#### 3. `SELECT ... FOR UPDATE` 구현

```python
# repositories/service_requests.py — 추가
async def get_by_id_for_update(self, id: uuid.UUID) -> ServiceRequest | None:
    """FR13 동시 수락 race 차단: 요청 행 비관적 잠금."""
    result = await self.session.execute(
        select(ServiceRequest)
        .where(
            ServiceRequest.id == id,
            ServiceRequest.deleted_at.is_(None),
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()
```

#### 4. `close_pending_except` bulk UPDATE

```python
# repositories/quotes.py — 추가
from sqlalchemy import update as sa_update

async def close_pending_except(
    self, request_id: uuid.UUID, exclude_quote_id: uuid.UUID
) -> None:
    """해당 요청의 현재 견적 제외 pending 견적을 bulk closed로 전환."""
    await self.session.execute(
        sa_update(Quote)
        .where(
            Quote.service_request_id == request_id,
            Quote.status == QuoteStatus.PENDING,
            Quote.id != exclude_quote_id,
            Quote.deleted_at.is_(None),
        )
        .values(status=QuoteStatus.CLOSED)
        .execution_options(synchronize_session=False)
    )
```

**`sa_update` alias 이유:** `from sqlalchemy import update`는 Python 내장 `update` dict 메서드와 충돌 가능성이 있음. `sa_update`로 alias.

#### 5. `ChatRoom` 모델 설계

에픽 스펙: `chat_rooms (id UUIDv7, service_request_id FK, customer_id FK, pro_id FK, quote_id FK, created_at)`.

`updated_at`과 `deleted_at`은 스펙에 없음 — `UUIDPrimaryKeyMixin`만 사용하고 `created_at`을 직접 정의한다. 채팅방은 생성 후 내용이 변경되지 않는 불변 레코드.

```python
# models/chat_room.py 신규
import uuid as _uuid
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import DateTime, func

from app.models.base import Base, UUIDPrimaryKeyMixin


class ChatRoom(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "chat_rooms"

    service_request_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("service_requests.id"), nullable=False, index=True
    )
    customer_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False, index=True
    )
    pro_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False, index=True
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
```

**`quote_id` unique 제약:** 견적 1개당 채팅방 1개 — DB 레벨 강제.
**`service_request_id` FK ondelete:** 서비스 요청은 소프트삭제이므로 RESTRICT(기본값) — 데이터 보존(FR22).

#### 6. `ChatRoomRead` 스키마

```python
# schemas/chat_room.py 신규
import uuid
from datetime import datetime

from app.schemas.base import CamelModel  # 프로젝트 표준 (schemas/quote.py 동일 패턴)


class ChatRoomRead(CamelModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    customer_id: uuid.UUID
    pro_id: uuid.UUID
    quote_id: uuid.UUID
    created_at: datetime
```

#### 7. `uq_quotes_accepted_per_request` partial unique index (AR7)

```python
# 마이그레이션 내 quotes 테이블에 index 추가
op.create_index(
    'uq_quotes_accepted_per_request',
    'quotes',
    ['service_request_id'],
    unique=True,
    postgresql_where=sa.text("status = 'accepted' AND deleted_at IS NULL"),
)
```

**이 index의 역할:** race condition에서 첫 번째 `commit()` 성공 후 두 번째가 `flush()` 시 `IntegrityError`를 발생시켜 `ServiceRequestAlreadyMatchedError`로 변환됨.

#### 8. `models/__init__.py` 업데이트

```python
# 기존 + ChatRoom 추가
from app.models.chat_room import ChatRoom
```

`__all__`에도 `"ChatRoom"` 추가.

#### 9. `services/quote.py` 추가 import

```python
from app.core.exceptions import (
    # 기존
    DuplicateQuoteError,
    ForbiddenError,
    InvalidCursorError,
    ServiceRequestNotFoundError,
    ServiceRequestNotOpenForQuoteError,
    # 신규
    QuoteNotFoundError,
    QuoteNotPendingError,
    ServiceRequestAlreadyMatchedError,
)
from app.models.chat_room import ChatRoom
from app.repositories.chat_rooms import ChatRoomRepository
from app.schemas.chat_room import ChatRoomRead  # 라우터에서 필요, service는 ChatRoom 반환
```

**서비스 반환 타입 주의:** `QuoteService.accept()`는 `ChatRoom` ORM 객체를 반환하고, 라우터의 `response_model=ChatRoomRead`가 직렬화를 담당한다. `from_attributes=True` (CamelModel 기반)가 ORM → Pydantic 변환을 처리.

#### 10. 마이그레이션 revision 체인

현재 최신 revision: `d7bffeb07473` (add_quotes_table).
신규 마이그레이션의 `down_revision = 'd7bffeb07473'`.

---

### 프론트엔드 — 수락 버튼 배선

#### 현재 상태 (Story 4.1 legacy)

`apps/user-web/src/app/(customer)/requests/[id]/page.tsx`의 `li` 컴포넌트 내:

```tsx
{data.status === "open" && quote.status === "pending" && (
  <div className="flex gap-2 mt-2">
    <button disabled className="... opacity-50" title="Story 4.2에서 구현 예정">
      수락하기
    </button>
    <button disabled className="... opacity-50" title="Story 4.3에서 구현 예정">
      거절하기
    </button>
  </div>
)}
```

#### Story 4.2 변경 — 수락 버튼만 활성화

```tsx
// 파일 상단 import 추가
import {
  useAcceptQuote,           // 신규 (Orval 재생성 후)
  getListServiceRequestQuotesQueryKey,  // 기존
  // ... 기존 imports 유지
} from "@gosoom/api-client";

// 컴포넌트 내 mutation 추가
const acceptMutation = useAcceptQuote({
  mutation: {
    onSuccess: (chatRoom) => {
      queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
      queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      router.push(`/chat/${chatRoom.id}`);
    },
  },
});

// 견적 카드 내 수락 버튼 교체
{data.status === "open" && quote.status === "pending" && (
  <div className="flex gap-2 mt-2">
    <button
      onClick={() => acceptMutation.mutate({ quoteId: quote.id })}
      disabled={acceptMutation.isPending}
      className="rounded-md bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
    >
      {acceptMutation.isPending ? "처리 중…" : "수락하기"}
    </button>
    <button
      disabled
      className="rounded-md bg-red-500 px-3 py-1 text-xs text-white opacity-50"
      title="Story 4.3에서 구현 예정"
    >
      거절하기
    </button>
  </div>
)}
{acceptMutation.isError && (
  <p className="text-red-600 text-xs mt-1" role="alert">
    수락 처리에 실패했습니다.
  </p>
)}
```

**⚠️ `router.push` 사용:** `useRouter` from `"next/navigation"`은 이미 컴포넌트에 존재하지 않으면 추가 필요. 현재 파일에서 `useParams`만 사용 중이므로 `useRouter` import 추가.

**⚠️ `chatRoom.id` 타입:** Orval이 `ChatRoomRead.id`를 `string` 타입으로 생성함 (UUID는 OpenAPI에서 string으로 표현). `router.push(\`/chat/${chatRoom.id}\`)` 그대로 사용 가능.

**⚠️ `/chat/{chatRoomId}` 경로:** Story 4.4에서 구현될 채팅 화면. 이 스토리에서는 라우팅 경로만 배선 — 실제 채팅 화면이 없으면 404 페이지로 이동하는 것은 허용됨.

**⚠️ `useAcceptQuote` 훅 파라미터 확인:** Orval이 생성할 시그니처:
```ts
const accept_quote = (quoteId: string, options?) => ...
useAcceptQuote({mutation?: {mutationFn, ...}})
// mutate 호출: acceptMutation.mutate({ quoteId: quote.id })
```
Orval 재생성 후 `packages/api-client/src/generated/quotes/quotes.ts`에서 실제 파라미터 구조 확인 필수.

---

### 알려진 함정

#### 1. `CamelModel` import 경로 확정 ✅

`schemas/quote.py`와 기타 모든 스키마 파일의 확인 결과:
```python
from app.schemas.base import CamelModel  # 확정된 경로
```
`schemas/chat_room.py`에서 동일하게 사용.

#### 2. Alembic autogenerate vs 수동 작성 ⚠️

이 스토리는 **수동 마이그레이션** 작성. 이유:
- `uq_quotes_accepted_per_request`는 기존 `quotes` 테이블에 추가되는 index → autogenerate가 `chat_room` 모델만 감지하고 이 index를 놓칠 수 있음
- `postgresql_where` 조건부 index는 autogenerate가 불완전하게 처리할 수 있음

**수동 작성 패턴 (기존 마이그레이션 참조):**
- `apps/api/alembic/versions/d7bffeb07473_add_quotes_table.py` 패턴 그대로 사용
- `sa.Enum` 없이 string literal로 postgresql_where 작성

#### 3. `synchronize_session=False` ⚠️

`QuoteRepository.close_pending_except`의 bulk update 후 세션 내 **이미 로드된 `Quote` ORM 객체** (`quote` 변수)의 `status`는 갱신되지 않는다. 그러나 `quote.status`는 step 8에서 이미 `ACCEPTED`로 수동 설정했으므로 문제없다. flush 후 commit 시 DB에 올바르게 반영됨.

#### 4. `with_for_update()` async 동작 ⚠️

SQLAlchemy 2.0 async에서 `with_for_update()`는 `NOWAIT`/`SKIP LOCKED` 옵션 없이 사용하면 **BLOCKING** 잠금. 다른 트랜잭션이 같은 행을 업데이트하고 commit하지 않으면 대기한다. 테스트 환경에서는 동일 DB 연결(동일 트랜잭션) 내 조회이므로 self-deadlock 방지 — 각 테스트는 별도 트랜잭션.

#### 5. `QuoteService` 초기화 확장 불필요 ⚠️

`ChatRoomRepository`는 `accept()` 메서드 내에서만 사용되므로 `__init__`에 추가하지 않는다. 로컬 생성:
```python
chat_room_repo = ChatRoomRepository(self.session)
self.session.add(chat_room)  # repository.create() 패턴 대신 직접 add
```
또는 `ChatRoomRepository.create()` 메서드를 만들고 호출 — 일관성 위해 후자 권장.

#### 6. `main.py` 변경 없음 ⚠️

`quotes_router`는 `main.py:124`에 이미 등록됨. `_q_router`에 엔드포인트 추가만으로 충분.

#### 7. Orval 태그 확인 ⚠️

`_q_router`는 `tags=["quotes"]`이므로 새 엔드포인트도 `quotes/quotes.ts`에 생성됨.
`index.ts`의 `export * from './generated/quotes/quotes'`가 이미 있으므로 `index.ts` 변경 불필요.

---

### 구현 세부 사항

#### `schemas/quote.py` 변경 없음

기존 스키마(`QuoteCreate`, `QuoteRead`, `QuoteListItem`, `QuoteWithProInfo`, `ProInfoSummary`, `ServiceRequestSummary`) 모두 그대로 유지.

#### `services/quote.py` 추가 import 정리

```python
from sqlalchemy.exc import IntegrityError  # 이미 있음 (submit에서 사용)
from app.models.chat_room import ChatRoom
from app.repositories.chat_rooms import ChatRoomRepository
from app.core.exceptions import (
    # 기존 유지
    DuplicateQuoteError,
    ForbiddenError,
    InvalidCursorError,
    ServiceRequestNotFoundError,
    ServiceRequestNotOpenForQuoteError,
    # 신규 추가
    QuoteNotFoundError,
    QuoteNotPendingError,
    ServiceRequestAlreadyMatchedError,
)
```

#### `routers/quotes.py` 추가 import

```python
from app.schemas.chat_room import ChatRoomRead
```

#### `test_quotes_accept.py` 헬퍼 재사용

`tests/helpers.py`의 모든 헬퍼 그대로 재사용:
- `_make_customer`, `_make_pro`, `_make_admin`, `_make_category`
- `_make_service_request`, `_make_quote`, `_assign_pro_categories`, `_auth`

**수락 성공 검증 핵심:**
```python
resp = await client_db.post(f"/api/v1/quotes/{quote.id}/accept", headers=_auth(customer))
assert resp.status_code == 200
data = resp.json()
assert "id" in data  # chatRoomId
assert data["customerId"] == str(customer.id)
assert data["proId"] == str(pro.id)
assert data["quoteId"] == str(quote.id)

# DB 상태 검증
await db_session.refresh(sr)
assert str(sr.status) == "matched"  # 또는 sr.status == ServiceRequestStatus.MATCHED
await db_session.refresh(quote)
assert str(quote.status) == "accepted"

# 나머지 pending 견적 → closed 검증
await db_session.refresh(other_quote)
assert str(other_quote.status) == "closed"
```

**⚠️ ORM 객체 refresh 패턴:** bulk update (`close_pending_except`) 후 `other_quote` ORM 객체의 상태는 세션 캐시에 남아있을 수 있음. `await db_session.refresh(other_quote)` 호출 필요.

---

## 파일 구조 요약

### 신규 파일 (NEW)

```
apps/api/alembic/versions/<rev>_add_chat_rooms_table.py    # chat_rooms + uq_quotes_accepted_per_request
apps/api/app/models/chat_room.py                           # ChatRoom ORM 모델
apps/api/app/repositories/chat_rooms.py                    # ChatRoomRepository
apps/api/app/schemas/chat_room.py                          # ChatRoomRead Pydantic 스키마
apps/api/tests/test_quotes_accept.py                       # 9개 pytest 케이스
```

### 수정 파일 (UPDATE)

```
apps/api/app/models/__init__.py                            # ChatRoom import 추가
apps/api/app/repositories/service_requests.py             # get_by_id_for_update() 추가
apps/api/app/repositories/quotes.py                       # close_pending_except() 추가
apps/api/app/core/exceptions.py                           # QuoteNotFoundError, QuoteNotPendingError, ServiceRequestAlreadyMatchedError 추가
apps/api/app/services/quote.py                            # accept() 추가 + import 추가
apps/api/app/routers/quotes.py                            # _q_router에 POST /{quote_id}/accept 추가
apps/user-web/src/app/(customer)/requests/[id]/page.tsx   # 수락 버튼 활성화
openapi.json                                               # Orval 입력 갱신
packages/api-client/src/generated/                        # Orval 재생성
```

### 수정 없는 파일 (NO CHANGE)

```
apps/api/app/main.py                   # quotes_router 이미 등록됨
apps/api/app/models/quote.py           # 모델 변경 없음
apps/api/app/schemas/quote.py          # 스키마 변경 없음
packages/api-client/src/index.ts      # generated/quotes/quotes 이미 re-export됨
```

---

## 수동 체크포인트 (⚡)

**신규 설정 없음** — 새 환경변수 없음, Railway/Supabase 설정 변경 없음.

DB 마이그레이션 실행: `uv run alembic upgrade head` (로컬 및 Railway 자동 배포 시 실행).

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `pytest apps/api/tests/test_quotes_accept.py` — 9/9 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과 (apps/user-web)
- [ ] Orval 생성물 커밋 포함 (`packages/api-client/src/generated/` 변경사항)
- [ ] user-web `(customer)/requests/[id]` 수락 버튼 동작 확인:
  - CUSTOMER 로그인 → 요청 상세 → pending 견적 "수락하기" 클릭
  - 처리 중 버튼 비활성화 확인
  - 성공 후 `/chat/{chatRoomId}` 이동 (404여도 라우팅 자체는 동작)
  - 에러 시 메시지 표시 확인

---

## 이전 스토리 인텔리전스 (Story 4.1 교훈)

1. **`cursor scope` 패치:** Story 4.1 code-review에서 cursor가 다른 request의 cursor를 수용하는 문제가 발견됨. `decode_cursor(cursor).split(":", 1)` 패턴으로 `{request_id}:{quote_id}` scope 검증이 추가됨. **accept에는 cursor 없으므로 해당 없음.**

2. **`from_attributes=True` 자동 처리:** `CamelModel` 기반 스키마는 `from_attributes=True`가 이미 설정됨. `ChatRoomRead.model_validate(chat_room)` 불필요 — FastAPI 라우터의 `response_model`이 자동 처리.

3. **helpers.py 재사용 규칙:** `_make_quote(status=QuoteStatus.REJECTED)` 등 status 파라미터로 다양한 상태 견적을 생성할 수 있음.

4. **`pro_ids set 순서 비결정성` deferred:** Story 4.1 review에서 `list({...})` 패턴이 비결정적 순서라는 deferred 항목이 있음. **accept에서는 set/list 변환 없으므로 해당 없음.**

5. **Orval 타입명 생성 패턴:** `ChatRoomRead` → Orval이 `chatRoomRead.ts` 파일 생성 + `ChatRoomRead` 타입 export. `model/index.ts`에 자동 추가됨. Orval 재생성 후 확인.

6. **`status: str` ORM enum 직렬화:** 기존 `QuoteStatus` 패턴 그대로 — `CamelModel`의 `from_attributes=True`가 enum → str(value) 처리. `str(quote.status)` 명시 불필요.

---

## Review Findings

- [x] [Review][Decision] IntegrityError 미분류 — 현재 유지(통합 처리) 결정. [apps/api/app/services/quote.py:254-257]
- [x] [Review][Decision] `chat_rooms.service_request_id` UniqueConstraint 추가 여부 — 추가 안 함(현재 유지) 결정.
- [x] [Review][Patch] chat_rooms FK ondelete='CASCADE' 누락 — 수정 완료. [apps/api/alembic/versions/a1b2c3d4e5f6_add_chat_rooms_table.py:31-32, apps/api/app/models/chat_room.py:23-27]
- [x] [Review][Patch] `quote_not_pending` 테스트 케이스 불완전 — `accepted`/`closed` 상태 케이스 추가 완료 (테스트 3개 → 4개). [apps/api/tests/test_quotes_accept.py]
- [x] [Review][Defer] TOCTOU — quote 행 잠금 없음 [apps/api/app/services/quote.py:212-231] — deferred, SR FOR UPDATE가 동일 SR에 대한 모든 동시 수락을 직렬화하므로 주요 레이스 차단됨. partial index가 최종 방어선.
- [x] [Review][Defer] CANCELLED/COMPLETED 요청에 `service_request_already_matched` 반환 [apps/api/app/services/quote.py:226-227] — deferred, AC3 스펙이 matched 상태만 명시. 비-OPEN 포괄 처리로 기술적 수용 가능.
- [x] [Review][Defer] 동시 수락 race condition 동시성 테스트 없음 (AC2) — deferred, 복잡한 async 동시성 테스트는 현 스토리 완료 정의 범위 외.
- [x] [Review][Defer] 소프트삭제된 pro 사용자와의 채팅방 생성 가능 [apps/api/app/services/quote.py:237-242] — deferred, 사용자 탈퇴 플로우는 Epic 6 범위.
- [x] [Review][Defer] `uq_quotes_accepted_per_request` PostgreSQL 전용 partial index — deferred, 프로젝트 PostgreSQL 전용.
- [x] [Review][Defer] non-IntegrityError 발생 시 명시적 rollback 없음 [apps/api/app/services/quote.py:253-257] — deferred, FastAPI 세션 dependency가 요청 컨텍스트에서 처리.
- [x] [Review][Defer] AC5 `/chat/{chatRoomId}` 라우트 미구현 → 404 [apps/user-web/src/app/(customer)/requests/[id]/page.tsx:71] — deferred, 개발자 노트에서 명시적 허용.
- [x] [Review][Defer] AC5 채팅방 TanStack Query 캐시 무효화 누락 [apps/user-web/src/app/(customer)/requests/[id]/page.tsx:67-73] — deferred, Story 4.4(채팅방 목록) 구현 시 쿼리 키 정의 후 처리.

---

## Dev Agent Record

### Completion Notes

- **AC1 단일 트랜잭션 원자적 수락:** `QuoteService.accept()` — SELECT FOR UPDATE → 상태 검증 → 4단계 전환(sr→matched, quote→accepted, 나머지→closed, chat_room 생성) → flush → commit 순서로 구현
- **AC2 동시 수락 race 차단:** `with_for_update()` 비관적 잠금 + `uq_quotes_accepted_per_request` partial unique index 이중 방어; `IntegrityError` 발생 시 `ServiceRequestAlreadyMatchedError(409)`로 변환
- **AC3 거부 케이스:** 404(quote_not_found), 409(quote_not_pending, service_request_already_matched), 403(forbidden) 모두 정상 반환
- **AC4 권한 제어:** `require_role(CUSTOMER)` — PRO/ADMIN 403, 비인증 401
- **AC5 프론트엔드:** `useAcceptQuote` 훅 배선, 성공 후 캐시 무효화 + `/chat/{chatRoomId}` 라우팅, 로딩/에러 상태 UI
- **테스트:** 9/9 통과 (`test_quotes_accept.py`), 전체 회귀 없음 (기존 5개 실패는 사전 존재 카테고리 이름 unique constraint DB 상태 문제)
- **Orval:** `useAcceptQuote` 훅 + `ChatRoomRead` 타입 생성 확인
- **빌드:** `pnpm --filter user-web build` 성공

### File List

- `apps/api/alembic/versions/a1b2c3d4e5f6_add_chat_rooms_table.py` (NEW)
- `apps/api/app/models/chat_room.py` (NEW)
- `apps/api/app/repositories/chat_rooms.py` (NEW)
- `apps/api/app/schemas/chat_room.py` (NEW)
- `apps/api/tests/test_quotes_accept.py` (NEW)
- `apps/api/app/models/__init__.py` (MODIFIED — ChatRoom import 추가)
- `apps/api/app/repositories/service_requests.py` (MODIFIED — get_by_id_for_update 추가)
- `apps/api/app/repositories/quotes.py` (MODIFIED — close_pending_except 추가)
- `apps/api/app/core/exceptions.py` (MODIFIED — 예외 3개 추가)
- `apps/api/app/services/quote.py` (MODIFIED — accept() 추가)
- `apps/api/app/routers/quotes.py` (MODIFIED — POST /{quote_id}/accept 추가)
- `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` (MODIFIED — 수락 버튼 활성화)
- `openapi.json` (MODIFIED — Orval 입력 갱신)
- `packages/api-client/src/generated/quotes/quotes.ts` (MODIFIED — useAcceptQuote 추가)
- `packages/api-client/src/generated/model/chatRoomRead.ts` (NEW — Orval 생성)
- `packages/api-client/src/generated/model/index.ts` (MODIFIED — Orval 갱신)

### Change Log

- 2026-06-10: Story 4.2 스토리 파일 작성 완료
- 2026-06-10: Story 4.2 구현 완료 — chat_rooms 마이그레이션, ChatRoom 모델/레포/스키마, QuoteService.accept() 단일 트랜잭션, 테스트 9/9, Orval 재생성, 수락 버튼 활성화
