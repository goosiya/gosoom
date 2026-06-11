---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 2.3: 요청 상태 관리 (취소·완료)

**Status:** done  
**Epic:** 2 — 고객 서비스 요청 (FR5-7)  
**Story ID:** 2-3  
**Story Key:** 2-3-request-status-management  
**작성일:** 2026-06-09  
**Author:** KTH (bmad-create-story 자동 생성)

---

## 사용자 스토리

**As a** 로그인한 고객(CUSTOMER)으로서,  
**I want** 내 서비스 요청을 취소하거나 거래 종료 시 완료 처리하고 싶다.  
**So that** 요청의 생애주기를 직접 관리할 수 있다.

---

## 인수 기준 (BDD)

### AC1 — 요청 취소 (open → cancelled, FR7)

```
Given `open` 상태의 본인 요청이 있을 때
When PATCH /api/v1/service-requests/{id}에 {"action": "cancel"}을 보내면
Then 상태가 `cancelled`로 전이되고 업데이트된 요청이 200으로 반환된다
And service 계층이 전이 규칙을 단일 시행한다(NFR4)
```

### AC2 — 요청 완료 (matched → completed, FR7)

```
Given `matched` 상태의 본인 요청이 있을 때
When PATCH /api/v1/service-requests/{id}에 {"action": "complete"}를 보내면
Then 상태가 `completed`로 전이되고 업데이트된 요청이 200으로 반환된다
```

### AC3 — 허용되지 않는 전이 거부 (NFR7)

```
Given 이미 `cancelled` 또는 `completed` 상태의 요청이거나,
      `matched` 요청에 cancel, `open` 요청에 complete를 시도하면
When PATCH /api/v1/service-requests/{id}를 호출하면
Then 409 Conflict + {code: "invalid_status_transition"}이 반환된다
And 어떤 상태도 변경되지 않는다(원자성)
```

### AC4 — 권한 제어 (FR4)

```
Given 타인의 요청 id일 때
When PATCH 엔드포인트를 호출하면
Then 403 Forbidden + {code: "forbidden"}이 반환된다

Given 비인증이거나 비활성 고객일 때
When 호출하면
Then 401이 반환된다

Given PRO 또는 ADMIN 역할의 사용자가
When PATCH 엔드포인트를 호출하면
Then 403 Forbidden이 반환된다

Given 존재하지 않는 요청 id일 때
When 호출하면
Then 404 Not Found + {code: "service_request_not_found"}이 반환된다
```

### AC5 — user-web 상세 화면 상태 관리 버튼 (FR7)

```
Given 로그인한 CUSTOMER가 요청 상세(/requests/[id])에 접근하면
When 현재 요청 상태가 `open`이면
Then "취소하기" 버튼이 표시된다

When 현재 요청 상태가 `matched`이면
Then "완료하기" 버튼이 표시된다

When 버튼을 클릭하면
Then PATCH 요청이 전송되고
And 성공 시 TanStack Query 캐시(상세 + 목록)가 무효화·갱신되어 상태가 즉시 업데이트된다

When 상태가 `completed` 또는 `cancelled`이면
Then 액션 버튼이 표시되지 않는다(최종 상태)

When 뮤테이션이 진행 중이면
Then 버튼이 disabled 처리된다(중복 클릭 방지)
```

---

## 태스크 및 서브태스크

### Task 1 — 예외 추가 (`apps/api/app/core/exceptions.py` UPDATE)

- [x] 파일 끝에 `InvalidStatusTransitionError` 추가 (409):
  ```python
  class InvalidStatusTransitionError(AppError):
      """허용되지 않는 상태 전이 시도(Story 2.3 AC3). 409."""

      def __init__(self) -> None:
          super().__init__(
              code="invalid_status_transition",
              message="허용되지 않는 상태 전이입니다.",
              status_code=409,
          )
  ```
- [x] 기존 예외(`ServiceRequestNotFoundError` 등) 파괴하지 않음 — 파일 끝에만 append

### Task 2 — 스키마 추가 (`apps/api/app/schemas/service_request.py` UPDATE)

- [x] `from typing import Literal` import 추가 (파일 상단 import 블록에)
- [x] 파일 끝에 `ServiceRequestStatusUpdate` 스키마 추가:
  ```python
  class ServiceRequestStatusUpdate(CamelModel):
      action: Literal["cancel", "complete"]
  ```
- [x] 기존 `ServiceRequestCreate`, `ServiceRequestRead` 파괴하지 않음

### Task 3 — 레포지토리 확장 (`apps/api/app/repositories/service_requests.py` UPDATE)

