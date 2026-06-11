---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 3.4: 내 견적 목록·상태 조회

- **Status:** review
- **Epic:** 3 — 고수 카테고리 & 견적 (FR9-12)
- **Story ID / Key:** 3-4 / 3-4-my-quotes-list
- **작성일:** 2026-06-09

---

## 사용자 스토리

As a 로그인한 고수(PRO),  
내가 제안한 견적의 목록과 상태를 조회하고 싶다.  
So that 어떤 견적이 수락/거절/마감되었는지 추적할 수 있다.

---

## 인수 기준 (BDD)

**AC1** — `GET /api/v1/quotes` 기본 목록 조회 (FR12)

- **Given** PRO가 여러 견적을 제안했을 때
- **When** `GET /api/v1/quotes`를 호출하면
- **Then** 본인 견적만 `{items, nextCursor}` 형식으로 반환된다
- **And** 각 항목에 견적 상태(pending/accepted/rejected/closed)와 대상 요청 정보(region, description, requestStatus, categoryId)가 포함된다
- **And** 정렬은 견적 id DESC(최신순)이다

**AC2** — cursor 페이지네이션

- **Given** PRO가 10개 이상의 견적을 제안했을 때
- **When** `GET /api/v1/quotes?limit=5`로 첫 페이지를 조회하면
- **Then** `{items: [...5개], nextCursor: <non-null>}`가 반환된다
- **When** `GET /api/v1/quotes?cursor=<nextCursor>&limit=5`로 다음 페이지를 조회하면
- **Then** `{items: [...나머지], nextCursor: null}`이 반환된다

**AC3** — 소유권 검사 (FR4)

- **Given** 타 PRO의 견적이 존재할 때
- **When** 현재 PRO가 목록을 조회하면
- **Then** 본인 견적만 반환되고 타 PRO 견적은 포함되지 않는다

**AC4** — 권한 제어 (FR4)

- **Given** 각 역할/인증 상태에서 요청 시
- **Then** 비인증 → 401 `not_authenticated`, CUSTOMER 역할 → 403 `forbidden`, ADMIN 역할 → 403 `forbidden`

**AC5** — 상태 변경 반영 (Epic 4 전이 정합)

- **Given** 견적 상태가 변경되었을 때(accepted/rejected/closed)
- **When** 고수가 목록을 조회하면
- **Then** 변경된 상태가 정확히 반영된다

**AC6** — user-web `(pro)/quotes` 화면

- **Given** user-web `(pro)/quotes` 페이지에서
- **When** PRO가 견적 목록을 열람하면
- **Then** Orval 훅(`useListMyQuotes`)으로 목록을 불러오고 각 견적의 상태가 한국어 라벨로 표시된다
- **And** 대상 요청의 지역과 설명(50자 초과 시 `...` truncate)이 함께 표시된다
- **And** 빈 목록일 때 "제안한 견적이 없습니다" 메시지가 표시된다

---

## 태스크 및 서브태스크

- [x] **Task 1:** `QuoteRepository`에 `list_by_pro` 메서드 추가
  - [x] `apps/api/app/repositories/quotes.py` 수정
  - [x] pro_id 필터 + deleted_at IS NULL + id DESC keyset cursor 페이지네이션
  - [x] 서비스 요청 정보 JOIN 또는 batch 조회 방식 구현 (설계 결정 참조)

- [x] **Task 2:** Pydantic 스키마 추가
  - [x] `apps/api/app/schemas/quote.py` 수정
  - [x] `ServiceRequestSummary`(region, description, requestStatus, categoryId) 추가
  - [x] `QuoteListItem`(Quote 전 필드 + `serviceRequest: ServiceRequestSummary | None`) 추가

- [x] **Task 3:** `QuoteService.list_mine()` 구현
  - [x] `apps/api/app/services/quote.py` 수정
  - [x] cursor 디코드 → UUID 변환 → `InvalidCursorError` 처리
  - [x] `list_by_pro` 호출 → batch 서비스 요청 조회 → `Page[QuoteListItem]` 반환

