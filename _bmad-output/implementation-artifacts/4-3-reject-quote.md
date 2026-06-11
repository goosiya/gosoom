---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 4.3: 견적 거절

- **Status:** done
- **Epic:** 4 — 매칭 & 채팅 (거래 루프 완결) (FR8, FR13-18)
- **Story ID / Key:** 4-3 / 4-3-reject-quote
- **작성일:** 2026-06-11

---

## 사용자 스토리

As a 로그인한 고객(CUSTOMER),
내 요청에 들어온 견적 중 마음에 들지 않는 것을 명시적으로 거절하고 싶다.
So that 원치 않는 견적을 정리하면서도 다른 견적은 계속 검토하고 수락할 수 있다.

---

## 인수 기준 (BDD)

**AC1** — 견적 거절 성공 (FR14)

- **Given** 본인 `open` 요청의 `pending` 견적이 있을 때
- **When** 고객이 `POST /api/v1/quotes/{id}/reject`를 호출하면
- **Then** 해당 견적의 상태가 `pending` → `rejected`로 전환된다
- **And** 서비스 요청 상태는 `open`으로 유지된다 (변경 없음)
- **And** 응답으로 거절된 견적 정보(`QuoteRead`)가 200으로 반환된다

**AC2** — 고수 견적 목록에 거절 상태 반영 (FR12)

- **Given** 견적이 거절되었을 때
- **When** 해당 고수가 `GET /api/v1/quotes` (내 견적 목록)를 조회하면
- **Then** 해당 견적의 `status`가 `rejected`로 반영되어 나타난다

**AC3** — 거부 케이스

- **Given** 본인 요청이 아닌 견적을 거절하려 할 때
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

- **Given** Story 4.2에서 비활성화(`disabled`) 상태로 남겨진 "거절하기" 버튼이 있을 때
- **When** 고객이 "거절하기" 버튼을 클릭하면
- **Then** `POST /api/v1/quotes/{id}/reject`가 호출되고
- **And** 성공 시 해당 요청의 견적 목록 TanStack Query 캐시가 무효화·갱신되며
- **And** 화면에서 해당 견적의 상태가 "거절됨"으로 업데이트된다
- **And** 처리 중에는 버튼이 `disabled` + 로딩 텍스트로 표시된다
- **And** 에러 시 에러 메시지가 표시된다

---

## 태스크 및 서브태스크

- [x] **Task 1:** `QuoteNotPendingError` 메시지 일반화
  - [x] `apps/api/app/core/exceptions.py` 수정
  - [x] `message` 변경: `"pending 상태의 견적만 수락할 수 있습니다."` → `"pending 상태의 견적만 변경할 수 있습니다."`
  - [x] `docstring`에 Story 4.3 참조 추가

- [x] **Task 2:** `QuoteService.reject()` 구현
  - [x] `apps/api/app/services/quote.py` 수정
  - [x] `reject(quote_id: UUID, current_user: User) -> Quote` 메서드 추가
  - [x] 견적 조회 (404) → 서비스 요청 조회 (소유권 확인용) → 소유권 검사 (403) → 상태 검사 (409) → `REJECTED` 전환 → commit → refresh → return

- [x] **Task 3:** 라우터에 `POST /{quote_id}/reject` 엔드포인트 추가
  - [x] `apps/api/app/routers/quotes.py` 수정
  - [x] `_q_router.post("/{quote_id}/reject", ...)` — CUSTOMER 역할 한정
  - [x] `response_model=QuoteRead`, `status_code=200`

- [x] **Task 4:** pytest 작성 (`apps/api/tests/test_quotes_reject.py`)
  - [x] AC1 거절 성공: 200, quote.status → rejected, sr.status → open (변경 없음)
  - [x] AC3 소유권: 타 고객 → 403 `forbidden`
  - [x] AC3 견적 not pending (`accepted`) → 409 `quote_not_pending`
  - [x] AC3 견적 not pending (`rejected`) → 409 `quote_not_pending`
  - [x] AC3 견적 not pending (`closed`) → 409 `quote_not_pending`
  - [x] AC3 존재하지 않는 견적 → 404 `quote_not_found`
  - [x] AC4 비인증 → 401 `not_authenticated`
  - [x] AC4 PRO 역할 → 403 `forbidden`
  - [x] AC4 ADMIN 역할 → 403 `forbidden`

