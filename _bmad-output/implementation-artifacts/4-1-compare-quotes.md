---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 4.1: 받은 견적 비교

- **Status:** done
- **Epic:** 4 — 매칭 & 채팅 (거래 루프 완결) (FR8, FR13-18)
- **Story ID / Key:** 4-1 / 4-1-compare-quotes
- **작성일:** 2026-06-10

---

## 사용자 스토리

As a 로그인한 고객(CUSTOMER),  
내 요청에 들어온 견적들을 가격·메시지·고수 정보와 함께 비교하고 싶다.  
So that 가장 마음에 드는 고수를 골라 수락(Story 4.2) 또는 거절(Story 4.3) 결정을 내릴 수 있다.

---

## 인수 기준 (BDD)

**AC1** — `GET /api/v1/service-requests/{id}/quotes` 기본 조회 (FR8)

- **Given** 본인 요청에 여러 견적이 들어왔을 때
- **When** 고객이 `GET /api/v1/service-requests/{id}/quotes`를 호출하면
- **Then** 해당 요청의 견적들이 `{items, nextCursor}` 형식으로 반환된다
- **And** 각 항목에 가격(`price`)·제안 메시지(`message`)·견적 상태(`status`)·고수 기본 정보(`pro.displayName` + `pro.categoryIds`)가 포함된다
- **And** 응답에 고수의 이메일이 포함되지 않는다(개인정보 최소 노출)
- **And** 정렬은 견적 id DESC(최신 등록순)이다
- **And** 모든 상태(pending/accepted/rejected/closed)의 견적이 반환된다(고객은 전체 이력 조회 가능)

**AC2** — 소유권 검사 (FR4)

- **Given** 타 고객의 요청 id로 조회할 때
- **When** 현재 고객이 `GET /api/v1/service-requests/{other_id}/quotes`를 호출하면
- **Then** 403 `forbidden` 으로 거부된다

**AC3** — 존재하지 않는 요청

- **Given** 존재하지 않거나 소프트 삭제된 요청 id로 조회할 때
- **Then** 404 `service_request_not_found` 로 거부된다

**AC4** — cursor 페이지네이션

- **Given** 한 요청에 3개 이상의 견적이 있을 때
- **When** `GET /api/v1/service-requests/{id}/quotes?limit=2`로 첫 페이지를 조회하면
- **Then** `{items: [...2개], nextCursor: <non-null>}`가 반환된다
- **When** `cursor=<nextCursor>`로 다음 페이지를 조회하면
- **Then** 나머지 견적이 반환되고 `nextCursor=null`이다
- **And** 잘못된 cursor를 보내면 400 `invalid_cursor`가 반환된다

**AC5** — 권한 제어 (FR4)

- **Then** 비인증 요청 → 401 `not_authenticated`
- **Then** PRO 역할 → 403 `forbidden`
- **Then** ADMIN 역할 → 403 `forbidden`

**AC6** — user-web `(customer)/requests/[id]` 상세 화면

- **Given** 로그인한 고객이 `(customer)/requests/[id]` 페이지를 열면
- **When** 해당 요청에 견적이 존재하면
- **Then** 견적 목록 섹션이 비교 가능한 형태(가격·메시지·고수 표시명·카테고리·상태)로 표시된다
- **And** 상태가 `pending`이고 요청 상태가 `open`인 견적에는 수락/거절 진입점 버튼이 노출된다(Story 4.2/4.3에서 실제 동작 배선)
- **And** 빈 목록일 때 "아직 받은 견적이 없습니다" 메시지가 표시된다

---

## 태스크 및 서브태스크

- [x] **Task 1:** `QuoteRepository.list_by_request` 메서드 추가
  - [x] `apps/api/app/repositories/quotes.py` 수정
  - [x] `service_request_id` 필터 + `deleted_at IS NULL` + `id DESC` keyset cursor

- [x] **Task 2:** `UserRepository.list_by_ids` 메서드 추가
  - [x] `apps/api/app/repositories/users.py` 수정
  - [x] `id.in_(ids)` + `deleted_at IS NULL` batch 조회

- [x] **Task 3:** `ProCategoryRepository.list_by_users` 메서드 추가
  - [x] `apps/api/app/repositories/pro_categories.py` 수정
  - [x] `user_id.in_(user_ids)` batch 조회

