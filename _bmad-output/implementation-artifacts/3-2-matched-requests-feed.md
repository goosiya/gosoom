---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 3.2: 카테고리 매칭 요청 열람

- **Status:** done
- **Epic:** 3 — 고수 카테고리 & 견적 (FR9-12)
- **Story ID / Key:** 3-2 / 3-2-matched-requests-feed
- **작성일:** 2026-06-09

---

## 사용자 스토리

As a 로그인한 고수(PRO),  
내 활동 카테고리와 일치하는 서비스 요청 목록과 상세를 열람하고 싶다.  
So that 견적을 제안할 만한 일감을 발견할 수 있다.

---

## 인수 기준 (BDD)

**AC1** — 피드 목록: `GET /api/v1/service-requests/feed`
- **Given** 고수가 활동 카테고리를 1개 이상 설정했을 때
- **When** `GET /api/v1/service-requests/feed`를 호출하면
- **Then** 고수 카테고리(`pro_categories`)와 일치하는 요청만 `{items, nextCursor}` cursor 페이지네이션으로 최신순(id DESC) 반환된다
- **And** 소프트 삭제된 요청(`deleted_at IS NOT NULL`)은 제외된다
- **And** status=completed 또는 cancelled 요청은 제외된다(open + matched만 포함)

**AC2** — Matched 요청 비활성 표시 (제외 아님)
- **Given** 피드에 포함된 요청이 `matched` 상태가 되었을 때
- **When** 고수가 피드를 조회하면
- **Then** 해당 요청은 목록에서 **제외되지 않고** `status="matched"`로 포함된다
- **And** 클라이언트는 status 필드로 해당 요청이 더 이상 견적 제안 불가임을 인지한다 (R1/FR10)

**AC3** — 피드 상세: `GET /api/v1/service-requests/feed/{id}`
- **Given** 고수가 자신의 카테고리와 일치하는 요청의 상세를 볼 때
- **When** `GET /api/v1/service-requests/feed/{id}`를 호출하면
- **Then** 요청의 id·categoryId·region·description·status·desiredSchedule·budget·createdAt·updatedAt이 반환된다
- **And** 자신의 카테고리에 없는 요청 ID 접근 시 403 `{"code":"forbidden"}` 반환
- **And** 존재하지 않거나 소프트 삭제된 요청 ID 접근 시 404 `{"code":"service_request_not_found"}` 반환

**AC4** — 권한 제어
- **Given** 각 역할/인증 상태에서 피드 목록 또는 상세 접근 시
- **Then** 비인증 → 401, CUSTOMER 역할 → 403, ADMIN 역할 → 403
- **Then** 카테고리 미설정 PRO가 피드 조회 → 빈 목록 `{items:[], nextCursor:null}` 반환 (오류 없음)

**AC5** — user-web `(pro)/feed` 화면
- **Given** user-web `(pro)/feed` 화면에서
- **When** 고수가 피드를 열람하면
- **Then** `open` 요청에는 "견적 제안하기" 진입 링크(Story 3.3 구현 예정이므로 `/feed/[id]`로 이동)가 노출된다
- **And** `matched` 요청에는 "이미 매칭됨" 배지가 표시되어 비활성임을 인지할 수 있다
- **And** `(pro)/feed/[id]` 상세 화면에서 요청 정보(카테고리, 지역, 내용, 상태, 일정, 예산)가 표시된다
- **And** Orval 훅 사용, 로딩·에러 상태 표시

---

## 태스크 및 서브태스크

- [x] **Task 1:** `ServiceRequestRepository.list_by_categories()` 추가
  - [x] `apps/api/app/repositories/service_requests.py`에 새 메서드 추가
  - [x] category_ids IN 필터 + status IN [open, matched] + deleted_at IS NULL + id DESC cursor keyset

- [x] **Task 2:** `ServiceRequestService.get_feed()` + `get_feed_detail()` 추가
  - [x] `apps/api/app/services/service_request.py`에 두 메서드 추가
  - [x] `get_feed`: ProCategoryRepository로 PRO 카테고리 조회 → list_by_categories 호출
  - [x] `get_feed_detail`: get_by_id → 카테고리 일치 검사(ForbiddenError)

- [x] **Task 3:** 라우터에 피드 엔드포인트 추가 (`apps/api/app/routers/service_requests.py`)
  - [x] `GET /feed` 엔드포인트 — **반드시 `/{request_id}` 앞에 삽입**
  - [x] `GET /feed/{request_id}` 엔드포인트 — **반드시 `/{request_id}` 앞에 삽입**
  - [x] 두 엔드포인트 모두 `require_role(PRO)` 가드