- [x] **Task 5:** Orval 재생성 + api-client 확인
  - [x] API 서버 기동 후 `openapi.json` 덤프 → `pnpm orval`
  - [x] `useRejectQuote` 훅 생성 확인 (`packages/api-client/src/generated/quotes/quotes.ts`)
  - [x] `QuoteRead` 타입은 이미 존재하므로 신규 타입 파일 없음

- [x] **Task 6:** user-web "거절하기" 버튼 활성화
  - [x] `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` 수정
  - [x] `useRejectQuote` import 추가 (Orval 재생성 후)
  - [x] `rejectMutation` hook 추가
  - [x] "거절하기" 버튼 `disabled` 해제, `title` 제거, `onClick` 핸들러 배선
  - [x] 거절 성공 후 견적 목록 캐시 무효화 (`getListServiceRequestQuotesQueryKey`)
  - [x] 처리 중 버튼 `disabled` + 에러 메시지 표시

---

## 개발자 노트

### 핵심 설계 결정

#### 1. 엔드포인트 위치 — `_q_router` (quotes.py)

`POST /api/v1/quotes/{quote_id}/reject`는 `accept`와 동일하게 **`_q_router`** (`/api/v1/quotes`)에 추가한다.

```python
# routers/quotes.py — _q_router에 추가
@_q_router.post("/{quote_id}/reject", response_model=QuoteRead, status_code=200)
async def reject_quote(
    quote_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> QuoteRead:
    svc = QuoteService(session)
    return await svc.reject(quote_id, current_user)
```

**응답:** `QuoteRead` 200 — 업데이트된 견적 객체 반환. `ChatRoomRead`를 반환하는 `accept`와 달리, `reject`는 신규 리소스를 생성하지 않으므로 업데이트된 `Quote` ORM 객체를 직접 반환하고 FastAPI가 `response_model=QuoteRead`로 직렬화한다.

**operationId 예측:**
```
함수명: reject_quote
FastAPI operationId: reject_quote_api_v1_quotes__quote_id__reject_post
orval.config.ts 정규식 제거 후: reject_quote
Orval camelCase 변환: useRejectQuote
생성 파일: packages/api-client/src/generated/quotes/quotes.ts
```

**`main.py` 변경 없음:** `quotes_router`는 `main.py`에 이미 등록됨. `_q_router`에 엔드포인트 추가만으로 충분.

#### 2. `QuoteService.reject()` 구현

`accept()`에 비해 단순하다 — 상태 전이가 단일 행(견적 1개)이고, 원자성 문제나 race condition이 없다.

```python
# services/quote.py — reject() 추가
async def reject(self, quote_id: UUID, current_user: User) -> Quote:
    """견적 거절 — 단일 견적 상태 전이 (AC1, FR14).

    순서:
    1. 견적 존재 확인
    2. 서비스 요청 조회 (소유권 확인용 — FOR UPDATE 불필요)
    3. 소유권 검사 (본인 요청의 견적만)
    4. 견적 상태 PENDING 검사
    5. 거절 처리 → commit → refresh
    """
    # 1. 견적 존재 확인
    quote = await self.quote_repo.get_by_id(quote_id)
    if quote is None:
        raise QuoteNotFoundError()

    # 2. 서비스 요청 조회 (소유권 확인용)
    request = await self.sr_repo.get_by_id(quote.service_request_id)
    if request is None:
        raise ServiceRequestNotFoundError()

    # 3. 소유권 검사 — 본인 요청의 견적만 거절 가능
    if request.customer_id != current_user.id:
        raise ForbiddenError()

    # 4. 견적 상태 검사 — pending만 거절 가능
    if quote.status != QuoteStatus.PENDING:
        raise QuoteNotPendingError()

    # 5. 거절 처리
    quote.status = QuoteStatus.REJECTED
    await self.session.commit()
    await self.session.refresh(quote)
    return quote
```