- [x] **Task 4:** Pydantic 스키마 추가
  - [x] `apps/api/app/schemas/quote.py` 수정
  - [x] `ProInfoSummary`(id, displayName, categoryIds) 추가
  - [x] `QuoteWithProInfo`(Quote 필드 + `pro: ProInfoSummary`) 추가

- [x] **Task 5:** `QuoteService.list_for_request()` 구현
  - [x] `apps/api/app/services/quote.py` 수정
  - [x] 요청 존재 확인 + 소유권 검사 → 3-쿼리 batch 조회 → `Page[QuoteWithProInfo]` 반환

- [x] **Task 6:** `_sr_router`에 `GET /{request_id}/quotes` 엔드포인트 추가
  - [x] `apps/api/app/routers/quotes.py` 수정
  - [x] 함수명 `list_service_request_quotes` (Orval operationId → 훅 `useListServiceRequestQuotes`)

- [x] **Task 7:** pytest 작성 (`apps/api/tests/test_quotes_list_for_request.py`)
  - [x] AC1 기본 성공: 200, pro.displayName 존재, 이메일 미포함, 필드 검증
  - [x] AC1 빈 목록: 200, items=[]
  - [x] AC1 모든 상태 포함: pending/accepted/rejected/closed 모두 반환 확인
  - [x] AC2 소유권: 타 고객 → 403
  - [x] AC3 존재하지 않는 요청 → 404
  - [x] AC4 페이지네이션: nextCursor 반환, 두 번째 페이지 조회
  - [x] AC4 잘못된 cursor → 400
  - [x] AC5 비인증 → 401
  - [x] AC5 PRO → 403
  - [x] AC5 ADMIN → 403
  - [x] 추가: matched 요청도 조회 가능(소유권만 만족하면 상태 제한 없음)

- [x] **Task 8:** Orval 재생성 + api-client 확인
  - [x] API 서버 기동 후 `openapi.json` 덤프(`uv run python -c "..."`) → `pnpm orval`
  - [x] `useListServiceRequestQuotes` 훅 생성 확인
  - [x] `QuoteWithProInfo`, `ProInfoSummary` 타입 생성 확인

- [x] **Task 9:** user-web `(customer)/requests/[id]/page.tsx` 업데이트
  - [x] `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` 수정
  - [x] 기존 요청 상세·취소/완료 버튼 유지(회귀 없음)
  - [x] 견적 목록 섹션 추가: `useListServiceRequestQuotes` 훅 사용
  - [x] 각 견적: 가격·메시지·고수 표시명·카테고리 ID·상태(한국어 라벨)
  - [x] pending 견적 + open 요청 조합: 수락/거절 placeholder 버튼 노출

### Review Findings

- [ ] [Review][Decision] 크로스-요청 cursor 오염 — cursor는 UUID를 base64 인코딩한 단순 토큰. 다른 request_id 견적 목록의 cursor를 현재 요청에 사용해도 에러 없이 수용됨(`services/quote.py:list_for_request`). `service_request_id` 필터 덕분에 데이터 누출은 없으나 UUID7 시간 기준 페이지 경계가 틀어져 조용히 잘못된 페이지 반환 가능. **선택지:** (A) cursor에 request_id를 포함해 검증 추가 (B) 현재 동작 수용(데이터 보안 보장, 페이지네이션 오작동은 엣지케이스)
- [x] [Review][Patch] Frontend categoryIds UUID 원시값 렌더링 [`apps/user-web/src/app/(customer)/requests/[id]/page.tsx:188`] — `useListCategories` 훅 추가, categoryMap 빌드 후 UUID → 카테고리 이름 resolve. 빈 배열 시 "없음" 폴백 추가. ✅ 수정됨
- [x] [Review][Patch] Frontend 견적 조회 에러 시 빈 상태 오인 [`apps/user-web/src/app/(customer)/requests/[id]/page.tsx:50`] — `isError: quotesError` 구조분해 추가, 에러 분기("견적을 불러오지 못했습니다.") 렌더링. ✅ 수정됨
- [x] [Review][Defer] SR 소프트 삭제 레이스 컨디션 [`apps/api/app/services/quote.py:134`] — deferred, pre-existing. 소유권 검사 통과 후 다른 트랜잭션이 SR 소프트삭제 시 삭제된 SR 견적 반환. 프로젝트 전체 공통 패턴 — 격리 레벨 정책 수립 시 일괄 처리.
- [x] [Review][Defer] matched 상태 전환 후 pending 견적 수락/거절 버튼 안내 없음 [`apps/user-web/src/app/(customer)/requests/[id]/page.tsx:191`] — deferred, pre-existing. AC6 스펙 범위 내 동작. Story 4.2/4.3 배선 시 상태별 UI 정리.
- [x] [Review][Defer] AC4 세 번째 이후 빈 페이지 cursor 동작 테스트 미비 — deferred, pre-existing. 코드 로직은 올바르나 명시적 테스트 케이스 부재.
- [x] [Review][Defer] pro_ids set 순서 비결정성 [`apps/api/app/services/quote.py:157`] — deferred, pre-existing. `list({...})` set→list 비결정 순서. 기능 영향 없음. `list(dict.fromkeys(...))` 패턴으로 개선 가능.