- [x] **Task 4:** pytest 작성 (`apps/api/tests/test_service_requests_feed.py`)
  - [x] 피드 목록: 정상, 카테고리 필터, matched 포함, 소프트삭제 제외, 카테고리 미설정 빈목록, cursor 페이지네이션
  - [x] 피드 권한: 비인증 401, CUSTOMER 403, ADMIN 403
  - [x] 피드 상세: 정상(open·matched), 카테고리 불일치 403, not found 404, 비인증 401, CUSTOMER 403

- [x] **Task 5:** user-web 피드 목록 화면 구현
  - [x] `apps/user-web/src/app/(pro)/feed/page.tsx` 생성
  - [x] Orval 훅 사용, open/matched 상태 분기 UI

- [x] **Task 6:** user-web 피드 상세 화면 구현
  - [x] `apps/user-web/src/app/(pro)/feed/[id]/page.tsx` 생성
  - [x] 요청 상세 + 상태 배지

- [x] **Task 7:** Orval 재생성 + api-client index 업데이트
  - [x] API 서버 기동 후 `pnpm orval` 실행
  - [x] `packages/api-client/src/generated/model/index.ts` 확인
  - [x] `packages/api-client/src/index.ts` 새 export 확인

### Review Findings

#### Decision Needed

- [x] [Review][Decision] AC5 "견적 제안하기" 진입 링크 구현 방식 — **→ Patch 전환**: 목록 open 아이템에 "견적 제안하기" 텍스트 CTA 링크 별도 추가
- [x] [Review][Decision] 카테고리 없는 PRO의 feed 상세 → 403 반환 (목록과 비대칭) — **→ 현재 유지(dismiss)**: AC3 "카테고리에 없는 요청 → 403" 규칙 적용이 맞음. KTH 결정.

#### Patches

- [x] [Review][Patch] AC5: 목록 open 아이템에 "견적 제안하기" CTA 링크 추가 [`apps/user-web/src/app/(pro)/feed/page.tsx`]
- [x] [Review][Patch] AC5: 상세 화면(`feed/[id]/page.tsx`)에 categoryId 미표시 — AC5가 "카테고리" 정보 표시를 명시하나 `feed/[id]/page.tsx`에 categoryId 렌더링 없음 [`apps/user-web/src/app/(pro)/feed/[id]/page.tsx`]
- [x] [Review][Patch] AC4: `GET /feed/{id}` ADMIN 역할 403 테스트 누락 — AC4가 "피드 목록 또는 상세 접근 시 ADMIN → 403" 명시하나 상세 엔드포인트 테스트 없음 [`apps/api/tests/test_service_requests_feed.py`]
- [x] [Review][Patch] AC3: `test_feed_detail_success_200`에서 desiredSchedule/budget 필드 단언 누락 — AC3가 두 필드 반환 명시하나 테스트에서 검증 없음 [`apps/api/tests/test_service_requests_feed.py`]
- [x] [Review][Patch] `feed/page.tsx:32` `req.description` null guard 없음 — `description.slice(0, 50)` 직접 호출, Orval 타입이 optional이면 TypeError 런타임 크래시 [`apps/user-web/src/app/(pro)/feed/page.tsx:32`]
- [x] [Review][Patch] cursor 유효 base64+non-UUID 내용 시 InvalidCursorError 경로 테스트 없음 [`apps/api/tests/test_service_requests_feed.py`]

#### Deferred

- [x] [Review][Defer] completed/cancelled 요청 PRO 직접 URL 접근 가능 [`apps/api/app/services/service_request.py:128`] — deferred, 스펙 의도 설계(북마크 허용 목적 — 개발자 노트 명시)
- [x] [Review][Defer] 목록 페이지 cursor 페이지네이션 UI 없음 [`apps/user-web/src/app/(pro)/feed/page.tsx`] — deferred, 현 스토리 스코프 밖 (후속 UX 개선 시)
- [x] [Review][Defer] 프론트엔드 AC5 렌더링 조건 분기 테스트 없음 [`apps/user-web/src/app/(pro)/feed/`] — deferred, E2E/RTL 테스트 인프라 미도입

---

## 개발자 노트

### 핵심 설계 결정