**`SELECT ... FOR UPDATE` 미사용 이유:** `accept()`와 달리 단일 견적 행의 상태만 변경하며, 요청 상태 변경·채팅방 생성·다중 행 bulk update가 없다. 동시에 두 클라이언트가 동일 견적을 reject해도 결과는 동일(`REJECTED`)하므로 race condition이 없다.

**`accept()`에서 이미 import된 예외 재사용:** `QuoteNotFoundError`, `ForbiddenError`, `QuoteNotPendingError`, `ServiceRequestNotFoundError` 모두 이미 `services/quote.py`에 import됨. 신규 import 불필요.

#### 3. `QuoteNotPendingError` 메시지 일반화

현재 메시지: `"pending 상태의 견적만 수락할 수 있습니다."` → `accept` 전용 문구.
변경 후: `"pending 상태의 견적만 변경할 수 있습니다."` — accept·reject 양쪽에 적용 가능.

```python
# exceptions.py 수정
class QuoteNotPendingError(AppError):
    """pending이 아닌 견적에 상태 변경(수락/거절)을 시도할 때(Story 4.2 AC3, Story 4.3 AC3). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="quote_not_pending",
            message="pending 상태의 견적만 변경할 수 있습니다.",
            status_code=409,
        )
```

**`code`는 유지:** `quote_not_pending`은 프론트엔드·API 클라이언트가 기계 판독하는 안정 식별자. 변경 금지.

#### 4. `services/quote.py` 추가 import 없음

`reject()`에서 사용하는 모든 심볼은 이미 파일 상단에 import됨:
- `QuoteNotFoundError`, `ForbiddenError`, `QuoteNotPendingError`, `ServiceRequestNotFoundError` ✅
- `QuoteStatus`, `QuoteRepository`, `ServiceRequestRepository` ✅

#### 5. 프론트엔드 — 거절 버튼 활성화

현재 상태 (`page.tsx` line 232-238):
```tsx
<button
  disabled
  className="rounded-md bg-red-500 px-3 py-1 text-xs text-white opacity-50"
  title="Story 4.3에서 구현 예정"
>
  거절하기
</button>
```

Story 4.3 변경:
```tsx
// 파일 상단 import 추가
import {
  useRejectQuote,  // 신규 (Orval 재생성 후)
  // ... 기존 imports 유지
} from "@gosoom/api-client";

// 컴포넌트 내 mutation 추가 (acceptMutation 아래)
const rejectMutation = useRejectQuote({
  mutation: {
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
    },
  },
});

// 견적 카드 내 거절 버튼 교체
{data.status === "open" && quote.status === "pending" && (
  <div className="flex flex-col gap-1 mt-2">
    <div className="flex gap-2">
      <button
        onClick={() => acceptMutation.mutate({ quoteId: quote.id })}
        disabled={acceptMutation.isPending}
        className="rounded-md bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {acceptMutation.isPending ? "처리 중…" : "수락하기"}
      </button>
      <button
        onClick={() => rejectMutation.mutate({ quoteId: quote.id })}
        disabled={rejectMutation.isPending}
        className="rounded-md bg-red-500 px-3 py-1 text-xs text-white hover:bg-red-600 disabled:opacity-50"
      >
        {rejectMutation.isPending ? "처리 중…" : "거절하기"}
      </button>
    </div>
    {acceptMutation.isError && (
      <p className="text-red-600 text-xs" role="alert">
        수락 처리에 실패했습니다.
      </p>
    )}
    {rejectMutation.isError && (
      <p className="text-red-600 text-xs" role="alert">
        거절 처리에 실패했습니다.
      </p>
    )}
  </div>
)}
```

**⚠️ `useRejectQuote` 훅 파라미터 확인:** Orval이 생성할 시그니처는 `useAcceptQuote`와 동일한 패턴:
```ts
// packages/api-client/src/generated/quotes/quotes.ts에서 확인
rejectMutation.mutate({ quoteId: quote.id })
```
Orval 재생성 후 실제 파라미터 구조 확인 필수.