- [x] **Task 4:** `quotes.py` 라우터 리팩터링 + 신규 GET 엔드포인트 추가
  - [x] `apps/api/app/routers/quotes.py` 수정
  - [x] prefix를 `/api/v1/service-requests` → `/api/v1`으로 변경
  - [x] 기존 POST 경로를 `/{request_id}/quotes` → `/service-requests/{request_id}/quotes`로 변경
  - [x] `GET /quotes` 엔드포인트 추가 (`cursor`, `limit` 쿼리 파라미터)
  - [x] 라우터 함수명: `list_my_quotes` (Orval operationId = `listMyQuotes` → 훅 = `useListMyQuotes`)

- [x] **Task 5:** pytest 작성 (`apps/api/tests/test_quotes_my_list.py`)
  - [x] AC1 기본 목록: 200, 본인 견적만, 필드 검증 (serviceRequest 포함)
  - [x] AC1 빈 목록: 200, items=[]
  - [x] AC2 페이지네이션: limit=1 + nextCursor, 두 번째 페이지 조회
  - [x] AC2 nextCursor=null (마지막 페이지)
  - [x] AC2 잘못된 cursor: 400 invalid_cursor
  - [x] AC3 타 PRO 견적 미포함 확인
  - [x] AC4 비인증: 401 not_authenticated
  - [x] AC4 CUSTOMER: 403 forbidden
  - [x] AC4 ADMIN: 403 forbidden

- [x] **Task 6:** Orval 재생성 + api-client 확인
  - [x] API 서버 기동 후 `pnpm orval` 실행
  - [x] `useListMyQuotes` 훅 생성 확인
  - [x] `QuoteListItem`, `ServiceRequestSummary` 타입 생성 확인
  - [x] `packages/api-client/src/index.ts`에 신규 훅 re-export 확인 (Orval 자동 또는 수동)

- [x] **Task 7:** user-web `(pro)/quotes/page.tsx` 구현
  - [x] `apps/user-web/src/app/(pro)/quotes/page.tsx` 신규 생성
  - [x] `useListMyQuotes` 훅으로 목록 조회
  - [x] 상태별 한국어 라벨, 요청 region/description 표시
  - [x] 빈 목록 처리

---

## 개발자 노트

### 핵심 설계 결정

#### 1. 라우터 prefix 변경 (필수 ⚠️)

현재 `routers/quotes.py`의 `prefix="/api/v1/service-requests"`를 `prefix="/api/v1"`으로 변경하고,
기존 POST 경로를 `/service-requests/{request_id}/quotes`로 업데이트해야 한다.

Story 3.3 개발자 노트에서 예고한 변경이다:
> "Story 3.4에서 `GET /api/v1/quotes?mine=true` 추가 시 prefix를 `/api/v1`로 변경 후 두 경로를 모두 처리하면 된다."

```python
# 변경 전 (Story 3.3)
router = APIRouter(prefix="/api/v1/service-requests", tags=["quotes"])

@router.post("/{request_id}/quotes", ...)
async def create_service_request_quote(...): ...

# 변경 후 (Story 3.4)
router = APIRouter(prefix="/api/v1", tags=["quotes"])

@router.post("/service-requests/{request_id}/quotes", ...)
async def create_service_request_quote(...): ...

@router.get("/quotes", response_model=Page[QuoteListItem])
async def list_my_quotes(...): ...
```

**기존 POST 엔드포인트 URL은 변경되지 않는다** — prefix + path = `/api/v1/service-requests/{id}/quotes`로 동일하다. Orval 생성 훅도 변경 없다.

#### 2. 대상 요청 정보 포함 전략 — 두 쿼리 방식

견적 목록에 "대상 요청 정보"를 포함하는 방법으로 **두 쿼리 방식**을 선택한다.

**이유:**
- `Quote` 모델에 SQLAlchemy `relationship`이 없어 `selectinload` 불가
- relationship을 추가하면 모델 변경이 필요해 Story 3.3의 마이그레이션에 소급 영향
- 두 쿼리 방식은 기존 repository 패턴(단순 select)과 일관성 유지
- limit ≤ 20이므로 N+1 쿼리 성능 이슈 없음