- [x] `save` 메서드 추가 (파일 끝 `list_by_customer` 다음에):
  ```python
  async def save(self, obj: ServiceRequest) -> ServiceRequest:
      """ORM 객체 변경사항을 flush/refresh하여 DB 반영. commit은 service 계층에서."""
      await self.session.flush()
      await self.session.refresh(obj)
      return obj
  ```
- [x] 기존 `create()`, `get_by_id()`, `list_by_customer()` 파괴하지 않음

### Task 4 — 서비스 확장 (`apps/api/app/services/service_request.py` UPDATE)

- [x] import 블록에 `InvalidStatusTransitionError` 추가:
  ```python
  from app.core.exceptions import (
      CategoryNotFoundError,
      InvalidCursorError,
      InvalidStatusTransitionError,   # ← 추가
      ServiceRequestNotFoundError,
  )
  ```
- [x] 클래스 맨 아래에 `change_status` 메서드 추가:
  ```python
  async def change_status(
      self, id: UUID, action: str, current_user: User
  ) -> ServiceRequest:
      """상태 전이 시행 (취소: open→cancelled, 완료: matched→completed).

      순서: 404 우선 → 소유권(403) → 전이 규칙(409) → save.
      """
      request = await self.repo.get_by_id(id)
      if request is None:
          raise ServiceRequestNotFoundError()
      # request.customer_id는 ORM에서 UUID 타입 — str 변환 절대 금지
      ensure_owner_or_admin(request.customer_id, current_user)

      if action == "cancel":
          if request.status != ServiceRequestStatus.OPEN:
              raise InvalidStatusTransitionError()
          request.status = ServiceRequestStatus.CANCELLED
      elif action == "complete":
          if request.status != ServiceRequestStatus.MATCHED:
              raise InvalidStatusTransitionError()
          request.status = ServiceRequestStatus.COMPLETED
      else:
          raise InvalidStatusTransitionError()

      return await self.repo.save(request)
  ```

### Task 5 — 라우터 확장 (`apps/api/app/routers/service_requests.py` UPDATE)

- [x] import 블록에 `ServiceRequestStatusUpdate` 추가:
  ```python
  from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead, ServiceRequestStatusUpdate
  ```
- [x] `GET /{request_id}` **다음**에 `PATCH /{request_id}` 엔드포인트 추가:
  ```python
  @router.patch("/{request_id}", response_model=ServiceRequestRead)
  async def update_service_request_status(
      request_id: uuid.UUID,
      body: ServiceRequestStatusUpdate,
      current_user: CurrentUser,
      _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
      session: AsyncSession = Depends(get_db),
  ) -> ServiceRequestRead:
      svc = ServiceRequestService(session)
      result = await svc.change_status(request_id, body.action, current_user)
      return result
  ```
- [x] 기존 POST /, GET /, GET /{request_id} 파괴하지 않음
- [x] 최종 등록 순서: `POST /` → `GET /` → `GET /{id}` → `PATCH /{id}`

### Task 6 — 테스트 (`apps/api/tests/test_service_requests_status.py` NEW)

- [x] `test_service_requests_list_detail.py` 패턴 복제: `pytestmark = pytest.mark.asyncio`, `client_db` fixture
- [x] 헬퍼 함수 정의:
  - `_make_customer(db, email)` — Story 2.2 패턴 동일
  - `_make_pro(db, email)` — Story 2.2 패턴 동일
  - `_make_admin(db, email)` — Story 2.2 패턴 동일, `user_role=UserRole.ADMIN, is_seed=True`
  - `_make_category(db, name="청소")` — Story 2.2 패턴 동일
  - `_make_service_request(db, customer, category, status=ServiceRequestStatus.OPEN)` — **status 파라미터 추가**
  - `_auth(user)` — Story 2.2 패턴 동일
- [x] **테스트 케이스 12개 구현:**
  - ✅ `test_cancel_open_request_200` — open → cancelled, `r.json()["status"] == "cancelled"` 확인
  - ✅ `test_complete_matched_request_200` — matched → completed, `r.json()["status"] == "completed"` 확인
  - ✅ `test_cancel_matched_request_409` — 409 + `code == "invalid_status_transition"`
  - ✅ `test_complete_open_request_409` — 409 + `code == "invalid_status_transition"`
  - ✅ `test_cancel_cancelled_request_409` — 이미 cancelled → 409
  - ✅ `test_cancel_completed_request_409` — 이미 completed → 409
  - ✅ `test_other_customer_cancel_403` — 타인 요청 → 403 + `code == "forbidden"`
  - ✅ `test_not_found_404` — 존재하지 않는 UUID → 404 + `code == "service_request_not_found"`
  - ✅ `test_no_token_401`
  - ✅ `test_inactive_customer_401`
  - ✅ `test_pro_role_403`
  - ✅ `test_admin_role_403`