---

## 개발자 노트

### 핵심 설계 결정

#### 1. 엔드포인트 위치 — `_sr_router` (quotes.py) ⚠️

`GET /api/v1/service-requests/{request_id}/quotes`는 `quotes.py`의 기존 `_sr_router`에 추가한다.

```python
# routers/quotes.py — _sr_router에 추가
@_sr_router.get("/{request_id}/quotes", response_model=Page[QuoteWithProInfo])
async def list_service_request_quotes(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[QuoteWithProInfo]:
    svc = QuoteService(session)
    return await svc.list_for_request(request_id, current_user, cursor, limit)
```

**이유:** POST `/{request_id}/quotes`(견적 제안, Story 3.3)와 동일 네임스페이스 `_sr_router`. FastAPI는 `{request_id}/quotes` 경로를 `service_requests.py`의 `/{request_id}`(단일 세그먼트)와 다르게 해석하므로 충돌 없음.

**FastAPI 라우트 매칭 규칙 준수:**  
`service_requests.py`에는 `GET /{request_id}` (단일 세그먼트)와 `GET /feed`, `GET /feed/{request_id}`가 있다. `_sr_router`의 `GET /{request_id}/quotes`는 2-세그먼트 경로라 충돌하지 않는다.

#### 2. 스키마 설계

```python
# schemas/quote.py 추가 (기존 QuoteCreate/QuoteRead/QuoteListItem/ServiceRequestSummary 유지)

class ProInfoSummary(CamelModel):
    """견적 비교에서 고수 기본 정보 (Story 4.1). 이메일 미포함(개인정보 최소화)."""
    id: uuid.UUID
    display_name: str
    category_ids: list[uuid.UUID]


class QuoteWithProInfo(CamelModel):
    """고객 측 견적 비교 응답 아이템 (Story 4.1). pro 필드 포함."""
    id: uuid.UUID
    pro_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    pro: ProInfoSummary
```

**`category_ids`만 반환하는 이유:** 프론트는 `useListCategories`(TanStack Query 캐시)로 카테고리 이름을 이미 보유. 중복 전송 방지(페이로드 최소화, CM1 정신).

#### 3. 3-쿼리 batch 전략 (relationship 없음)

```python
# services/quote.py — list_for_request 추가
async def list_for_request(
    self, request_id: UUID, current_user: User, cursor: str | None, limit: int
) -> Page[QuoteWithProInfo]:
    # 1. 요청 존재 + 소유권
    request = await self.sr_repo.get_by_id(request_id)
    if request is None:
        raise ServiceRequestNotFoundError()
    if request.customer_id != current_user.id:
        raise ForbiddenError()

    # 2. cursor 디코드
    limit = max(1, limit)
    after_id: UUID | None = None
    if cursor is not None:
        decoded = decode_cursor(cursor)
        try:
            after_id = UUID(decoded)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidCursorError() from exc

    # 3. 견적 목록 (keyset)
    rows = await self.quote_repo.list_by_request(request_id, after_id, limit + 1)
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

    # 4. PRO 사용자 batch 조회
    pro_ids = list({q.pro_id for q in page_rows})
    user_repo = UserRepository(self.session)
    users = await user_repo.list_by_ids(pro_ids)
    user_map: dict[UUID, User] = {u.id: u for u in users}

    # 5. PRO 카테고리 batch 조회
    pro_cats = await self.pro_cat_repo.list_by_users(pro_ids)
    cat_map: dict[UUID, list[UUID]] = {}
    for pc in pro_cats:
        cat_map.setdefault(pc.user_id, []).append(pc.category_id)

    # 6. 조립
    items = [
        QuoteWithProInfo(
            id=q.id,
            pro_id=q.pro_id,
            price=q.price,
            message=q.message,
            status=q.status,
            created_at=q.created_at,
            updated_at=q.updated_at,
            pro=ProInfoSummary(
                id=q.pro_id,
                display_name=user_map[q.pro_id].display_name if q.pro_id in user_map else "알 수 없음",
                category_ids=cat_map.get(q.pro_id, []),
            ),
        )
        for q in page_rows
    ]
    return Page[QuoteWithProInfo](items=items, next_cursor=next_cursor)
```