**구현:**

```python
# repositories/quotes.py — list_by_pro 추가
async def list_by_pro(
    self, pro_id: uuid.UUID, after_id: uuid.UUID | None, limit: int
) -> list[Quote]:
    """PRO의 견적을 id DESC(최신순) keyset으로 조회. deleted_at IS NULL 필터."""
    stmt = select(Quote).where(
        Quote.pro_id == pro_id,
        Quote.deleted_at.is_(None),
    )
    if after_id is not None:
        stmt = stmt.where(Quote.id < after_id)
    stmt = stmt.order_by(Quote.id.desc()).limit(limit)
    return list((await self.session.execute(stmt)).scalars().all())
```

```python
# services/quote.py — list_mine 추가
async def list_mine(
    self, current_user: User, cursor: str | None, limit: int
) -> Page[QuoteListItem]:
    limit = max(1, limit)
    after_id: UUID | None = None
    if cursor is not None:
        decoded = decode_cursor(cursor)
        try:
            after_id = UUID(decoded)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidCursorError() from exc

    rows = await self.quote_repo.list_by_pro(current_user.id, after_id, limit + 1)
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

    # 대상 요청 batch 조회
    request_ids = [r.service_request_id for r in page_rows]
    request_map: dict[UUID, ServiceRequest] = {}
    if request_ids:
        sr_rows = await self.sr_repo.list_by_ids(request_ids)
        request_map = {r.id: r for r in sr_rows}

    items = []
    for q in page_rows:
        sr = request_map.get(q.service_request_id)
        items.append(QuoteListItem(
            id=q.id,
            service_request_id=q.service_request_id,
            price=q.price,
            message=q.message,
            status=q.status,
            created_at=q.created_at,
            updated_at=q.updated_at,
            service_request=ServiceRequestSummary.model_validate(sr) if sr else None,
        ))

    return Page[QuoteListItem](items=items, next_cursor=next_cursor)
```

#### 3. `ServiceRequestRepository.list_by_ids` 추가

`list_mine()`이 batch 조회를 위해 호출하는 신규 메서드:

```python
# repositories/service_requests.py — list_by_ids 추가
async def list_by_ids(self, ids: list[uuid.UUID]) -> list[ServiceRequest]:
    """UUID 목록으로 미삭제 요청 batch 조회. 정렬 없음(호출측이 order 관리)."""
    if not ids:
        return []
    result = await self.session.execute(
        select(ServiceRequest).where(
            ServiceRequest.id.in_(ids),
            ServiceRequest.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())
```

#### 4. Pydantic 스키마 설계

```python
# schemas/quote.py 수정 — 기존 QuoteCreate/QuoteRead 유지 + 추가

class ServiceRequestSummary(CamelModel):
    """견적 목록에서 대상 요청 요약 정보(Story 3.4)."""
    id: uuid.UUID
    category_id: uuid.UUID
    region: str
    description: str
    status: str


class QuoteListItem(CamelModel):
    """내 견적 목록 응답 아이템(Story 3.4). service_request 필드 포함."""
    id: uuid.UUID
    service_request_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    service_request: ServiceRequestSummary | None = None
```

**QuoteRead는 그대로 유지** — Story 3.3의 POST 응답 스키마를 변경하지 않는다.

#### 5. 라우터 GET 엔드포인트 — `list_my_quotes`

```python
@router.get("/quotes", response_model=Page[QuoteListItem])
async def list_my_quotes(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[QuoteListItem]:
    svc = QuoteService(session)
    return await svc.list_mine(current_user, cursor, limit)
```

**Orval operationId**: 함수명 `list_my_quotes` → `listMyQuotes` → 훅 이름 `useListMyQuotes`.

#### 6. `main.py` 변경 없음

`quotes_router`는 이미 등록되어 있다. prefix 변경은 `routers/quotes.py` 내에서만 처리된다.