#### 1. 피드 전용 엔드포인트 분리 (`/feed`, `/feed/{id}`)

기존 `GET /api/v1/service-requests/{id}`는 CUSTOMER 전용(소유권 검사)이다. PRO에게 동일 엔드포인트를 재사용하면 소유권 로직이 복잡해지고 기존 CUSTOMER 테스트가 영향받는다. 따라서 피드 전용 엔드포인트를 분리한다:

- `GET /api/v1/service-requests/feed` — PRO 전용 피드 목록
- `GET /api/v1/service-requests/feed/{id}` — PRO 전용 피드 상세

기존 CUSTOMER 엔드포인트(`GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`)는 **무수정 유지**.

#### 2. 상태 필터: open + matched만 포함

PRO 피드에는 `open`(견적 제안 가능) + `matched`(이미 매칭됨, 비활성 표시)만 포함한다.
`completed`, `cancelled` 요청은 거래가 종료된 것으로 피드에서 제외한다.
이는 PRO가 "활성 상태의 일감"만 볼 수 있게 하여 UX를 단순하게 유지한다.

#### 3. 피드 상세는 상태 필터 없음

피드 목록은 open+matched 필터를 적용하지만, 피드 상세(`/feed/{id}`)는 상태에 관계없이 카테고리 일치만 검사한다. 이는 PRO가 직접 링크로 상세에 접근하는 경우(예: 북마크)를 허용하기 위함이다.

#### 4. 카테고리 미설정 PRO → 빈 목록 반환

카테고리가 없는 PRO가 피드를 호출하면 `category_ids`가 빈 배열이 된다. 이때 DB 쿼리를 실행하지 않고 즉시 빈 Page를 반환한다(불필요한 쿼리 방지). 400 오류 반환이 아님에 주의.

#### 5. IDOR 방지

피드 상세에서 PRO는 자신의 카테고리와 일치하는 요청만 열람 가능하다. `get_feed_detail()`에서 `ProCategoryRepository.list_by_user(current_user.id)`로 카테고리를 조회하고, `request.category_id not in category_ids_set` 이면 `ForbiddenError()`를 던진다.

---

### 구현 세부 사항

#### `ServiceRequestRepository` — 신규 메서드

```python
# apps/api/app/repositories/service_requests.py
async def list_by_categories(
    self,
    category_ids: list[uuid.UUID],
    after_id: uuid.UUID | None,
    limit: int,
) -> list[ServiceRequest]:
    """고수 피드: 카테고리 일치 요청(open+matched)을 id DESC로 조회."""
    if not category_ids:
        return []
    stmt = select(ServiceRequest).where(
        ServiceRequest.category_id.in_(category_ids),
        ServiceRequest.deleted_at.is_(None),
        ServiceRequest.status.in_([
            ServiceRequestStatus.OPEN,
            ServiceRequestStatus.MATCHED,
        ]),
    )
    if after_id is not None:
        stmt = stmt.where(ServiceRequest.id < after_id)
    stmt = stmt.order_by(ServiceRequest.id.desc()).limit(limit)
    return list((await self.session.execute(stmt)).scalars().all())
```

`ServiceRequestStatus`는 이미 `service_request.py` 모델에 정의되어 있다. repo에서 임포트할 것.

#### `ServiceRequestService` — 신규 메서드 2개

```python
# apps/api/app/services/service_request.py 상단 임포트 추가
from app.repositories.pro_categories import ProCategoryRepository

# 기존 __init__ 수정 없음 — 각 메서드에서 ProCategoryRepository 인스턴스 생성

async def get_feed(
    self, current_user: User, cursor: str | None, limit: int
) -> Page[ServiceRequestRead]:
    """PRO 피드: 내 카테고리와 일치하는 요청 목록 (open+matched). cursor id DESC."""
    limit = max(1, limit)
    
    pro_cat_repo = ProCategoryRepository(self.session)
    pro_cats = await pro_cat_repo.list_by_user(current_user.id)
    category_ids = [pc.category_id for pc in pro_cats]
    
    if not category_ids:
        return Page[ServiceRequestRead](items=[], next_cursor=None)
    
    after_id: UUID | None = None
    if cursor is not None:
        decoded = decode_cursor(cursor)
        try:
            after_id = UUID(decoded)
        except (ValueError, AttributeError, TypeError) as exc:
            raise InvalidCursorError() from exc
    
    rows = await self.repo.list_by_categories(category_ids, after_id, limit + 1)
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None
    
    return Page[ServiceRequestRead](
        items=[ServiceRequestRead.model_validate(r) for r in page_rows],
        next_cursor=next_cursor,
    )

async def get_feed_detail(
    self, request_id: uuid.UUID, current_user: User
) -> ServiceRequest:
    """PRO 피드 상세: 자신의 카테고리와 일치하는 요청만 열람 가능."""
    request = await self.repo.get_by_id(request_id)
    if request is None:
        raise ServiceRequestNotFoundError()
    
    pro_cat_repo = ProCategoryRepository(self.session)
    pro_cats = await pro_cat_repo.list_by_user(current_user.id)
    category_ids = {pc.category_id for pc in pro_cats}
    
    if request.category_id not in category_ids:
        raise ForbiddenError()
    
    return request
```