- [x] `uv run pytest tests/test_service_requests_status.py -v` 전체 패스 (12/12)

### Task 7 — user-web 상세 페이지 업데이트 (`apps/user-web/src/app/(customer)/requests/[id]/page.tsx` UPDATE)

> **⚠️ 필독:** `apps/user-web/AGENTS.md` — "This is NOT the Next.js you know". 코드 작성 전 `node_modules/next/dist/docs/` 확인.

- [x] Orval 생성 뮤테이션 훅 + queryKey 헬퍼 import (Task 8 완료 후 실제 이름 확인):
  ```typescript
  import {
    useGetServiceRequest,
    useUpdateServiceRequestStatus,
    getGetServiceRequestQueryKey,
    getListMyServiceRequestsQueryKey,
    type ServiceRequestRead,
  } from "@gosoom/api-client";
  import { useQueryClient } from "@tanstack/react-query";
  ```
- [x] 컴포넌트 내부에 queryClient + mutation 설정:
  ```typescript
  const queryClient = useQueryClient();
  const mutation = useUpdateServiceRequestStatus({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
        queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      },
    },
  });
  ```
- [x] 상태 기반 버튼 렌더링 (`data &&` 블록 내):
  ```typescript
  {data.status === "open" && (
    <button
      onClick={() => mutation.mutate({ requestId: id, data: { action: "cancel" } })}
      disabled={mutation.isPending}
      className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
    >
      {mutation.isPending ? "처리 중…" : "취소하기"}
    </button>
  )}
  {data.status === "matched" && (
    <button
      onClick={() => mutation.mutate({ requestId: id, data: { action: "complete" } })}
      disabled={mutation.isPending}
      className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
    >
      {mutation.isPending ? "처리 중…" : "완료하기"}
    </button>
  )}
  {mutation.isError && (
    <p className="text-red-600 text-sm" role="alert">
      요청 처리에 실패했습니다.
    </p>
  )}
  ```
- [x] 기존 상세 표시 코드(`dl` 블록, 뒤로가기 링크) 파괴하지 않음

### Review Findings

- [x] [Review][Patch] PRO·ADMIN 403 테스트 응답 body `code` 미검증 — `test_pro_role_403`, `test_admin_role_403` 에서 `r.status_code == 403`만 단언하고 `r.json()["code"] == "forbidden"` 검증 없음 [apps/api/tests/test_service_requests_status.py:280,296]
- [x] [Review][Patch] `cancelled`/`completed` 상태 409 테스트 `code` 미검증 — `test_cancel_cancelled_request_409`, `test_cancel_completed_request_409`에서 code 필드 검증 누락 [apps/api/tests/test_service_requests_status.py:191,205]
- [x] [Review][Patch] `complete` action + 종료 상태(CANCELLED/COMPLETED) 전이 거부 테스트 완전 누락 — AC3 "어떤 상태도 변경되지 않음" 보장 불완전 [apps/api/tests/test_service_requests_status.py]
- [x] [Review][Defer] `ensure_owner_or_admin` ADMIN 우회가 서비스 계층에 잠재 [apps/api/app/core/authz.py:26] — deferred, pre-existing (Story 1.5 도입, 현재 require_role(CUSTOMER)로 차단됨)
- [x] [Review][Defer] `save()` 메서드 `session.add()` 없는 암묵적 계약 [apps/api/app/repositories/service_requests.py:50] — deferred, pre-existing (tracked 객체 전용 패턴으로 안전, 신규 객체 전달 시 위험 잠재)
- [x] [Review][Defer] 두 탭 동시 요청 race condition — deferred, pre-existing (Epic 4 이후 idempotency 정책 수립 시 처리)
- [x] [Review][Defer] soft-deleted 요청 404 응답 audit trail 없음 — deferred, pre-existing (현재 삭제 경로 없음, 관리자 콘솔 Epic 6 도입 시 처리)

### Task 8 — Orval 재생성 및 커밋

- [x] `apps/api`에서 openapi.json 덤프 (**PowerShell `>` 리다이렉트 절대 금지**, Python `open` 방식):
  ```powershell
  cd apps/api
  uv run python -c "import json; from app.main import app; open(r'../../openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"
  ```