---

### 구현 세부 사항

#### `schemas/quote.py` 최종 구조

```python
# 기존 (Story 3.3, 변경 없음)
class QuoteCreate(CamelModel): ...
class QuoteRead(CamelModel): ...

# 신규 (Story 3.4)
class ServiceRequestSummary(CamelModel):
    id: uuid.UUID
    category_id: uuid.UUID
    region: str
    description: str
    status: str

class QuoteListItem(CamelModel):
    id: uuid.UUID
    service_request_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    service_request: ServiceRequestSummary | None = None
```

#### `services/quote.py` 추가 임포트

```python
# 기존 임포트에 추가
from uuid import UUID

from app.core.pagination import decode_cursor, encode_cursor
from app.core.exceptions import InvalidCursorError
from app.models.service_request import ServiceRequest
from app.schemas.pagination import Page
from app.schemas.quote import QuoteListItem, ServiceRequestSummary
```

#### `routers/quotes.py` 최종 구조

```python
from fastapi import APIRouter, Depends, Query
...

router = APIRouter(prefix="/api/v1", tags=["quotes"])


@router.post("/service-requests/{request_id}/quotes", response_model=QuoteRead, status_code=201)
async def create_service_request_quote(
    request_id: uuid.UUID,
    body: QuoteCreate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> QuoteRead:
    svc = QuoteService(session)
    return await svc.submit(request_id, body, current_user)


@router.get("/quotes", response_model=Page[QuoteListItem])
async def list_my_quotes(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[QuoteListItem]:
    svc = QuoteService(session)
    return await svc.list_mine(current_user, cursor, limit)
```

#### `test_quotes_my_list.py` 구조

기존 `test_quotes_submit.py`의 헬퍼를 재사용 불가(다른 파일). 독립 헬퍼 정의:

```python
# 헬퍼
async def _make_pro(db, email) -> User: ...
async def _make_customer(db, email) -> User: ...
async def _make_admin(db, email) -> User: ...
async def _make_category(db) -> Category: ...
async def _make_service_request(db, customer, category) -> ServiceRequest: ...
async def _make_quote(db, pro, request, price=10000, message="테스트 견적") -> Quote: ...
def _auth(user) -> dict: ...
```

테스트 케이스 목록 (9개):

| # | 테스트명 | 검증 |
|---|---------|------|
| 1 | `test_list_my_quotes_success_200` | 본인 견적 반환, serviceRequest 포함, 필드 검증 |
| 2 | `test_list_my_quotes_empty_200` | 견적 없음: 200, items=[] |
| 3 | `test_list_my_quotes_pagination_next_cursor` | limit=1, 2개 견적 → nextCursor non-null |
| 4 | `test_list_my_quotes_pagination_second_page` | nextCursor로 두 번째 페이지 조회 |
| 5 | `test_list_my_quotes_no_other_pro_quotes` | 타 PRO 견적 미포함 확인 |
| 6 | `test_list_my_quotes_invalid_cursor_400` | 잘못된 cursor → 400 invalid_cursor |
| 7 | `test_list_my_quotes_no_token_401` | 비인증 → 401 not_authenticated |
| 8 | `test_list_my_quotes_customer_role_403` | CUSTOMER → 403 forbidden |
| 9 | `test_list_my_quotes_admin_role_403` | ADMIN → 403 forbidden |

#### `(pro)/quotes/page.tsx` 프론트엔드