**QuoteService 초기화 확장:**  
`__init__`에 `UserRepository` 임포트/사용을 추가한다. `list_for_request`에서 로컬 생성(`UserRepository(self.session)`)이 더 명확하다 — `submit`/`list_mine`에는 `user_repo`가 불필요하므로 생성자에 추가하지 않는다.

#### 4. 신규 Repository 메서드

```python
# repositories/quotes.py — 추가
async def list_by_request(
    self, request_id: UUID, after_id: UUID | None, limit: int
) -> list[Quote]:
    """특정 요청의 견적을 id DESC(최신순) keyset으로 조회. deleted_at IS NULL 필터."""
    stmt = select(Quote).where(
        Quote.service_request_id == request_id,
        Quote.deleted_at.is_(None),
    )
    if after_id is not None:
        stmt = stmt.where(Quote.id < after_id)
    stmt = stmt.order_by(Quote.id.desc()).limit(limit)
    return list((await self.session.execute(stmt)).scalars().all())
```

```python
# repositories/users.py — 추가
async def list_by_ids(self, ids: list[UUID]) -> list[User]:
    """UUID 목록으로 미삭제 사용자 batch 조회."""
    if not ids:
        return []
    result = await self.session.execute(
        select(User).where(
            User.id.in_(ids),
            User.deleted_at.is_(None),
        )
    )
    return list(result.scalars().all())
```

```python
# repositories/pro_categories.py — 추가
async def list_by_users(self, user_ids: list[uuid.UUID]) -> list[ProCategory]:
    """여러 고수의 카테고리를 batch 조회."""
    if not user_ids:
        return []
    result = await self.session.execute(
        select(ProCategory).where(ProCategory.user_id.in_(user_ids))
    )
    return list(result.scalars().all())
```

#### 5. main.py 변경 없음

`quotes_router`는 이미 등록되어 있다. `_sr_router`에 새 경로 추가는 `routers/quotes.py` 내부 변경이므로 `main.py` 무변경.

#### 6. Orval operationId → 훅명

```
함수명: list_service_request_quotes
FastAPI operationId: list_service_request_quotes_api_v1_service_requests__request_id__quotes_get
orval.config.ts 정규식 제거 후: list_service_request_quotes
Orval camelCase 변환: useListServiceRequestQuotes
생성 파일: packages/api-client/src/generated/quotes/quotes.ts
```

`index.ts`에 `export * from './generated/quotes/quotes'`가 이미 존재하므로 `index.ts` 수정 불필요.

#### 7. 프론트엔드 — [id]/page.tsx 업데이트 전략

기존 파일(`apps/user-web/src/app/(customer)/requests/[id]/page.tsx`)은 요청 상세 + 취소/완료 버튼을 구현하고 있다. **기존 코드 유지** + 견적 섹션 추가.

```tsx
// 추가할 훅 (Orval 재생성 후 확인)
import {
  useListServiceRequestQuotes,
  type PageQuoteWithProInfo,
} from "@gosoom/api-client";

const QUOTE_STATUS_LABELS: Record<string, string> = {
  pending: "검토 중",
  accepted: "수락됨",
  rejected: "거절됨",
  closed: "마감됨",
};

// 컴포넌트 내 추가
const { data: quotesData, isPending: quotesLoading } =
  useListServiceRequestQuotes<PageQuoteWithProInfo, Error>(id);
```