- [x] 레포 루트에서 `pnpm orval` 실행
- [x] `packages/api-client/src/generated/service-requests/` 갱신 확인:
  - `useUpdateServiceRequestStatus` 훅 생성 확인
  - `ServiceRequestStatusUpdate` 타입 생성 확인
  - `getGetServiceRequestQueryKey`, `getListMyServiceRequestsQueryKey` 헬퍼 확인
- [x] **실제 생성된 함수명·타입명·시그니처를 생성물에서 확인 후 Task 7 코드 수정**
- [x] `openapi.json` 삭제(커밋 제외), **생성물만 커밋 대상**:
  ```powershell
  Remove-Item openapi.json
  git add packages/api-client/src/generated/
  ```

---

## 개발자 노트 (Dev Notes)

### 핵심 설계 결정 사항

#### 상태 기계 — 허용 전이표 (FR7)

| 현재 상태 | action="cancel" | action="complete" |
|-----------|----------------|-------------------|
| `open`    | ✅ → `cancelled` | ❌ 409            |
| `matched` | ❌ 409          | ✅ → `completed`  |
| `completed` | ❌ 409        | ❌ 409            |
| `cancelled` | ❌ 409        | ❌ 409            |

`matched → cancelled` 미허용: FR7은 취소를 `open` 상태에서만 명시. `matched`는 견적 수락 후 상태이므로 취소 불가.  
`matched → cancelled`는 Epic 4(FR13) 이후 비즈니스 결정으로 추가 가능하지만 현재 스펙에 없음.

#### 엔드포인트 설계 — `PATCH /{id}` + action body

`PATCH /api/v1/service-requests/{id}` + `{ "action": "cancel" | "complete" }` 선택 근거:
- Epic 4가 `POST /quotes/{id}/accept`, `POST /quotes/{id}/reject` 전용 액션 패턴을 사용하는 것과 달리, 서비스 요청 상태 관리는 단일 PATCH 엔드포인트로 처리 (`PATCH ... 또는 전용 액션` 에픽 스펙).
- `Literal["cancel", "complete"]`로 OpenAPI에 허용값 문서화.
- 추후 action 확장 시 단일 엔드포인트 유지.

#### 소유권 검사 순서 (2.2 패턴 계승)

```
get_by_id → None이면 404 → ensure_owner_or_admin → 상태 전이 검사 → save
```
404 우선 → 소유권(403) → 전이 규칙(409) 순서 엄수.  
`require_role(CUSTOMER)`로 ADMIN은 라우터에서 이미 차단 → `ensure_owner_or_admin`의 ADMIN 통과 분기 도달 불가.

#### `save()` 레포 메서드 역할

```python
# ORM 객체 직접 수정 후 flush+refresh
request.status = ServiceRequestStatus.CANCELLED
return await self.repo.save(request)  # flush → updated_at 자동 갱신 → refresh
```
`TimestampMixin.updated_at`에 `onupdate=func.now()`가 설정되어 있어 flush 시 자동 갱신됨 (base.py:47 확인).  
별도 `updated_at` 처리 불필요.

### 기존 참조 파일 (수정 대상)

| 파일 | 현재 상태 | 이 스토리 변경 |
|------|-----------|----------------|
| `apps/api/app/core/exceptions.py` | `ServiceRequestNotFoundError`까지 정의됨 | `InvalidStatusTransitionError` append |
| `apps/api/app/schemas/service_request.py` | `ServiceRequestCreate`, `ServiceRequestRead` | `ServiceRequestStatusUpdate` 추가 |
| `apps/api/app/repositories/service_requests.py` | `create`, `get_by_id`, `list_by_customer` | `save` 추가 |
| `apps/api/app/services/service_request.py` | `create`, `list_mine`, `get_detail` | `change_status` 추가 |
| `apps/api/app/routers/service_requests.py` | POST /, GET /, GET /{id} | PATCH /{id} 추가 |
| `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` | 상세 표시만 | 취소/완료 버튼 추가 |

### 아키텍처 필수 준수 사항

#### 레이어 규칙 (2.1/2.2 계승, 엄격 준수)
- **router**: HTTP 파싱·의존성 주입·status code만
- **service**: 소유권 검사·상태 전이 규칙 단일 시행 — **라우터/클라이언트 분산 금지**
- **repository**: DB 접근만, commit 없음

#### FastAPI 라우터 등록 순서

```
POST  /          (create)
GET   /          (list)  — 고정 경로 우선
GET   /{id}      (detail)
PATCH /{id}      (status update, 이 스토리) ← GET과 메서드 달라 충돌 없음
```
`GET /`와 `GET /{id}`의 순서가 중요 (2.2 계승). `PATCH /{id}`는 메서드 다르므로 위치 무관하나 일관성을 위해 맨 아래.