**거절 후 네비게이션 없음:** `accept`와 달리 `reject`는 채팅방으로 이동하지 않는다. 성공 시 견적 목록만 무효화하여 화면이 자동 갱신된다. `getListServiceRequestQuotesQueryKey(id)` 하나만 무효화하면 충분.

#### 6. Orval 태그 확인

`_q_router`는 `tags=["quotes"]`이므로 새 엔드포인트도 `quotes/quotes.ts`에 생성됨.
`packages/api-client/src/index.ts`의 `export * from './generated/quotes/quotes'`가 이미 있으므로 `index.ts` 변경 불필요.

---

### 알려진 함정

#### 1. 신규 알렉빅 마이그레이션 없음 ✅

이 스토리는 새 테이블·컬럼·인덱스를 추가하지 않는다. `quotes` 테이블의 `status` 컬럼은 이미 `rejected` 값을 허용한다 (`QuoteStatus` Enum에 이미 정의됨).

#### 2. `QuoteRead` 직렬화 ✅

`QuoteService.reject()`는 `Quote` ORM 객체를 반환한다. 라우터의 `response_model=QuoteRead`가 `CamelModel.from_attributes=True`로 자동 직렬화 처리한다. `model_validate()` 명시 호출 불필요.

#### 3. `updated_at` 자동 업데이트 확인 ⚠️

`Quote` 모델의 `updated_at`이 SQLAlchemy `onupdate=func.now()`으로 정의되어 있다면 commit 시 자동 갱신된다. `session.refresh(quote)` 호출 후 `QuoteRead.updated_at`에 새 타임스탬프가 반영된다. 모델 정의를 확인하고, 만약 `onupdate`가 없다면 수동으로 `quote.updated_at = func.now()`를 추가해야 한다.

> **확인 방법:** `apps/api/app/models/quote.py`의 `updated_at` 컬럼 정의 확인.

#### 4. `rejectMutation`은 컴포넌트 레벨 (quote 카드별 아님) ⚠️

현재 `acceptMutation`과 동일하게 `rejectMutation`도 컴포넌트 최상단에 정의된다. 여러 pending 견적이 있을 때 하나의 견적을 거절 중이면 다른 pending 견적의 거절 버튼도 `isPending` 상태가 된다. 이는 UX 제약이지만 MVP에서 허용 가능한 단순화다.

#### 5. 동시 수락+거절 race ⚠️

고객이 동시에 수락과 거절을 시도할 수 없다 (UI가 단일 클릭 기반). 그러나 만약 `accept`와 `reject`가 동시에 서버에 도달하면:
- `accept`가 먼저 완료 → 견적이 `accepted`로 전환 → `reject`가 `QuoteNotPendingError` (409) 반환 → 자연스럽게 처리됨
- `reject`가 먼저 완료 → 견적이 `rejected`로 전환 → `accept`가 `QuoteNotPendingError` (409) 반환 → 자연스럽게 처리됨

별도 보호 메커니즘 불필요.

#### 6. `service_request.status` 검사 여부 ⚠️

`reject`에서 요청이 이미 `matched`인 경우를 별도로 차단할 필요가 없다. 이미 수락된 요청의 견적들은 모두 `accepted` 또는 `closed` 상태이므로, `QuoteNotPendingError` (409)가 자연스럽게 거절 시도를 차단한다. 별도 `ServiceRequestAlreadyMatchedError` 검사 불필요.

---

### 구현 세부 사항

#### `services/quote.py` 최종 import 목록 (변경 없음)

```python
from app.core.exceptions import (
    DuplicateQuoteError,
    ForbiddenError,
    InvalidCursorError,
    QuoteNotFoundError,
    QuoteNotPendingError,
    ServiceRequestAlreadyMatchedError,
    ServiceRequestNotFoundError,
    ServiceRequestNotOpenForQuoteError,
)
```

`reject()`는 위 중 `QuoteNotFoundError`, `ForbiddenError`, `QuoteNotPendingError`, `ServiceRequestNotFoundError`를 사용한다. **모두 이미 import됨** — 추가 import 없음.