`ForbiddenError`를 `exceptions.py`에서 임포트하는 것을 잊지 말 것.

#### `service_requests.py` 라우터 — 신규 엔드포인트 삽입 위치

**⚠️ CRITICAL: 라우터 등록 순서**

FastAPI는 경로를 등록 순서대로 매칭한다. `/{request_id}`는 `/feed`를 포함한 모든 단일 세그먼트 경로를 가로챈다. 따라서 `/feed`와 `/feed/{request_id}`는 반드시 `/{request_id}` **앞에** 등록해야 한다.

올바른 순서:
```python
@router.post("/", ...)           # 1. 요청 생성 (CUSTOMER)
@router.get("/", ...)            # 2. 내 목록 (CUSTOMER)
@router.get("/feed", ...)        # 3. ★ 피드 목록 (PRO) — /{id} 앞
@router.get("/feed/{request_id}", ...)  # 4. ★ 피드 상세 (PRO) — /{id} 앞
@router.get("/{request_id}", ...) # 5. 기존 상세 (CUSTOMER)
@router.patch("/{request_id}", ...) # 6. 기존 상태변경 (CUSTOMER)
```

신규 엔드포인트 시그니처:
```python
@router.get("/feed", response_model=Page[ServiceRequestRead])
async def list_service_request_feed(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[ServiceRequestRead]:
    svc = ServiceRequestService(session)
    return await svc.get_feed(current_user, cursor, limit)


@router.get("/feed/{request_id}", response_model=ServiceRequestRead)
async def get_service_request_feed_detail(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.PRO))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    return await svc.get_feed_detail(request_id, current_user)
```

함수명을 `list_service_request_feed`, `get_service_request_feed_detail`로 지정하면 Orval이 생성하는 훅 이름이 `useListServiceRequestFeed`, `useGetServiceRequestFeedDetail`이 된다.

---

### 테스트 파일 구조 (`test_service_requests_feed.py`)

기존 `test_service_requests_list_detail.py`의 헬퍼 패턴을 참고하되, 새 파일에 독립 헬퍼를 정의한다. `ProCategory` 생성 헬퍼도 필요하다.

```python
# 헬퍼 함수 구조
async def _make_pro(session) -> User: ...        # PRO 역할 유저 생성
async def _make_customer(session) -> User: ...   # CUSTOMER 역할 유저 생성  
async def _make_admin(session) -> User: ...      # ADMIN 역할 유저 생성
async def _make_category(session, name="청소") -> Category: ...  # 카테고리 생성
async def _make_service_request(session, customer, category, status="open") -> ServiceRequest: ...
async def _assign_pro_categories(session, pro, categories: list[Category]): ...  # ProCategory 행 삽입
def _auth(user) -> dict: ...  # {"Authorization": "Bearer <jwt>"}
```

테스트 케이스 목록 (12개):

**피드 목록:**
1. `test_feed_empty_when_no_categories_200` — 카테고리 없는 PRO → 빈 목록, 오류 없음
2. `test_feed_returns_matching_open_requests_200` — 기본 정상: open 요청 반환
3. `test_feed_includes_matched_requests_200` — matched 요청 포함 검증
4. `test_feed_excludes_completed_cancelled` — completed/cancelled 요청 제외
5. `test_feed_excludes_non_matching_categories` — 다른 카테고리 요청 제외
6. `test_feed_excludes_soft_deleted_200` — deleted_at 설정 요청 제외
7. `test_feed_cursor_pagination_200` — limit=1, 2페이지 cursor 페이지네이션 검증
8. `test_feed_no_token_401` — 비인증
9. `test_feed_customer_role_403` — CUSTOMER → 403
10. `test_feed_admin_role_403` — ADMIN → 403