```tsx
"use client";

import {
  useListMyQuotes,
  type PageQuoteListItem,
} from "@gosoom/api-client";

const QUOTE_STATUS_LABELS: Record<string, string> = {
  pending: "검토 중",
  accepted: "수락됨",
  rejected: "거절됨",
  closed: "마감됨",
};

const REQUEST_STATUS_LABELS: Record<string, string> = {
  open: "접수됨",
  matched: "매칭됨",
  completed: "완료됨",
  cancelled: "취소됨",
};

export default function MyQuotesPage() {
  const { data, isPending, isError } = useListMyQuotes<PageQuoteListItem, Error>();

  if (isPending) return <div>로딩 중...</div>;
  if (isError) return <div>견적 목록을 불러오는 중 오류가 발생했습니다.</div>;

  const items = data?.items ?? [];

  return (
    <main style={{ padding: "1.5rem" }}>
      <h1>내 견적 목록</h1>
      {items.length === 0 && <p>제안한 견적이 없습니다.</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {items.map((quote) => (
          <li key={quote.id} style={{ marginBottom: "1.5rem", borderBottom: "1px solid #eee", paddingBottom: "1rem" }}>
            <div>
              <strong>견적 상태:</strong>{" "}
              {QUOTE_STATUS_LABELS[quote.status] ?? quote.status}
            </div>
            <div>
              <strong>금액:</strong> {quote.price.toLocaleString()}원
            </div>
            <div>
              <strong>메시지:</strong> {quote.message}
            </div>
            {quote.serviceRequest && (
              <div style={{ marginTop: "0.5rem", color: "#555" }}>
                <div>
                  <strong>요청 지역:</strong> {quote.serviceRequest.region}
                </div>
                <div>
                  <strong>요청 내용:</strong>{" "}
                  {(quote.serviceRequest.description ?? "").slice(0, 50)}
                  {(quote.serviceRequest.description?.length ?? 0) > 50 ? "..." : ""}
                </div>
                <div>
                  <strong>요청 상태:</strong>{" "}
                  {REQUEST_STATUS_LABELS[quote.serviceRequest.status] ?? quote.serviceRequest.status}
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
```

**주의:** `useListMyQuotes`의 정확한 시그니처는 Orval 재생성 후 확인. `PageQuoteListItem`는 Orval이 `Page_QuoteListItem_` 또는 유사 이름으로 생성할 수 있다. 생성된 타입명을 확인하고 import를 맞출 것.

---

## 알려진 함정

### 1. POST 엔드포인트 URL 회귀 검사 ⚠️

`quotes.py` prefix 변경 후 **POST 엔드포인트 URL이 변경되지 않았는지** 반드시 검증한다.
- 변경 전: `prefix="/api/v1/service-requests"` + `"/{request_id}/quotes"` = `/api/v1/service-requests/{request_id}/quotes`
- 변경 후: `prefix="/api/v1"` + `"/service-requests/{request_id}/quotes"` = `/api/v1/service-requests/{request_id}/quotes`

URL이 동일해야 한다. 기존 `test_quotes_submit.py` 전체 통과로 검증.

### 2. `ServiceRequestRepository.list_by_ids` 추가 ⚠️

`service_request.py` 레포지토리에 `list_by_ids` 메서드를 추가하지 않으면 `QuoteService.list_mine()`이 동작하지 않는다. **반드시 추가할 것.**

### 3. Orval 타입명 불일치 ⚠️

`Page[QuoteListItem]`는 FastAPI/Pydantic이 OpenAPI 스키마에서 `Page_QuoteListItem_`로 표현할 수 있다.
Orval 재생성 후 `src/generated/model/index.ts`에서 실제 타입명을 확인하고 프론트엔드 import를 맞출 것.

### 4. `service_request` 없는 경우(소프트 삭제) ⚠️

`list_by_ids`에서 `deleted_at IS NULL` 필터를 적용하므로, 소프트 삭제된 요청은 `request_map`에 없다.
`QuoteListItem.service_request`는 `Optional`이므로 `None`으로 반환된다 — 프론트엔드에서 `quote.serviceRequest && ...` 조건부 렌더링이 필수.

### 5. `Page` import 충돌 ⚠️

`services/quote.py`에 `from app.schemas.pagination import Page`를 추가할 때 기존 임포트와 충돌 없는지 확인. `ServiceRequest` 모델 임포트도 추가 필요 (batch 조회 반환 타입).

### 6. `QuoteListItem.status` — ORM enum → str 직렬화 ⚠️