#### `routers/quotes.py` 추가 import

`QuoteRead`는 이미 import됨:
```python
from app.schemas.quote import QuoteCreate, QuoteListItem, QuoteRead, QuoteWithProInfo
```
추가 import 없음.

#### `test_quotes_reject.py` 헬퍼 재사용

`tests/helpers.py`의 모든 헬퍼 그대로 재사용:
- `_make_customer`, `_make_pro`, `_make_admin`, `_make_category`
- `_make_service_request`, `_make_quote`, `_auth`

**거절 성공 검증 핵심:**
```python
resp = await client_db.post(
    f"/api/v1/quotes/{quote.id}/reject", headers=_auth(customer)
)
assert resp.status_code == 200, resp.text
data = resp.json()
assert data["id"] == str(quote.id)
assert data["status"] == "rejected"

# DB 상태 검증 — sr.status는 open 유지
await db_session.refresh(quote)
assert quote.status == QuoteStatus.REJECTED

await db_session.refresh(sr)
assert sr.status == ServiceRequestStatus.OPEN  # 변경 없음
```

---

## 파일 구조 요약

### 신규 파일 (NEW)

```
apps/api/tests/test_quotes_reject.py    # 9개 pytest 케이스
```

### 수정 파일 (UPDATE)

```
apps/api/app/core/exceptions.py                           # QuoteNotPendingError 메시지 일반화
apps/api/app/services/quote.py                            # reject() 메서드 추가
apps/api/app/routers/quotes.py                            # _q_router에 POST /{quote_id}/reject 추가
apps/user-web/src/app/(customer)/requests/[id]/page.tsx   # 거절하기 버튼 활성화
openapi.json                                               # Orval 입력 갱신
packages/api-client/src/generated/quotes/quotes.ts        # useRejectQuote 훅 추가 (Orval)
```

### 수정 없는 파일 (NO CHANGE)

```
apps/api/alembic/versions/            # 마이그레이션 없음 (스키마 변경 없음)
apps/api/app/models/quote.py          # 모델 변경 없음
apps/api/app/schemas/quote.py         # QuoteRead 이미 존재, 변경 없음
apps/api/app/repositories/quotes.py   # 추가 메서드 불필요
apps/api/app/main.py                  # quotes_router 이미 등록됨
packages/api-client/src/index.ts      # generated/quotes/quotes 이미 re-export됨
packages/api-client/src/generated/model/  # QuoteRead 타입 이미 존재
```

---

## 수동 체크포인트 (⚡)

**신규 설정 없음** — 새 환경변수 없음, Railway/Supabase 설정 변경 없음, DB 마이그레이션 없음.

---

## 스토리 완료 기준 (Definition of Done)

- [ ] `pytest apps/api/tests/test_quotes_reject.py` — 9/9 통과
- [ ] 기존 테스트 회귀 없음: `pytest apps/api/` 전체 통과 (특히 `test_quotes_accept.py` 재확인)
- [ ] `pnpm typecheck` + `pnpm lint` + `pnpm build` 통과 (apps/user-web)
- [ ] Orval 생성물 커밋 포함 (`packages/api-client/src/generated/quotes/quotes.ts` 변경사항)
- [ ] user-web `(customer)/requests/[id]` 거절 버튼 동작 확인:
  - CUSTOMER 로그인 → 요청 상세 → pending 견적 "거절하기" 클릭
  - 처리 중 버튼 비활성화 확인
  - 성공 후 견적 상태가 "거절됨"으로 갱신
  - 에러 시 메시지 표시 확인

---

## 이전 스토리 인텔리전스 (Story 4.2 교훈)

1. **`CamelModel.from_attributes=True` 자동 처리:** 라우터의 `response_model`이 ORM → Pydantic 변환을 처리한다. `model_validate()` 명시 불필요. `reject()`가 `Quote` ORM 객체를 반환하면 `QuoteRead` 직렬화는 자동.

2. **helpers.py `_make_quote(status=QuoteStatus.REJECTED)` 패턴:** `_make_quote`의 `status` 파라미터로 다양한 상태 견적 생성 가능. AC3 테스트에서 `accepted`, `rejected`, `closed` 각각 생성하여 409 검증.