#### `ensure_owner_or_admin` UUID 타입 일치 — **절대 엄수**

```python
ensure_owner_or_admin(request.customer_id, current_user)  # ✅ UUID 직접
ensure_owner_or_admin(str(request.customer_id), current_user)  # ❌ 금지 → 모든 고객 403
```
`request.customer_id`는 ORM에서 `UUID` 타입. str 변환 시 `UUID != str` 항상 True → 정당 소유자도 403.

### 전체 구현 코드 레퍼런스

#### exceptions.py (파일 끝 append)
```python
class InvalidStatusTransitionError(AppError):
    """허용되지 않는 상태 전이 시도(Story 2.3 AC3). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="invalid_status_transition",
            message="허용되지 않는 상태 전이입니다.",
            status_code=409,
        )
```

#### schemas/service_request.py (파일 끝 append)
```python
from typing import Literal  # import 블록에 추가

class ServiceRequestStatusUpdate(CamelModel):
    action: Literal["cancel", "complete"]
```

#### repositories/service_requests.py (list_by_customer 다음에 추가)
```python
async def save(self, obj: ServiceRequest) -> ServiceRequest:
    """ORM 객체 변경사항을 flush/refresh하여 DB 반영. commit은 service 계층에서."""
    await self.session.flush()
    await self.session.refresh(obj)
    return obj
```

#### services/service_request.py (change_status 메서드 추가)
```python
# import 블록에 추가:
from app.core.exceptions import (
    CategoryNotFoundError,
    InvalidCursorError,
    InvalidStatusTransitionError,
    ServiceRequestNotFoundError,
)

# 클래스 메서드 추가:
async def change_status(
    self, id: UUID, action: str, current_user: User
) -> ServiceRequest:
    """상태 전이 시행 (취소: open→cancelled, 완료: matched→completed)."""
    request = await self.repo.get_by_id(id)
    if request is None:
        raise ServiceRequestNotFoundError()
    ensure_owner_or_admin(request.customer_id, current_user)

    if action == "cancel":
        if request.status != ServiceRequestStatus.OPEN:
            raise InvalidStatusTransitionError()
        request.status = ServiceRequestStatus.CANCELLED
    elif action == "complete":
        if request.status != ServiceRequestStatus.MATCHED:
            raise InvalidStatusTransitionError()
        request.status = ServiceRequestStatus.COMPLETED
    else:
        raise InvalidStatusTransitionError()

    return await self.repo.save(request)
```

#### routers/service_requests.py (GET /{request_id} 다음에 추가)
```python
# import 수정:
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead, ServiceRequestStatusUpdate

# 엔드포인트 추가:
@router.patch("/{request_id}", response_model=ServiceRequestRead)
async def update_service_request_status(
    request_id: uuid.UUID,
    body: ServiceRequestStatusUpdate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    result = await svc.change_status(request_id, body.action, current_user)
    return result
```

### 테스트 구현 패턴