**피드 상세:**
11. `test_feed_detail_success_200` — 정상(카테고리 일치)
12. `test_feed_detail_category_mismatch_403` — 카테고리 불일치 → 403
13. `test_feed_detail_matched_request_visible_200` — matched 요청도 상세 조회 가능
14. `test_feed_detail_not_found_404` — 존재하지 않는 ID
15. `test_feed_detail_no_token_401` — 비인증
16. `test_feed_detail_customer_role_403` — CUSTOMER → 403

(목표: 16개)

---

### user-web 프론트엔드

#### 파일 구조
```
apps/user-web/src/app/(pro)/
├─ layout.tsx        # 기존 — 수정 없음 (PRO 가드)
├─ categories/
│   └─ page.tsx      # 기존 — 수정 없음
└─ feed/             # ★ 신규
    ├─ page.tsx      # 피드 목록
    └─ [id]/
        └─ page.tsx  # 피드 상세
```

#### `(pro)/feed/page.tsx` 핵심 구조

```tsx
"use client";

import Link from "next/link";
import { useListServiceRequestFeed, type PageServiceRequestRead } from "@gosoom/api-client";

export default function FeedPage() {
  const feed = useListServiceRequestFeed<PageServiceRequestRead, Error>();
  
  if (feed.isPending) return <div>로딩 중...</div>;
  if (feed.isError) return <div>피드를 불러오는 중 오류가 발생했습니다.</div>;

  const items = feed.data?.items ?? [];

  return (
    <main style={{ padding: "1.5rem" }}>
      <h1>매칭 요청 피드</h1>
      {items.length === 0 && <p>표시할 요청이 없습니다. 카테고리를 먼저 설정해 주세요.</p>}
      <ul style={{ listStyle: "none", padding: 0 }}>
        {items.map((req) => (
          <li key={req.id} style={{ marginBottom: "1rem", opacity: req.status === "matched" ? 0.5 : 1 }}>
            <Link href={`/feed/${req.id}`}>
              <strong>{req.region}</strong> — {req.description.slice(0, 50)}
              {req.description.length > 50 ? "..." : ""}
            </Link>
            {req.status === "matched" && (
              <span style={{ marginLeft: "0.5rem", color: "gray" }}>[이미 매칭됨]</span>
            )}
            {req.status === "open" && (
              <span style={{ marginLeft: "0.5rem", color: "green" }}>[견적 제안 가능]</span>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
```

#### `(pro)/feed/[id]/page.tsx` 핵심 구조

```tsx
"use client";

import { use } from "react";
import { useGetServiceRequestFeedDetail, type ServiceRequestRead } from "@gosoom/api-client";

export default function FeedDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const detail = useGetServiceRequestFeedDetail<ServiceRequestRead, Error>(id);

  if (detail.isPending) return <div>로딩 중...</div>;
  if (detail.isError) return <div>요청을 불러오는 중 오류가 발생했습니다.</div>;

  const req = detail.data;
  if (!req) return null;

  return (
    <main style={{ padding: "1.5rem" }}>
      <h1>요청 상세</h1>
      <p><strong>지역:</strong> {req.region}</p>
      <p><strong>내용:</strong> {req.description}</p>
      <p><strong>상태:</strong> {req.status === "open" ? "견적 가능" : req.status === "matched" ? "이미 매칭됨" : req.status}</p>
      {req.desiredSchedule && <p><strong>희망 일정:</strong> {req.desiredSchedule}</p>}
      {req.budget != null && <p><strong>예산:</strong> {req.budget.toLocaleString()}원</p>}
      {req.status === "open" && (
        <button disabled style={{ marginTop: "1rem" }}>
          견적 제안하기 (Story 3.3에서 구현 예정)
        </button>
      )}
      {req.status === "matched" && (
        <p style={{ color: "gray" }}>이 요청은 이미 다른 고수와 매칭되었습니다.</p>
      )}
    </main>
  );
}
```

> **Next.js 15+ params는 Promise 타입**: `use(params)`로 언래핑해야 한다. 기존 `(pro)/categories/page.tsx`와 동일 패턴.

---

### Orval 재생성 절차

1. API 서버 실행: `cd apps/api && uvicorn app.main:app --reload --port 8000`
2. openapi.json 갱신: `curl http://localhost:8000/openapi.json > openapi.json`  
   (또는 orval.config.ts 확인 — 자동으로 서버에서 가져올 수도 있음)