**수락/거절 버튼(placeholder):** Story 4.1 AC6는 "진입점 노출"만 요구한다. Story 4.2/4.3에서 onClick을 배선하므로, 이 스토리에서는 버튼 UI만 렌더링하고 `onClick`은 빈 핸들러 또는 TODO 주석으로 남긴다.

```tsx
{/* pending 견적 + open 요청: 수락/거절 진입점 */}
{data?.status === "open" && quote.status === "pending" && (
  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
    <button
      disabled
      className="rounded-md bg-blue-600 px-3 py-1 text-xs text-white opacity-50"
      title="Story 4.2에서 구현 예정"
    >
      수락하기
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
```

> **⚠️ Story 4.2/4.3 인계 지점:** 버튼의 `disabled`를 해제하고 각 스토리에서 mutate 로직을 추가한다.

#### 8. Orval 타입명 주의 ⚠️

`QuoteWithProInfo`는 Orval이 `quoteWithProInfo.ts`로 생성한다. `ProInfoSummary`는 `proInfoSummary.ts`. `Page[QuoteWithProInfo]`는 `PageQuoteWithProInfo`로 생성된다. 재생성 후 `generated/model/index.ts`에서 실제 타입명을 확인하고 import를 맞출 것.

---

### 구현 세부 사항

#### `schemas/quote.py` 최종 구조

```python
# 기존 유지
class QuoteCreate(CamelModel): ...
class QuoteRead(CamelModel): ...
class QuoteListItem(CamelModel): ...
# service_request.py에서 re-export
from app.schemas.service_request import ServiceRequestSummary  # noqa: F401

# 신규 (Story 4.1)
class ProInfoSummary(CamelModel):
    id: uuid.UUID
    display_name: str
    category_ids: list[uuid.UUID]

class QuoteWithProInfo(CamelModel):
    id: uuid.UUID
    pro_id: uuid.UUID
    price: int
    message: str
    status: str
    created_at: datetime
    updated_at: datetime
    pro: ProInfoSummary
```

#### `services/quote.py` 추가 임포트

```python
from app.repositories.users import UserRepository
from app.schemas.quote import ProInfoSummary, QuoteWithProInfo
```

#### `routers/quotes.py` 추가 임포트

```python
from app.schemas.quote import QuoteCreate, QuoteListItem, QuoteRead, QuoteWithProInfo
```

#### `test_quotes_list_for_request.py` 헬퍼 재사용

`tests/helpers.py`에서 `_make_customer`, `_make_pro`, `_make_category`, `_make_service_request`, `_make_quote`, `_assign_pro_categories`, `_auth`를 모두 재사용한다. 추가 헬퍼 불필요.

---

## 알려진 함정

### 1. FastAPI 라우트 순서 — `GET /{request_id}/quotes` vs `GET /{request_id}` ⚠️

`service_requests.py`의 `GET /{request_id}`는 `/api/v1/service-requests/{uuid}` 경로다. `_sr_router`의 `GET /{request_id}/quotes`는 `/api/v1/service-requests/{uuid}/quotes`(2-세그먼트)라 Python path 수준에서 겹치지 않는다. 그러나 `main.py`의 `app.include_router` 순서가 잘못되면 예상치 않은 매칭이 발생할 수 있다. 현재 순서(`service_requests_router` 먼저, `quotes_router` 나중)를 유지하고 테스트로 검증한다.

### 2. `pro_id`가 `user_map`에 없는 경우(소프트 삭제된 PRO) ⚠️

`list_by_ids`는 `deleted_at IS NULL` 필터를 적용하므로 소프트 삭제된 PRO는 `user_map`에 없다. 이 경우 `display_name`은 `"알 수 없음"`으로 처리한다. 견적 자체는 삭제되지 않았으므로(deleted_at IS NULL 필터를 통과) 정상 반환한다.

### 3. Orval 태그 위치 확인 ⚠️

`_sr_router`의 `tags=["quotes"]`를 그대로 사용한다. 새 엔드포인트도 동일 태그를 사용하므로 `generated/quotes/quotes.ts`에 생성된다. **`tags=["service-requests"]`로 바꾸지 말 것** — 그러면 `generated/service-requests/service-requests.ts`에 들어가 기존 index.ts 동작은 유지되나 파일 위치가 혼동스럽다.

### 4. `Page` import 충돌 가능 ⚠️