```python
# apps/api/tests/test_service_requests_status.py

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.service_request import ServiceRequest, ServiceRequestStatus
from app.models.user import User, UserRole

pytestmark = pytest.mark.asyncio


async def _make_customer(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="고객유저",
        user_role=UserRole.CUSTOMER,
        is_active=True,
        is_seed=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_pro(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="고수유저",
        user_role=UserRole.PRO,
        is_active=True,
        is_seed=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_admin(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        password_hash=hash_password("secret"),
        display_name="관리자유저",
        user_role=UserRole.ADMIN,
        is_active=True,
        is_seed=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_category(db: AsyncSession, name: str = "청소") -> Category:
    import uuid_extensions
    cat = Category(
        id=uuid_extensions.uuid7(),
        name=name,
        is_active=True,
    )
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return cat


async def _make_service_request(
    db: AsyncSession,
    customer: User,
    category: Category,
    status: ServiceRequestStatus = ServiceRequestStatus.OPEN,
) -> ServiceRequest:
    import uuid_extensions
    req = ServiceRequest(
        id=uuid_extensions.uuid7(),
        customer_id=customer.id,
        category_id=category.id,
        region="서울 강남구",
        description="테스트 요청",
        status=status,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req


def _auth(user: User) -> dict[str, str]:
    token = create_access_token({"user_id": str(user.id), "user_role": user.user_role.value})
    return {"Authorization": f"Bearer {token}"}


async def test_cancel_open_request_200(client_db):
    client, db = client_db
    customer = await _make_customer(db, "cancel_open@test.com")
    cat = await _make_category(db, "청소_c1")
    req = await _make_service_request(db, customer, cat, ServiceRequestStatus.OPEN)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_complete_matched_request_200(client_db):
    client, db = client_db
    customer = await _make_customer(db, "complete_matched@test.com")
    cat = await _make_category(db, "청소_c2")
    req = await _make_service_request(db, customer, cat, ServiceRequestStatus.MATCHED)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "complete"},
        headers=_auth(customer),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


async def test_cancel_matched_request_409(client_db):
    client, db = client_db
    customer = await _make_customer(db, "cancel_matched@test.com")
    cat = await _make_category(db, "청소_c3")
    req = await _make_service_request(db, customer, cat, ServiceRequestStatus.MATCHED)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_complete_open_request_409(client_db):
    client, db = client_db
    customer = await _make_customer(db, "complete_open@test.com")
    cat = await _make_category(db, "청소_c4")
    req = await _make_service_request(db, customer, cat, ServiceRequestStatus.OPEN)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "complete"},
        headers=_auth(customer),
    )
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_status_transition"


async def test_cancel_cancelled_request_409(client_db):
    client, db = client_db
    customer = await _make_customer(db, "cancel_cancelled@test.com")
    cat = await _make_category(db, "청소_c5")
    req = await _make_service_request(db, customer, cat, ServiceRequestStatus.CANCELLED)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 409


async def test_cancel_completed_request_409(client_db):
    client, db = client_db
    customer = await _make_customer(db, "cancel_completed@test.com")
    cat = await _make_category(db, "청소_c6")
    req = await _make_service_request(db, customer, cat, ServiceRequestStatus.COMPLETED)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 409


async def test_other_customer_cancel_403(client_db):
    client, db = client_db
    owner = await _make_customer(db, "owner403@test.com")
    other = await _make_customer(db, "other403@test.com")
    cat = await _make_category(db, "청소_c7")
    req = await _make_service_request(db, owner, cat, ServiceRequestStatus.OPEN)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(other),
    )
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


async def test_not_found_404(client_db):
    client, db = client_db
    customer = await _make_customer(db, "notfound404@test.com")
    import uuid
    fake_id = uuid.uuid4()

    r = await client.patch(
        f"/api/v1/service-requests/{fake_id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 404
    assert r.json()["code"] == "service_request_not_found"


async def test_no_token_401(client_db):
    client, db = client_db
    customer = await _make_customer(db, "notoken401@test.com")
    cat = await _make_category(db, "청소_c8")
    req = await _make_service_request(db, customer, cat)

    r = await client.patch(f"/api/v1/service-requests/{req.id}", json={"action": "cancel"})
    assert r.status_code == 401


async def test_inactive_customer_401(client_db):
    client, db = client_db
    customer = await _make_customer(db, "inactive401@test.com")
    customer.is_active = False
    await db.flush()
    cat = await _make_category(db, "청소_c9")
    req = await _make_service_request(db, customer, cat)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(customer),
    )
    assert r.status_code == 401


async def test_pro_role_403(client_db):
    client, db = client_db
    pro = await _make_pro(db, "pro403@test.com")
    customer = await _make_customer(db, "pro403_owner@test.com")
    cat = await _make_category(db, "청소_c10")
    req = await _make_service_request(db, customer, cat)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(pro),
    )
    assert r.status_code == 403


async def test_admin_role_403(client_db):
    client, db = client_db
    admin = await _make_admin(db, "admin403@test.com")
    customer = await _make_customer(db, "admin403_owner@test.com")
    cat = await _make_category(db, "청소_c11")
    req = await _make_service_request(db, customer, cat)

    r = await client.patch(
        f"/api/v1/service-requests/{req.id}",
        json={"action": "cancel"},
        headers=_auth(admin),
    )
    assert r.status_code == 403
```

### Orval 훅 예측 (생성물 확인 후 Task 7 적용)

operationId `update_service_request_status` 기반 예측:

| 생성물 | 예측 이름 |
|--------|-----------|
| 뮤테이션 훅 | `useUpdateServiceRequestStatus` |
| 타입 | `ServiceRequestStatusUpdate` |
| GET queryKey | `getGetServiceRequestQueryKey` |
| GET list queryKey | `getListMyServiceRequestsQueryKey` |

실제 이름은 `packages/api-client/src/generated/service-requests/service-requests.ts` 확인 후 Task 7 코드에 반영.

**Orval 뮤테이션 시그니처 예측:**
```typescript
mutation.mutate({ requestId: string, data: ServiceRequestStatusUpdate })
```
`requestId`는 `params.id` (string) 직접 사용 가능.