`Quote.status`는 `QuoteStatus` enum 타입이다. `QuoteListItem.status: str`으로 선언되어 있으므로 `model_validate`시 `str(q.status)` 또는 `q.status.value`로 변환이 필요할 수 있다.
`CamelModel`의 `from_attributes=True`가 enum을 값(value)으로 직렬화하는지 확인하거나, 명시적으로 `status: str = Field(default="")` + `model_validator`를 사용할 것.

실제로 기존 `QuoteRead.status: str`도 같은 방식으로 동작 중이므로 패턴 동일. ORM 직렬화 경계에서 `from_attributes=True`가 enum → str(value)로 변환함.

### 7. `limit` 파라미터 Query 기본값 ⚠️

`GET /api/v1/quotes`의 `limit` 기본값을 `20`으로 설정한다(service-requests 목록과 동일). `ge=1, le=100` 범위 제한 포함. `ge=1`이 서비스 계층의 `max(1, limit)` 방어와 이중 검증.

### 8. Orval `quotes/quotes.ts` 파일에 GET 훅 자동 추가 ⚠️

`packages/api-client/src/index.ts`에 이미 `'./generated/quotes/quotes'`가 re-export되어 있다. Orval 재생성 후 `useListMyQuotes`가 해당 파일에 자동 생성되면 별도 `index.ts` 수정이 불필요하다. 확인 후 처리.

---

## 파일 구조 요약

### 수정 파일 (UPDATE)

```
apps/api/app/repositories/quotes.py              # list_by_pro 메서드 추가
apps/api/app/repositories/service_requests.py   # list_by_ids 메서드 추가
apps/api/app/schemas/quote.py                    # ServiceRequestSummary, QuoteListItem 추가
apps/api/app/services/quote.py                   # list_mine() 메서드 추가 + 임포트 추가
apps/api/app/routers/quotes.py                   # prefix 변경 + list_my_quotes GET 추가
packages/api-client/src/generated/              # Orval 재생성 전체
```

### 신규 파일 (NEW)

```
apps/api/tests/test_quotes_my_list.py            # 9개 pytest 케이스
apps/user-web/src/app/(pro)/quotes/page.tsx      # 내 견적 목록 UI
```

### 수정 없는 파일 (NO CHANGE)

```
apps/api/app/main.py                             # quotes_router 이미 등록됨
apps/api/app/models/quote.py                     # 모델 변경 없음
apps/api/app/models/__init__.py                  # 변경 없음
apps/api/app/core/exceptions.py                  # 변경 없음 (InvalidCursorError 재사용)
apps/api/app/core/pagination.py                  # 변경 없음
apps/user-web/src/app/(pro)/feed/[id]/page.tsx   # 변경 없음
packages/api-client/src/index.ts                 # Orval이 자동 처리 예상 (재생성 후 확인)
```

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `pytest apps/api/tests/test_quotes_my_list.py` — 9/9 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과 (특히 `test_quotes_submit.py` 14/14 확인)
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과
- [ ] Orval 생성물 커밋 포함 (`packages/api-client/src/generated/` 변경사항)
- [ ] user-web `(pro)/quotes` 페이지 동작 확인:
  - PRO 로그인 후 `/quotes` → 견적 목록 표시 (상태 한국어 라벨)
  - 대상 요청 지역/내용 표시
  - 빈 목록 시 "제안한 견적이 없습니다" 표시

---

## 이전 스토리 인텔리전스 (Story 3.3 교훈)

1. **라우터 prefix 변경 예고**: Story 3.3 개발자 노트에서 이미 "Story 3.4에서 prefix를 `/api/v1`로 변경"을 명시했다. 이를 정확히 따른다.

2. **Orval 훅 mutate 시그니처 확인**: 재생성 후 생성된 타입명과 파라미터명을 직접 확인하고 프론트 코드를 맞출 것. 스키마명이 `Page_QuoteListItem_` 같은 형태일 수 있다.

3. **`model_validate` 패턴**: ORM 객체 → Pydantic 변환은 `ServiceRequestSummary.model_validate(sr)` 패턴 사용. `from_attributes=True`가 `CamelModel`에 설정되어 있다.