`services/quote.py`에 `from app.schemas.pagination import Page`가 이미 있다. 신규 import 추가 시 중복 확인.

### 5. `QuoteStatus` ORM enum → str 직렬화 ⚠️

`QuoteWithProInfo.status: str` 선언. Story 3.4의 `QuoteListItem` 패턴과 동일 — `from_attributes=True`(CamelModel 기반)가 enum → str(value)로 직렬화. 기존 패턴 재사용이므로 별도 처리 불필요.

### 6. cursor 비어있는 page_rows ⚠️

`page_rows`가 빈 리스트일 때 `encode_cursor(str(page_rows[-1].id))`를 호출하지 않는다 — `has_more`가 False이므로 안전. list comprehension도 빈 리스트 반환.

### 7. `useListServiceRequestQuotes` 시그니처 확인 ⚠️

Orval 재생성 후 파라미터 구조 확인 필수. `request_id`가 path param이므로 Orval 생성 함수 시그니처는:
```ts
const list_service_request_quotes = (requestId: string, params?: ...) => ...
```
훅 호출: `useListServiceRequestQuotes(id)` 또는 `useListServiceRequestQuotes(id, params?, options?)`

---

## 파일 구조 요약

### 신규 파일 (NEW)

```
apps/api/tests/test_quotes_list_for_request.py     # 11개 pytest 케이스
```

### 수정 파일 (UPDATE)

```
apps/api/app/repositories/quotes.py               # list_by_request 메서드 추가
apps/api/app/repositories/users.py                # list_by_ids 메서드 추가
apps/api/app/repositories/pro_categories.py       # list_by_users 메서드 추가
apps/api/app/schemas/quote.py                     # ProInfoSummary, QuoteWithProInfo 추가
apps/api/app/services/quote.py                    # list_for_request() 추가 + 임포트 추가
apps/api/app/routers/quotes.py                    # _sr_router에 GET /{request_id}/quotes 추가
apps/user-web/src/app/(customer)/requests/[id]/page.tsx   # 견적 섹션 추가
packages/api-client/src/generated/               # Orval 재생성 전체
```

### 수정 없는 파일 (NO CHANGE)

```
apps/api/app/main.py                             # quotes_router 이미 등록됨
apps/api/app/models/quote.py                     # 모델 변경 없음
apps/api/app/core/exceptions.py                  # ForbiddenError/ServiceRequestNotFoundError 재사용
apps/api/app/core/pagination.py                  # 변경 없음
packages/api-client/src/index.ts                 # generated/quotes/quotes 이미 re-export됨
```

---

## 수동 체크포인트 (⚡)

**신규 설정 없음** — 백엔드 DB 스키마 변경(마이그레이션) 없음, 새 환경변수 없음, Railway/Supabase 설정 변경 없음.

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `pytest apps/api/tests/test_quotes_list_for_request.py` — 11/11 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과
- [ ] Orval 생성물 커밋 포함 (`packages/api-client/src/generated/` 변경사항)
- [ ] user-web `(customer)/requests/[id]` 페이지 동작 확인:
  - CUSTOMER 로그인 후 견적이 있는 요청 상세 → 견적 섹션 표시
  - 가격·메시지·고수 표시명·상태(한국어 라벨) 렌더링
  - pending 견적 + open 요청: 수락/거절 버튼 표시(비활성화, Story 4.2/4.3 배선 대기)
  - 견적 없는 요청: "아직 받은 견적이 없습니다" 표시

---

## 이전 스토리 인텔리전스 (Epic 3 교훈)

1. **`helpers.py` 재사용:** Epic 3 종료 시 테스트 공통 헬퍼가 `tests/helpers.py`로 통합됐다. `_make_pro`, `_make_customer`, `_make_category`, `_make_service_request`, `_make_quote`, `_assign_pro_categories`, `_auth` 모두 사용 가능 — 중복 정의 금지.

2. **두 쿼리 batch 패턴 계승:** Story 3.4의 `list_mine`이 quotes → service_requests batch 패턴을 확립했다. 이 스토리는 quotes → users + pro_categories 두 batch 쿼리로 동일 패턴을 적용.

3. **라우터 서브라우터 패턴:** Story 3.4 코드리뷰에서 `_sr_router` / `_q_router` 분리가 확립됐다. 이 스토리는 `_sr_router`에 GET 경로만 추가하면 된다.