---

## 파일 구조 요약

```
NEW (생성):
  apps/api/tests/test_service_requests_status.py

UPDATE (수정):
  apps/api/app/core/exceptions.py                    ← InvalidStatusTransitionError 추가
  apps/api/app/schemas/service_request.py            ← ServiceRequestStatusUpdate 추가
  apps/api/app/repositories/service_requests.py     ← save() 추가
  apps/api/app/services/service_request.py          ← change_status() 추가
  apps/api/app/routers/service_requests.py          ← PATCH /{id} 추가
  apps/user-web/src/app/(customer)/requests/[id]/page.tsx  ← 취소/완료 버튼
  packages/api-client/src/generated/                ← Orval 재생성
```

---

## 테스트 요구사항

### 백엔드 테스트

**픽스처:** `client_db` (real DB, `join_transaction_mode="create_savepoint"` — **conftest.py 수정 금지**)

```
test_cancel_open_request_200       — open → cancelled 200
test_complete_matched_request_200  — matched → completed 200
test_cancel_matched_request_409    — matched 취소 → 409
test_complete_open_request_409     — open 완료 → 409
test_cancel_cancelled_request_409  — 이미 cancelled → 409
test_cancel_completed_request_409  — 이미 completed → 409
test_other_customer_cancel_403     — 타인 요청 → 403
test_not_found_404                 — 존재하지 않는 id → 404
test_no_token_401
test_inactive_customer_401
test_pro_role_403
test_admin_role_403
```

### 프론트엔드 검증 게이트

```
pnpm typecheck   ← 타입 오류 없음 (생성물 포함)
pnpm lint        ← ESLint 통과
pnpm build       ← Next.js 빌드 성공
```

---

## 이전 스토리 학습 사항 (2.1, 2.2 → 2.3 계승)

1. **`uuid_extensions.uuid7()`** — `uuid7` 패키지 아님, `uuid_extensions` 패키지의 함수 (테스트 헬퍼에서 동일)
2. **`ensure_owner_or_admin(resource_owner_id: UUID, ...)` — str 변환 절대 금지** (str 변환 시 모든 고객 403)
3. **PowerShell `>` 리다이렉트 절대 금지** — openapi.json 덤프는 Python `open(encoding='utf-8')` 방식만
4. **Orval 생성물은 커밋 대상** — `packages/api-client/src/generated/` gitignore 추가 금지
5. **conftest.py `join_transaction_mode="create_savepoint"` 수정 금지**
6. **FastAPI 라우터 등록 순서**: `GET /` → `GET /{id}` (고정 경로 우선) — PATCH는 메서드 달라 충돌 없음
7. **`AGENTS.md` 필독 의무**: user-web 코드 작성 전 `node_modules/next/dist/docs/` 확인
8. **기존 테스트 pre-existing 실패** — test_categories_list.py 3개, test_seed_categories.py 2개 (DB 시드 오염) — 내 변경과 무관, 수정 대상 아님
9. **Orval 훅 이름 확인 필수** — 생성물(`service-requests.ts`)에서 실제 이름 확인 후 적용

---

## 알려진 함정

1. **`_make_category` 중복 이름 충돌:** 테스트 파일 내 여러 테스트가 각각 카테고리를 생성할 때 같은 `name`을 쓰면 unique 제약 위반 가능. **각 테스트에서 고유한 name 파라미터 사용** (`"청소_c1"`, `"청소_c2"` 등) — 위 코드 참조.

2. **`Literal` import 위치:** `from typing import Literal` — `ServiceRequestStatusUpdate`와 함께 `schemas/service_request.py` 상단 import 블록에 추가.

3. **`PATCH /{request_id}` FastAPI 등록:** `PATCH`와 `GET`은 HTTP 메서드가 다르므로 동일 경로 패턴 충돌 없음. 하지만 `GET /`(고정)보다 `GET /{id}`(동적)가 나중 등록되어야 하는 규칙은 계속 준수.

4. **뮤테이션 중복 클릭:** `mutation.isPending` 중 버튼 `disabled` 처리 필수. 미처리 시 취소/완료 중복 전송 → 두 번째 409 응답으로 UX 깨짐.

5. **queryKey 함수 이름:** `getGetServiceRequestQueryKey(id)` — Orval이 GET 훅 이름 기반으로 생성. 실제 이름은 생성물에서 확인. 잘못된 queryKey 사용 시 캐시 무효화 미동작 → UI 갱신 안 됨.