3. Orval 실행: `pnpm orval` (프로젝트 루트에서)
4. 생성된 훅 확인:
   - `useListServiceRequestFeed` — 피드 목록
   - `useGetServiceRequestFeedDetail` — 피드 상세
5. `packages/api-client/src/generated/model/index.ts`에 신규 타입이 export되어 있는지 확인
6. `packages/api-client/src/index.ts`에 신규 훅이 re-export되어 있는지 확인

---

## 알려진 함정

### 1. 라우터 순서 — 가장 중요한 함정 ⚠️
`GET /feed`를 `GET /{request_id}` **뒤에** 등록하면 FastAPI가 `/feed` 요청을 `request_id="feed"`로 잘못 매칭한다. 반드시 앞에 삽입할 것. 현재 `service_requests.py` 기준으로 `@router.get("/")` 다음, `@router.get("/{request_id}")` 앞에 삽입.

### 2. `ProCategoryRepository` 임포트
`ServiceRequestService`에서 `ProCategoryRepository`를 임포트해야 한다. 기존 `service_request.py`에는 없는 임포트다. 순환 임포트는 없다(서비스→레포지토리, 역방향 없음).

### 3. `ServiceRequest.status.in_()` SQLAlchemy 사용
`ServiceRequestStatus.OPEN`과 `ServiceRequestStatus.MATCHED`를 `Enum.in_()` 필터에 사용할 때 `ServiceRequestStatus`를 임포트해야 한다. 레포지토리 파일 상단에 모델 임포트가 있는지 확인.

### 4. 카테고리 ID 집합(set) 사용 — 선형 탐색 방지
`get_feed_detail()`에서 PRO 카테고리 일치 검사 시 `list[ProCategory]`를 순회하지 말고 `{pc.category_id for pc in pro_cats}`로 set을 만들어 `O(1)` 조회.

### 5. Orval 훅 이름 충돌 주의
피드 상세 엔드포인트 함수명을 `get_service_request_feed_detail`로 지으면 Orval operationId가 `getServiceRequestFeedDetail`이 된다. 기존 `getServiceRequest` 훅과 이름이 겹치지 않음. 그러나 함수명을 줄여서 `get_feed_detail`로 지으면 operationId가 `getFeedDetail`이 되어 더 짧아진다. 어느 쪽을 선택해도 무방하나 일관성을 유지할 것.

### 6. Page 타입 cursor 필드명
기존 `Page[ServiceRequestRead]` 반환 시 `next_cursor` 필드명을 쓴다. 프론트엔드에서는 Orval이 camelCase로 변환하므로 `nextCursor`로 접근. 기존 패턴과 동일.

### 7. 테스트에서 _make_service_request status 파라미터
matched 상태 요청을 직접 생성할 때 `ServiceRequest(status=ServiceRequestStatus.MATCHED, ...)`로 ORM 객체를 만들고 session.add + flush하면 된다. 상태 전이 API를 통하지 않아도 된다(테스트 헬퍼이므로 직접 DB 삽입 허용).

---

## 파일 구조 요약

### 신규 파일 (NEW)
```
apps/api/tests/test_service_requests_feed.py           # 피드 테스트 (16케이스)
apps/user-web/src/app/(pro)/feed/page.tsx              # 피드 목록 화면
apps/user-web/src/app/(pro)/feed/[id]/page.tsx         # 피드 상세 화면
```

### 수정 파일 (UPDATE)
```
apps/api/app/repositories/service_requests.py  # list_by_categories() 추가
apps/api/app/services/service_request.py       # get_feed(), get_feed_detail() 추가
apps/api/app/routers/service_requests.py       # /feed, /feed/{id} 엔드포인트 추가 (순서 주의)
packages/api-client/src/generated/            # Orval 재생성 전체
packages/api-client/src/index.ts              # 신규 훅 re-export 추가 (Orval 자동)
```