4. **cursor 디코드 오류 처리**: `ServiceRequestService.list_mine()`과 완전히 동일한 패턴:
   ```python
   decoded = decode_cursor(cursor)
   try:
       after_id = UUID(decoded)
   except (ValueError, AttributeError, TypeError) as exc:
       raise InvalidCursorError() from exc
   ```

5. **빈 page_rows 처리**: `page_rows`가 빈 리스트이면 `encode_cursor`를 호출하지 않는다 — `has_more`가 False이므로 안전.

6. **`list_by_ids` 정렬 없음**: `list_by_ids`는 batch 조회 헬퍼이므로 정렬 없음. dict 변환 후 quote 순서(id DESC)를 따른다.

---

## Dev Agent Record

### Implementation Plan

두 쿼리 방식(relationship 없음): `list_by_pro` → `list_by_ids` 순으로 batch 조회.
라우터 prefix를 `/api/v1`로 변경해 POST URL은 동일(`/api/v1/service-requests/{id}/quotes`)하게 유지.
Orval operationName 정규식이 `list_my_quotes_api_v1_quotes_get` → `list_my_quotes`로 정리되어 `useListMyQuotes` 훅 자동 생성.
Orval 타입명: `PageQuoteListItem` (Page_QuoteListItem_ 아님), `QuoteListItemServiceRequest` (serviceRequest 필드 타입).

### Completion Notes

- AC1: `GET /api/v1/quotes` → 본인 견적만 id DESC 정렬, `serviceRequest` 포함 반환 확인
- AC2: cursor 페이지네이션(limit=1, 2개 견적) nextCursor → 두 번째 페이지 → nextCursor=null 확인
- AC2: 잘못된 cursor(비 base64) → 400 invalid_cursor 확인
- AC3: 타 PRO 견적 미포함 소유권 검사 확인
- AC4: 비인증 401, CUSTOMER 403, ADMIN 403 확인
- AC5: QuoteStatus ORM enum → str 직렬화 `from_attributes=True` 경유 정상 동작
- AC6: user-web `/quotes` 페이지 빌드 성공, `useListMyQuotes` 훅 통합
- 테스트: `test_quotes_my_list.py` 9/9 통과, `test_quotes_submit.py` 14/14 회귀 없음
- `pnpm typecheck` 성공, user-web build 성공

### File List

- `apps/api/app/repositories/quotes.py` — `list_by_pro` 메서드 추가
- `apps/api/app/repositories/service_requests.py` — `list_by_ids` 메서드 추가
- `apps/api/app/schemas/quote.py` — `ServiceRequestSummary`, `QuoteListItem` 추가
- `apps/api/app/services/quote.py` — `list_mine()` 메서드 추가 + 임포트 추가
- `apps/api/app/routers/quotes.py` — prefix 변경 + `list_my_quotes` GET 추가
- `apps/api/tests/test_quotes_my_list.py` — 신규: 9개 pytest 케이스
- `apps/user-web/src/app/(pro)/quotes/page.tsx` — 신규: 내 견적 목록 UI
- `packages/api-client/src/generated/quotes/quotes.ts` — Orval 재생성
- `packages/api-client/src/generated/model/index.ts` — Orval 재생성
- `packages/api-client/src/generated/model/pageQuoteListItem.ts` — Orval 신규
- `packages/api-client/src/generated/model/quoteListItem.ts` — Orval 신규
- `packages/api-client/src/generated/model/quoteListItemServiceRequest.ts` — Orval 신규
- `packages/api-client/src/generated/model/serviceRequestSummary.ts` — Orval 신규
- `packages/api-client/src/generated/model/listMyQuotesParams.ts` — Orval 신규
- `packages/api-client/src/generated/model/pageQuoteListItemNextCursor.ts` — Orval 신규
- `openapi.json` — API spec 갱신
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 상태 갱신

### Change Log

- 2026-06-09: Story 3.4 구현 완료 — 내 견적 목록 GET 엔드포인트 + cursor 페이지네이션 + user-web 페이지