6. **`ServiceRequestStatusUpdate` camelCase 직렬화:** `action` 필드명은 소문자라 camelCase 변환 없음. 클라이언트는 `{"action": "cancel"}` 그대로 전송.

7. **`TimestampMixin.updated_at` 자동 갱신 확인:** `base.py:47`에 `onupdate=func.now()` 설정 확인됨 → status 변경 flush 시 자동 갱신. 별도 처리 불필요.

8. **`inactive_customer_401` 테스트:** 비활성 고객 토큰은 `create_access_token`으로 생성 가능하지만, 서버의 `get_current_user`가 DB에서 `is_active=False` 확인 후 401 반환 — 이 흐름이 기존 패턴(1.4/1.5)과 동일함을 확인.

---

## AR23 체크포인트 — 외부 수동 설정

**이 스토리는 외부 수동 설정 필요 없음.**

기존 Railway + Supabase(PostgreSQL), Alembic 마이그레이션이 그대로 사용된다.  
신규 테이블/마이그레이션 없음 — 기존 `service_requests.status` 컬럼 업데이트만.

---

## 스토리 완료 기준

- [x] `uv run pytest tests/test_service_requests_status.py -v` 전체 패스 (12/12)
- [x] `uv run pytest` 기존 테스트 회귀 없음 (pre-existing 5개 실패 제외)
- [x] `pnpm typecheck && pnpm lint && pnpm build` 전체 통과
- [x] `packages/api-client/src/generated/` 갱신 내용 커밋 포함
- [x] user-web `/requests/[id]` 상세 페이지: 상태별 취소/완료 버튼 구현 + 캐시 무효화

---

## Dev Agent Record

### 구현 계획

router → service → repository 레이어 규칙 준수. 총 8개 태스크 순서:
- Task 1: 예외 추가 (InvalidStatusTransitionError)
- Task 2: 스키마 추가 (ServiceRequestStatusUpdate)
- Task 3: 레포지토리 save() 추가
- Task 4: 서비스 change_status() 추가
- Task 5: 라우터 PATCH /{id} 추가
- Task 6: 백엔드 테스트 12케이스
- Task 7: user-web 취소/완료 버튼
- Task 8: Orval 재생성 + 커밋

### 완료 노트

- PATCH /api/v1/service-requests/{id} 엔드포인트 구현 (open→cancelled, matched→completed 전이)
- `InvalidStatusTransitionError` (409) 추가 — 허용되지 않은 전이 시 반환
- 소유권 검사 순서 준수: 404 → 403 → 409
- 테스트 픽스처 패턴 수정: `client_db`(AsyncClient) + `db_session`(AsyncSession) 별도 인자 사용 (story 파일의 `client_db` 튜플 예제는 실제 conftest와 불일치 — 2.2 패턴으로 수정)
- Orval 재생성으로 `useUpdateServiceRequestStatus` 훅, `ServiceRequestStatusUpdate` 타입, queryKey 헬퍼 생성
- user-web 상세 페이지에 상태별 취소/완료 버튼 + TanStack Query 캐시 무효화 추가
- pnpm typecheck, lint, build 모두 통과
- 백엔드 전체 테스트 95/95 통과 (pre-existing 5개 별도)

### File List

- `apps/api/app/core/exceptions.py` — `InvalidStatusTransitionError` 추가
- `apps/api/app/schemas/service_request.py` — `ServiceRequestStatusUpdate` 추가, `Literal` import
- `apps/api/app/repositories/service_requests.py` — `save()` 메서드 추가
- `apps/api/app/services/service_request.py` — `change_status()` 메서드 추가, import 확장
- `apps/api/app/routers/service_requests.py` — `PATCH /{request_id}` 엔드포인트 추가, import 확장
- `apps/api/tests/test_service_requests_status.py` — 신규 (12개 테스트케이스)
- `apps/user-web/src/app/(customer)/requests/[id]/page.tsx` — 취소/완료 버튼 + mutation + 캐시 무효화
- `packages/api-client/src/generated/service-requests/service-requests.ts` — Orval 재생성
- `packages/api-client/src/generated/model/serviceRequestStatusUpdate.ts` — Orval 재생성 (신규)
- `packages/api-client/src/generated/model/index.ts` — Orval 재생성
- `packages/api-client/src/index.ts` — 변경 없음 (기존 service-requests export 유지)

## Change Log

- 2026-06-09: Story 2.3 스토리 파일 생성 (ready-for-dev)
- 2026-06-09: Story 2.3 구현 완료 — PATCH /{id} 상태 관리 엔드포인트, 12개 테스트 통과, Orval 재생성, user-web 버튼 구현