### 수정 없는 파일 (NO CHANGE)
```
apps/api/app/models/service_request.py         # 모델 변경 없음
apps/api/app/schemas/service_request.py        # 스키마 변경 없음 (ServiceRequestRead 재사용)
apps/api/app/core/exceptions.py                # 기존 ForbiddenError, ServiceRequestNotFoundError 재사용
apps/api/app/models/pro_category.py            # 변경 없음
apps/api/app/repositories/pro_categories.py   # 변경 없음 (list_by_user 재사용)
apps/api/app/main.py                           # 라우터 등록 변경 없음 (service_requests_router 이미 등록)
apps/user-web/src/app/(pro)/layout.tsx         # PRO 가드 — 변경 없음
```

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `alembic upgrade head` 통과 (신규 마이그레이션 없음)
- [ ] `pytest apps/api/tests/test_service_requests_feed.py` — 16/16 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과
- [ ] Orval 생성물 커밋 포함 (`packages/api-client/src/generated/` 변경사항)
- [ ] user-web `(pro)/feed` 화면 동작 확인:
  - PRO 로그인 후 `/feed` 접근 → 카테고리 미설정 시 안내 메시지
  - 카테고리 설정 후 `/feed` → 매칭 요청 목록 표시
  - matched 요청에 "이미 매칭됨" 배지 노출
  - 요청 클릭 → `/feed/[id]` 상세 진입

---

## 이전 스토리 인텔리전스 (Story 3.1 교훈)

Story 3.1 리뷰에서 확인된 패턴:

1. **commit() 누락 주의**: `get_feed()`, `get_feed_detail()`은 읽기 전용이므로 commit 불필요. 실수로 commit() 추가하지 말 것.

2. **`current_user.id` 직접 사용**: IDOR 방지를 위해 경로 파라미터나 요청 바디에서 user_id를 받지 않고 항상 `current_user.id` 사용.

3. **`(pro)` 라우트 그룹 디렉터리 먼저 생성**: `feed/` 디렉터리와 `feed/[id]/` 디렉터리를 먼저 생성 후 파일 작성.

4. **라우터 등록 순서**: Story 3.1에서 고정 경로 먼저 등록 패턴이 이미 문서화됨. 이 스토리에서도 동일하게 적용.

5. **CamelModel 경계**: `ServiceRequestRead`는 이미 `CamelModel` 기반이므로 JSON 직렬화 시 camelCase로 변환됨. Orval 훅도 camelCase 타입 생성.

6. **두 GET API 혼동 주의**: 기존 `GET /` (CUSTOMER 본인 목록)와 신규 `GET /feed` (PRO 피드)는 완전히 다른 엔드포인트. 실수로 기존 엔드포인트를 수정하지 말 것.

---

## Dev Agent Record

- **Model:** claude-sonnet-4-6
- **구현 중 발견한 사항:**
  - `categories/page.tsx`에 `useListCategories({ params: { limit: 100 } })` → `useListCategories({ limit: 100 })` pre-existing TypeScript 버그 수정 (Orval 훅 시그니처 불일치)
  - 기존 `test_categories_list.py` 3건 + `test_seed_categories.py` 2건 pre-existing 실패 확인 (내 변경과 무관)
  - 16개 피드 테스트 전부 1회 통과 (red→green 사이클 완료)
  - Orval 재생성 후 `useListServiceRequestFeed`, `useGetServiceRequestFeedDetail` 훅 정상 생성 확인

## 파일 목록

### 신규 파일 (NEW)
- `apps/api/tests/test_service_requests_feed.py` — 피드 테스트 16케이스
- `apps/user-web/src/app/(pro)/feed/page.tsx` — 피드 목록 화면
- `apps/user-web/src/app/(pro)/feed/[id]/page.tsx` — 피드 상세 화면
- `packages/api-client/src/generated/model/listServiceRequestFeedParams.ts` — Orval 생성
- `packages/api-client/src/generated/service-requests/service-requests.ts` — Orval 생성

### 수정 파일 (UPDATE)
- `apps/api/app/repositories/service_requests.py` — `list_by_categories()` 추가
- `apps/api/app/services/service_request.py` — `get_feed()`, `get_feed_detail()` 추가, `ForbiddenError`/`ProCategoryRepository` 임포트 추가
- `apps/api/app/routers/service_requests.py` — `/feed`, `/feed/{id}` 엔드포인트 추가
- `apps/user-web/src/app/(pro)/categories/page.tsx` — `useListCategories` 인자 버그 수정 (`{ params: { limit: 100 } }` → `{ limit: 100 }`)
- `packages/api-client/src/generated/model/index.ts` — Orval 재생성

## 변경 이력

- 2026-06-09: Story 3.2 구현 완료 — PRO 피드 엔드포인트(백엔드) + 피드 목록/상세 화면(프론트) + 16개 pytest + Orval 재생성