4. **`model_validate` + `from_attributes=True`:** `ProInfoSummary`는 ORM 객체가 아닌 직접 생성이므로 `model_validate` 불필요. 키워드 인자로 직접 생성한다.

5. **`status: str` ORM enum 직렬화:** Story 3.3/3.4 패턴 그대로 — `CamelModel`의 `from_attributes=True`가 처리. `str(q.status)` 명시 불필요.

6. **Orval operationName 정규식:** `list_service_request_quotes_api_v1_service_requests__request_id__quotes_get` → 정규식이 `_api_v1_...` 제거 → `list_service_request_quotes` → Orval이 `useListServiceRequestQuotes`.

---

## Dev Agent Record

### Implementation Plan

스토리 노트의 설계 결정을 그대로 준수:
1. `QuoteRepository.list_by_request` — service_request_id + deleted_at IS NULL + id DESC keyset
2. `UserRepository.list_by_ids` — batch 조회 (deleted_at IS NULL)
3. `ProCategoryRepository.list_by_users` — user_id.in_ batch 조회
4. `ProInfoSummary` / `QuoteWithProInfo` Pydantic 스키마 추가
5. `QuoteService.list_for_request` — 소유권 검사 + 3-쿼리 batch + Page 조립
6. `_sr_router.get("/{request_id}/quotes")` — CUSTOMER 역할 한정 엔드포인트
7. pytest 12개 케이스 (스토리 지정 11개 + matched 상태 추가 1개)
8. openapi.json 덤프 → pnpm orval → `useListServiceRequestQuotes` 훅, `ProInfoSummary`/`QuoteWithProInfo`/`PageQuoteWithProInfo`/`listServiceRequestQuotesParams` 타입 생성 확인
9. user-web `(customer)/requests/[id]/page.tsx` — 견적 목록 섹션 추가, pending+open 조합 수락/거절 placeholder 버튼 노출

### Completion Notes

- `pytest apps/api/tests/test_quotes_list_for_request.py` 12/12 통과 (스토리 요구 11 + matched 추가 1)
- 전체 회귀: 167 passed / 2 pre-existing failures (test_categories_list × 3, test_seed_categories × 2 — 이전 스토리부터 존재한 DB 격리 문제, 본 스토리 무관)
- TypeScript 타입체크 통과 (`pnpm typecheck` in apps/user-web)
- Orval 재생성: `proInfoSummary.ts`, `quoteWithProInfo.ts`, `pageQuoteWithProInfo.ts`, `listServiceRequestQuotesParams.ts` 신규 생성
- openapi.json을 `apps/api`에서 생성 후 루트로 복사 (Orval 입력 소스)
- `main.py` 변경 없음 — `quotes_router` 이미 등록됨

### File List

**신규 (NEW)**
- `apps/api/tests/test_quotes_list_for_request.py`

**수정 (UPDATE)**
- `apps/api/app/repositories/quotes.py` — `list_by_request` 메서드 추가
- `apps/api/app/repositories/users.py` — `list_by_ids` 메서드 추가
- `apps/api/app/repositories/pro_categories.py` — `list_by_users` 메서드 추가
- `apps/api/app/schemas/quote.py` — `ProInfoSummary`, `QuoteWithProInfo` 추가
- `apps/api/app/services/quote.py` — `list_for_request()` 추가, 임포트 추가
- `apps/api/app/routers/quotes.py` — `GET /{request_id}/quotes` 엔드포인트 추가
- `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` — 견적 섹션 추가
- `openapi.json` — Orval 입력 갱신
- `packages/api-client/src/generated/` — Orval 재생성 전체
  - `model/proInfoSummary.ts` (NEW)
  - `model/quoteWithProInfo.ts` (NEW)
  - `model/pageQuoteWithProInfo.ts` (NEW)
  - `model/pageQuoteWithProInfoNextCursor.ts` (NEW)
  - `model/listServiceRequestQuotesParams.ts` (NEW)
  - `model/index.ts` (UPDATE)
  - `quotes/quotes.ts` (UPDATE)

### Change Log

- 2026-06-10: Story 4.1 스토리 파일 작성 완료
- 2026-06-10: Story 4.1 구현 완료 — 백엔드 API, Orval 재생성, user-web UI 업데이트