3. **`main.py` 변경 없음 확인:** `quotes_router`는 `main.py:124`에 이미 등록됨. `_q_router.post("/{quote_id}/reject", ...)` 추가만으로 충분.

4. **Orval 재생성 후 훅 파라미터 확인 필수:** `useRejectQuote` 훅의 `mutate` 파라미터 구조를 `packages/api-client/src/generated/quotes/quotes.ts`에서 반드시 확인 후 프론트엔드 코드 작성.

5. **`IntegrityError` 처리 불필요:** `reject()`는 `accept()`와 달리 `chat_rooms`에 INSERT가 없고 unique index 충돌이 없다. `try/except IntegrityError` 불필요 — commit만 하면 됨.

6. **`session.refresh(quote)` 필수:** commit 후 ORM 객체의 `updated_at` 등 DB 서버 기본값이 갱신된다. `refresh()` 없이 반환하면 stale 데이터가 응답에 포함될 수 있다.

---

## Dev Agent Record

### Completion Notes

- Task 1: `QuoteNotPendingError` 메시지를 수락/거절 양쪽에 범용적으로 적용 가능하도록 일반화 (`수락` → `변경`), docstring에 Story 4.3 AC3 참조 추가
- Task 2: `QuoteService.reject()` 구현 — SELECT FOR UPDATE 불필요(단일 행 변경, race condition 없음), 기존 import 재사용으로 신규 import 0건
- Task 3: `_q_router`에 `POST /{quote_id}/reject` 추가 — `response_model=QuoteRead`, CUSTOMER 역할 한정
- Task 4: `test_quotes_reject.py` 9개 케이스 작성, 9/9 통과, 전체 201개 테스트 회귀 없음
- Task 5: API 서버 기동 후 `openapi.json` 덤프, `pnpm orval` 실행 → `useRejectQuote` 훅 생성 확인 (`mutate({ quoteId: string })`)
- Task 6: `page.tsx`에 `useRejectQuote` import, `rejectMutation` 추가, 거절 버튼 활성화 (처리 중 disabled + 에러 표시), `pnpm typecheck` + `lint` + `build` 통과

### File List

- `apps/api/app/core/exceptions.py` — QuoteNotPendingError 메시지/docstring 수정
- `apps/api/app/services/quote.py` — reject() 메서드 추가
- `apps/api/app/routers/quotes.py` — POST /{quote_id}/reject 엔드포인트 추가
- `apps/api/tests/test_quotes_reject.py` — 신규 (9개 pytest 케이스)
- `openapi.json` — Orval 입력 갱신
- `packages/api-client/src/generated/quotes/quotes.ts` — useRejectQuote 훅 추가 (Orval 생성)
- `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` — 거절하기 버튼 활성화

### Change Log

- 2026-06-11: Story 4.3 스토리 파일 작성 완료
- 2026-06-11: Story 4.3 구현 완료 — 백엔드 reject 엔드포인트, Orval 재생성, 프론트엔드 버튼 활성화
- 2026-06-11: Story 4.3 코드 리뷰 완료 — patch 0건, decision-needed 0건, defer 3건, dismiss 11건 → done

---

### Review Findings

- [x] [Review][Defer] 거절 실패 에러 코드별 메시지 미분기 [`apps/user-web/src/app/(customer)/requests/[id]/page.tsx`] — deferred, pre-existing UX 패턴 (`rejectMutation.isError` 시 단일 문자열 고정; 409/403/404 구분 없음)
- [x] [Review][Defer] `ServiceRequestNotFoundError` 경로 미테스트 (orphan quote) [`apps/api/tests/test_quotes_reject.py`] — deferred, 데이터 무결성 엣지케이스 (FK 제약 하에서 현재 도달 불가능)
- [x] [Review][Defer] 소프트삭제 SR의 견적 거절 시 404 반환 정책 미문서화 — deferred, pre-existing 시스템 동작 (SR 소프트삭제 경로 Epic 6 범위)
