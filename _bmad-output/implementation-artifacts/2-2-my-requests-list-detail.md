---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 2.2: 내 요청 목록·상세 조회

**Status:** done  
**Epic:** 2 — 고객 서비스 요청 (FR5-7)  
**Story ID:** 2-2  
**Story Key:** 2-2-my-requests-list-detail  
**작성일:** 2026-06-09  
**Author:** KTH (bmad-create-story 자동 생성)

---

## 사용자 스토리

**As a** 로그인한 고객(CUSTOMER)으로서,  
**I want** 내가 생성한 서비스 요청의 목록과 각 요청의 상세를 조회하고 싶다.  
**So that** 각 요청의 진행 상태(open/matched/completed/cancelled)를 파악할 수 있다.

---

## 인수 기준 (BDD)

### AC1 — 내 요청 목록 조회 (FR6)

```
Given 고객이 여러 요청을 생성했을 때
When GET /api/v1/service-requests를 호출하면
Then 본인 요청만 {items, nextCursor} cursor 페이지네이션으로 최신순(id DESC) 반환되고
And 소프트 삭제(deleted_at IS NOT NULL) 요청은 제외된다
And 다른 고객의 요청은 응답에 포함되지 않는다
```

### AC2 — 요청 상세 조회 (FR6)

```
Given 특정 서비스 요청의 id가 있을 때
When GET /api/v1/service-requests/{id}를 호출하면
Then 카테고리·지역·내용·상태·생성일 등 요청 전체 필드가 반환된다

When 다른 고객의 요청 id로 조회하면
Then 403 Forbidden + {code: "forbidden"}이 반환된다

When 존재하지 않는 id로 조회하면
Then 404 Not Found + {code: "service_request_not_found"}이 반환된다
```

### AC3 — 권한 제어 (FR4, FR7)

```
Given 비인증 요청이거나 비활성 고객일 때
When 목록 또는 상세 엔드포인트를 호출하면
Then 401이 반환된다

Given PRO 또는 ADMIN 역할의 사용자가
When 목록 또는 상세 엔드포인트를 시도하면
Then 403 Forbidden이 반환된다 (require_role(CUSTOMER) 가드)
```

### AC4 — user-web 목록·상세 화면 (FR6)

```
Given 로그인한 CUSTOMER가 /requests에 접근하면
When 목록 화면이 로드되면
Then 본인 요청 목록이 각 상태를 한국어 라벨로 표시한다
  - open → "접수됨", matched → "매칭됨", completed → "완료됨", cancelled → "취소됨"
And 각 항목 클릭 시 /requests/[id] 상세 화면으로 이동한다
And 상세 화면에서 요청의 모든 필드(카테고리, 지역, 설명, 상태, 생성일 등)가 표시된다
```

---

## 태스크 및 서브태스크

### Task 1 — 예외 추가 (`apps/api/app/core/exceptions.py` UPDATE)

- [x] 파일 끝에 `ServiceRequestNotFoundError` 추가 (404):
  ```python
  class ServiceRequestNotFoundError(AppError):
      def __init__(self) -> None:
          super().__init__(
              code="service_request_not_found",
              message="요청을 찾을 수 없습니다.",
              status_code=404,
          )
  ```
- [x] 기존 예외(`CategoryNotFoundError` 등) 파괴하지 않고 파일 끝에만 append

### Task 2 — 레포지토리 확장 (`apps/api/app/repositories/service_requests.py` UPDATE)

- [x] `list_by_customer(customer_id, after_id, limit)` 메서드 추가:
  ```python
  async def list_by_customer(
      self, customer_id: uuid.UUID, after_id: uuid.UUID | None, limit: int
  ) -> list[ServiceRequest]:
      """고객별 요청을 id DESC(최신순) keyset으로 조회. deleted_at IS NULL 필터."""
      stmt = select(ServiceRequest).where(
          ServiceRequest.customer_id == customer_id,
          ServiceRequest.deleted_at.is_(None),
      )
      if after_id is not None:
          stmt = stmt.where(ServiceRequest.id < after_id)  # DESC 방향: 더 오래된 항목
      stmt = stmt.order_by(ServiceRequest.id.desc()).limit(limit)
      return list((await self.session.execute(stmt)).scalars().all())
  ```
- [x] 기존 `create()`, `get_by_id()` 메서드 파괴하지 않음

### Task 3 — 서비스 확장 (`apps/api/app/services/service_request.py` UPDATE)

- [x] import 추가:
  ```python
  from app.core.authz import ensure_owner_or_admin
  from app.core.exceptions import CategoryNotFoundError, ServiceRequestNotFoundError
  from app.core.pagination import decode_cursor, encode_cursor
  from app.schemas.pagination import Page
  ```
- [x] `list_mine(current_user, cursor, limit)` 메서드 추가:
  ```python
  async def list_mine(
      self, current_user: User, cursor: str | None, limit: int
  ) -> Page[ServiceRequestRead]:
      from uuid import UUID
      from app.core.exceptions import InvalidCursorError

      after_id: UUID | None = None
      if cursor is not None:
          decoded = decode_cursor(cursor)
          try:
              after_id = UUID(decoded)
          except (ValueError, AttributeError, TypeError) as exc:
              raise InvalidCursorError() from exc

      rows = await self.repo.list_by_customer(current_user.id, after_id, limit + 1)
      has_more = len(rows) > limit
      page_rows = rows[:limit]
      next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

      return Page[ServiceRequestRead](
          items=[ServiceRequestRead.model_validate(r) for r in page_rows],
          next_cursor=next_cursor,
      )
  ```
- [x] `get_detail(id, current_user)` 메서드 추가:
  ```python
  async def get_detail(
      self, id: uuid.UUID, current_user: User
  ) -> ServiceRequest:
      request = await self.repo.get_by_id(id)
      if request is None:
          raise ServiceRequestNotFoundError()
      ensure_owner_or_admin(request.customer_id, current_user)
      return request
  ```
  - **`ensure_owner_or_admin`에 `request.customer_id`(UUID 타입)를 직접 전달** — str 변환 금지(deferred-work str-vs-UUID 위험 계승)
- [x] 기존 `create()` 메서드 파괴하지 않음

### Task 4 — 라우터 확장 (`apps/api/app/routers/service_requests.py` UPDATE)

- [x] import 추가:
  ```python
  from fastapi import APIRouter, Depends, Query
  from app.schemas.pagination import Page
  ```
- [x] `GET /` 엔드포인트 추가:
  ```python
  @router.get("/", response_model=Page[ServiceRequestRead])
  async def list_my_service_requests(
      current_user: CurrentUser,
      _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
      session: AsyncSession = Depends(get_db),
      cursor: str | None = Query(None),
      limit: int = Query(20, ge=1, le=100),
  ) -> Page[ServiceRequestRead]:
      svc = ServiceRequestService(session)
      return await svc.list_mine(current_user, cursor, limit)
  ```
- [x] `GET /{id}` 엔드포인트 추가:
  ```python
  @router.get("/{request_id}", response_model=ServiceRequestRead)
  async def get_service_request(
      request_id: uuid.UUID,
      current_user: CurrentUser,
      _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
      session: AsyncSession = Depends(get_db),
  ) -> ServiceRequestRead:
      svc = ServiceRequestService(session)
      result = await svc.get_detail(request_id, current_user)
      return result
  ```
- [x] 기존 `POST /` 엔드포인트 파괴하지 않음
- [x] `uuid` import 추가: `import uuid`

### Task 5 — 테스트 (`apps/api/tests/test_service_requests_list_detail.py` NEW)

- [x] `test_service_requests_create.py` 패턴 복제: `pytestmark = pytest.mark.asyncio`, `client_db` fixture 사용
- [x] 헬퍼 함수: `_make_customer()`, `_make_pro()`, `_make_admin()`, `_make_category()`, `_make_service_request()`, `_auth(user)` 정의
  - `_make_service_request(db, customer, category)` → 서비스 요청 생성 헬퍼
- [x] **목록 엔드포인트 테스트 케이스:**
  - ✅ `test_list_mine_success_200` — 200, items에 본인 요청만 포함
  - ✅ `test_list_mine_excludes_other_customers` — 다른 고객 요청 미포함 확인
  - ✅ `test_list_mine_empty_200` — 요청 없을 때 빈 items 반환
  - ✅ `test_list_mine_cursor_pagination` — 2개 요청 생성, limit=1 → nextCursor 존재, 두 번째 호출로 나머지 조회
  - ✅ `test_list_mine_newest_first` — 여러 요청 중 최신(나중 생성)이 먼저
  - ✅ `test_list_mine_no_token_401`
  - ✅ `test_list_mine_inactive_customer_401`
  - ✅ `test_list_mine_pro_role_403`
  - ✅ `test_list_mine_admin_role_403`
- [x] **상세 엔드포인트 테스트 케이스:**
  - ✅ `test_get_detail_success_200` — 200, 올바른 필드 반환
  - ✅ `test_get_detail_other_customer_403` — 타인 요청 접근 시 403
  - ✅ `test_get_detail_not_found_404` — 존재하지 않는 id
  - ✅ `test_get_detail_no_token_401`
  - ✅ `test_get_detail_pro_role_403`
  - ✅ `test_get_detail_admin_role_403`
- [x] `uv run pytest tests/test_service_requests_list_detail.py -v` 전체 패스 확인 (15/15)

### Task 6 — user-web 목록 페이지 실구현 (`apps/user-web/src/app/(customer)/requests/page.tsx` UPDATE)

> **⚠️ 필독:** `apps/user-web/AGENTS.md` — "This is NOT the Next.js you know" 경고. 코드 작성 전 `node_modules/next/dist/docs/` 확인.

- [x] `"use client"` — 클라이언트 컴포넌트 (TanStack Query 훅 사용)
- [x] Orval 생성 `useListMyServiceRequests()` 훅으로 목록 조회
  - 훅 이름은 Task 8 완료 후 생성물에서 확인 — `list_my_service_requests` 함수명 기반
- [x] 상태 한국어 라벨 매핑:
  ```typescript
  const STATUS_LABELS: Record<string, string> = {
    open: "접수됨",
    matched: "매칭됨",
    completed: "완료됨",
    cancelled: "취소됨",
  };
  ```
- [x] 로딩·에러 상태 처리 (`isPending`, `isError`)
- [x] 각 요청 항목 클릭 시 `/requests/[id]` 이동 (Next.js `Link`)
- [x] `/requests/new` 링크 유지 (기존 "새 요청 만들기" 버튼)

### Task 7 — user-web 상세 페이지 (`apps/user-web/src/app/(customer)/requests/[id]/page.tsx` NEW)

> **⚠️ 필독:** `apps/user-web/AGENTS.md` 경고 동일 적용.

- [x] `"use client"` — 클라이언트 컴포넌트
- [x] `useParams<{ id: string }>()` 로 `id` 추출 (`params.id`)
- [x] Orval 생성 `useGetServiceRequest(id)` 훅으로 상세 조회 (실제 시그니처: `useGetServiceRequest(requestId: string)`)
- [x] 표시 항목: 카테고리ID, 지역, 설명, 상태(한국어 라벨), 생성일(ISO→한국어 날짜 포맷), 희망 일정(있을 때만), 예산(있을 때만, KRW 포맷: `n.toLocaleString('ko-KR')` + "원")
- [x] 로딩·에러 상태 처리
- [x] `/requests`로 돌아가는 "뒤로 가기" 링크

### Task 8 — Orval 재생성 및 커밋

- [x] `apps/api`에서 openapi.json 덤프 (Python `open` 방식)
- [x] 레포 루트에서 `pnpm orval` 실행
- [x] `packages/api-client/src/generated/service-requests/` 갱신 확인 (`useListMyServiceRequests`, `useGetServiceRequest` 생성)
- [x] 생성된 훅 이름 확인 후 Task 6·7의 훅 호출 코드 점검
- [x] `openapi.json` 삭제(커밋 제외), **생성물만 커밋 대상**

---

## 개발자 노트 (Dev Notes)

### 핵심 설계 결정 사항

#### 엔드포인트 역할 제한
- `GET /api/v1/service-requests` — `require_role(CUSTOMER)` 적용 → PRO·ADMIN 403
- `GET /api/v1/service-requests/{id}` — `require_role(CUSTOMER)` 적용 → PRO·ADMIN 403
- **ADMIN 접근은 Epic 6의 `/api/v1/admin/service-requests` 경로 예정** (이 스토리 범위 외)
- 이 결정은 Story 2.1의 POST 엔드포인트와 일관성 유지

#### 목록 정렬 전략 — DESC keyset
- 서비스 요청은 "최신순" 표시 → `id DESC` (UUIDv7 = 시간순 정렬 키)
- 카테고리 목록(`id ASC`)과 **방향이 반대** — 주의
- DESC keyset cursor: `WHERE id < after_id ORDER BY id DESC`
  - `after_id` = 현재 페이지 마지막 항목의 id
  - "이전(더 오래된) 항목 조회" 의미

#### 소유권 검사 전략
- `get_detail`에서: `get_by_id()` → None이면 404 → `ensure_owner_or_admin()` 호출
- `require_role(CUSTOMER)`로 ADMIN은 이미 차단 → `ensure_owner_or_admin`의 ADMIN 통과 분기는 도달 불가
- **중요:** `ensure_owner_or_admin(request.customer_id, current_user)` — `request.customer_id`는 ORM에서 `UUID` 타입으로 반환됨. str 변환 없이 직접 전달(deferred-work 참고)
- 목록에서는 `WHERE customer_id = current_user.id` 쿼리 자체가 보안 경계 → per-item 소유권 검사 불필요

#### 새 예외: ServiceRequestNotFoundError
```python
# apps/api/app/core/exceptions.py 파일 끝에 추가
class ServiceRequestNotFoundError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="service_request_not_found",
            message="요청을 찾을 수 없습니다.",
            status_code=404,
        )
```

### 아키텍처 필수 준수 사항

#### 레이어 규칙 (2.1 계승)
- **router → service → repository** 엄격 순서 유지
- router: HTTP 파싱·Pydantic 직렬화·의존성 주입·status code만
- service: cursor 디코딩·페이지네이션·소유권 검사·비즈니스 로직
- repository: DB 접근만, commit 없음

#### 페이지네이션 패턴 (CategoryService 패턴 계승, 방향만 반대)
| 항목 | 카테고리 (참조) | 서비스 요청 (이 스토리) |
|------|----------------|------------------------|
| 정렬 방향 | ASC (id 오름차순) | **DESC (최신순)** |
| keyset 조건 | `id > after_id` | **`id < after_id`** |
| cursor 인코딩 | `encode_cursor(str(rows[-1].id))` | 동일 |
| limit+1 패턴 | 사용 | **동일** |
| `decode_cursor` / `InvalidCursorError` | 사용 | **동일** |
| `Page[T]` envelope | 사용 | **동일** |

**참조 파일:**
- `apps/api/app/core/pagination.py` — `encode_cursor`, `decode_cursor`
- `apps/api/app/schemas/pagination.py` — `Page[T]`
- `apps/api/app/services/category.py` — `list_active()` 패턴 참조 (방향 반전 적용)

#### 기존 패턴 참조
| 참조 대상 | 위치 |
|-----------|------|
| 소유권 검사 헬퍼 | `apps/api/app/core/authz.py:ensure_owner_or_admin` |
| cursor 유틸리티 | `apps/api/app/core/pagination.py` |
| Page envelope | `apps/api/app/schemas/pagination.py` |
| 예외 패턴 | `apps/api/app/core/exceptions.py` |
| 라우터 의존성 패턴 | `apps/api/app/routers/service_requests.py` (POST /) |
| 카테고리 서비스 페이지네이션 | `apps/api/app/services/category.py:list_active` |

### 구현 코드 레퍼런스

#### 레포지토리 확장 전체 코드
```python
# apps/api/app/repositories/service_requests.py — UPDATE
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.service_request import ServiceRequest

class ServiceRequestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, obj: ServiceRequest) -> ServiceRequest:
        # 기존 메서드 — 변경 없음
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def get_by_id(self, id: uuid.UUID) -> ServiceRequest | None:
        # 기존 메서드 — 변경 없음
        result = await self.session.execute(
            select(ServiceRequest).where(
                ServiceRequest.id == id,
                ServiceRequest.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_by_customer(
        self, customer_id: uuid.UUID, after_id: uuid.UUID | None, limit: int
    ) -> list[ServiceRequest]:
        """고객별 요청을 id DESC(최신순) keyset으로 조회. deleted_at IS NULL 필터."""
        stmt = select(ServiceRequest).where(
            ServiceRequest.customer_id == customer_id,
            ServiceRequest.deleted_at.is_(None),
        )
        if after_id is not None:
            stmt = stmt.where(ServiceRequest.id < after_id)
        stmt = stmt.order_by(ServiceRequest.id.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
```

#### 서비스 확장 전체 코드
```python
# apps/api/app/services/service_request.py — UPDATE
import uuid
import uuid_extensions
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import ensure_owner_or_admin
from app.core.exceptions import (
    CategoryNotFoundError,
    InvalidCursorError,
    ServiceRequestNotFoundError,
)
from app.core.pagination import decode_cursor, encode_cursor
from app.models.service_request import ServiceRequest, ServiceRequestStatus
from app.models.user import User
from app.repositories.categories import CategoryRepository
from app.repositories.service_requests import ServiceRequestRepository
from app.schemas.pagination import Page
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead


class ServiceRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ServiceRequestRepository(session)
        self.cat_repo = CategoryRepository(session)

    async def create(
        self, data: ServiceRequestCreate, current_user: User
    ) -> ServiceRequest:
        # 기존 메서드 — 변경 없음
        category = await self.cat_repo.get_by_id(data.category_id)
        if category is None:
            raise CategoryNotFoundError()
        new_id = uuid_extensions.uuid7()
        instance = ServiceRequest(
            id=new_id,
            customer_id=current_user.id,
            status=ServiceRequestStatus.OPEN,
            **data.model_dump(),
        )
        return await self.repo.create(instance)

    async def list_mine(
        self, current_user: User, cursor: str | None, limit: int
    ) -> Page[ServiceRequestRead]:
        """본인 요청을 id DESC(최신순) cursor 페이지네이션으로 조회."""
        after_id: UUID | None = None
        if cursor is not None:
            decoded = decode_cursor(cursor)
            try:
                after_id = UUID(decoded)
            except (ValueError, AttributeError, TypeError) as exc:
                raise InvalidCursorError() from exc

        rows = await self.repo.list_by_customer(current_user.id, after_id, limit + 1)
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = encode_cursor(str(page_rows[-1].id)) if has_more else None

        return Page[ServiceRequestRead](
            items=[ServiceRequestRead.model_validate(r) for r in page_rows],
            next_cursor=next_cursor,
        )

    async def get_detail(
        self, id: UUID, current_user: User
    ) -> ServiceRequest:
        """id로 요청 조회 후 소유권 검사. 없으면 404, 타인 소유 시 403."""
        request = await self.repo.get_by_id(id)
        if request is None:
            raise ServiceRequestNotFoundError()
        ensure_owner_or_admin(request.customer_id, current_user)
        return request
```

#### 라우터 확장 전체 코드
```python
# apps/api/app/routers/service_requests.py — UPDATE
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.deps import CurrentUser, require_role
from app.models.user import UserRole
from app.schemas.pagination import Page
from app.schemas.service_request import ServiceRequestCreate, ServiceRequestRead
from app.services.service_request import ServiceRequestService

router = APIRouter(prefix="/api/v1/service-requests", tags=["service-requests"])


@router.post("/", response_model=ServiceRequestRead, status_code=201)
async def create_service_request(
    body: ServiceRequestCreate,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    result = await svc.create(body, current_user)
    return result


@router.get("/", response_model=Page[ServiceRequestRead])
async def list_my_service_requests(
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> Page[ServiceRequestRead]:
    svc = ServiceRequestService(session)
    return await svc.list_mine(current_user, cursor, limit)


@router.get("/{request_id}", response_model=ServiceRequestRead)
async def get_service_request(
    request_id: uuid.UUID,
    current_user: CurrentUser,
    _: Annotated[None, Depends(require_role(UserRole.CUSTOMER))],
    session: AsyncSession = Depends(get_db),
) -> ServiceRequestRead:
    svc = ServiceRequestService(session)
    result = await svc.get_detail(request_id, current_user)
    return result
```

**⚠️ FastAPI 라우터 순서 주의:** `GET /{request_id}`보다 `GET /` 먼저 등록해야 한다. FastAPI는 순서대로 매칭하므로 고정 경로(`/`) 먼저, 동적 경로(`/{id}`) 나중. 위 코드 순서(POST / → GET / → GET /{id}) 그대로 유지.

### 테스트 헬퍼 구현 패턴

```python
# apps/api/tests/test_service_requests_list_detail.py

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid as _uuid

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
    # ... 동일 패턴

async def _make_admin(db: AsyncSession, email: str) -> User:
    # ... 동일 패턴, user_role=UserRole.ADMIN, is_seed=True

async def _make_category(db: AsyncSession, name: str = "청소") -> Category:
    # test_service_requests_create.py의 _make_category() 패턴 복제

async def _make_service_request(
    db: AsyncSession,
    customer: User,
    category: Category,
    description: str = "테스트 요청",
) -> ServiceRequest:
    """서비스 요청 생성 헬퍼 (service 계층 미경유, 직접 DB insert)."""
    import uuid_extensions
    req = ServiceRequest(
        id=uuid_extensions.uuid7(),
        customer_id=customer.id,
        category_id=category.id,
        region="서울 강남구",
        description=description,
        status=ServiceRequestStatus.OPEN,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    return req

def _auth(user: User) -> dict[str, str]:
    token = create_access_token({"user_id": str(user.id), "user_role": user.user_role.value})
    return {"Authorization": f"Bearer {token}"}
```

**테스트 cursor pagination 예시:**
```python
async def test_list_mine_cursor_pagination(client_db):
    client, db = client_db
    customer = await _make_customer(db, "page@test.com")
    cat = await _make_category(db)
    req1 = await _make_service_request(db, customer, cat, "첫 번째")
    req2 = await _make_service_request(db, customer, cat, "두 번째")  # 더 나중 생성 = 더 높은 id

    # 첫 번째 페이지 (limit=1) → 최신인 req2가 먼저 와야 함
    r = await client.get("/api/v1/service-requests", params={"limit": 1}, headers=_auth(customer))
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(req2.id)
    assert body["nextCursor"] is not None

    # 두 번째 페이지
    r2 = await client.get("/api/v1/service-requests", params={"limit": 1, "cursor": body["nextCursor"]}, headers=_auth(customer))
    assert r2.status_code == 200
    body2 = r2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["id"] == str(req1.id)
    assert body2["nextCursor"] is None
```

### user-web 상태 라벨 매핑 (일관성 유지)

```typescript
// 두 파일 모두 동일 매핑 사용
const STATUS_LABELS: Record<string, string> = {
  open: "접수됨",
  matched: "매칭됨",
  completed: "완료됨",
  cancelled: "취소됨",
};

// 사용: STATUS_LABELS[item.status] ?? item.status
```

### Orval 재생성 필수 절차

```powershell
# 1. apps/api에서 실행
cd apps/api
uv run python -c "import json; from app.main import app; open(r'../../openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"

# 2. 레포 루트
cd ../..
pnpm orval

# 3. 생성물 확인 후 커밋 (openapi.json 제외)
git add packages/api-client/src/generated/
```

**생성 훅 이름 예측 (확인 필수):**
- `list_my_service_requests` → `useListMyServiceRequests`
- `get_service_request` → `useGetServiceRequest`
- 실제 이름은 생성물(`packages/api-client/src/generated/service-requests/service-requests.ts`)에서 확인

---

## 파일 구조 요약

```
NEW (생성):
  apps/api/tests/test_service_requests_list_detail.py
  apps/user-web/src/app/(customer)/requests/[id]/page.tsx

UPDATE (수정):
  apps/api/app/core/exceptions.py         ← ServiceRequestNotFoundError 추가
  apps/api/app/repositories/service_requests.py  ← list_by_customer 추가
  apps/api/app/services/service_request.py       ← list_mine, get_detail 추가
  apps/api/app/routers/service_requests.py       ← GET /, GET /{id} 추가
  apps/user-web/src/app/(customer)/requests/page.tsx  ← 실구현 (플레이스홀더 교체)
  packages/api-client/src/generated/            ← Orval 재생성
```

---

## 테스트 요구사항

### 백엔드 테스트

**픽스처:** `client_db` (real DB, `join_transaction_mode="create_savepoint"` — conftest.py 수정 금지)

```
# 목록 엔드포인트 (GET /)
test_list_mine_success_200
test_list_mine_excludes_other_customers
test_list_mine_empty_200
test_list_mine_cursor_pagination
test_list_mine_newest_first
test_list_mine_no_token_401
test_list_mine_inactive_customer_401
test_list_mine_pro_role_403
test_list_mine_admin_role_403

# 상세 엔드포인트 (GET /{id})
test_get_detail_success_200
test_get_detail_other_customer_403
test_get_detail_not_found_404
test_get_detail_no_token_401
test_get_detail_pro_role_403
test_get_detail_admin_role_403
```

### 프론트엔드 검증 게이트

```
pnpm typecheck   ← 타입 오류 없음 (생성물 포함)
pnpm lint        ← ESLint 통과
pnpm build       ← Next.js 빌드 성공
```

---

## 이전 스토리 학습 사항 (2.1 → 2.2 계승)

1. **`uuid_extensions.uuid7()`** — `uuid7` 패키지 아님, `uuid_extensions` 패키지의 함수
2. **`ensure_owner_or_admin(resource_owner_id: UUID, ...)` — str 변환 없이 UUID 직접 전달** (deferred-work: str-vs-UUID 위험)
3. **PowerShell `>` 리다이렉트 절대 금지** — openapi.json 덤프는 Python `open(encoding='utf-8')` 방식만
4. **Orval 생성물은 커밋 대상** — `packages/api-client/src/generated/` gitignore 추가 금지
5. **conftest.py `join_transaction_mode="create_savepoint"` 수정 금지**
6. **FastAPI 라우터 등록 순서**: 고정 경로(`GET /`) 가 동적 경로(`GET /{id}`) 보다 먼저
7. **`AGENTS.md` 필독 의무**: user-web 코드 작성 전 `node_modules/next/dist/docs/` 확인
8. **기존 2.1 테스트 5개 실패** — DB 시드 오염(pre-existing), 내 변경과 무관 확인됨. 새 테스트 파일의 실패만 수정 대상
9. **Orval operationId 기반 훅 이름** — `list_my_service_requests` → `useListMyServiceRequests` (실제 이름은 생성물 확인 후 사용)

---

## 알려진 함정

1. **DESC keyset 방향 반전:** 카테고리(`id > after_id ASC`)와 달리 서비스 요청은 `id < after_id DESC`. 카테고리 패턴을 그대로 복사하면 방향이 반대가 되는 버그 발생.

2. **FastAPI 라우터 순서:** `GET /{request_id}` 가 `GET /` 보다 먼저 등록되면, `/api/v1/service-requests?cursor=xxx` 요청이 `{request_id}="?cursor=xxx"`로 매칭 시도 → 422 또는 예상치 못한 동작. **반드시 GET / → GET /{id} 순서로 등록.**

3. **`ensure_owner_or_admin` UUID 타입 일치:** `request.customer_id`는 ORM이 `UUID` 타입으로 반환하므로 str 변환 없이 직접 전달. 실수로 `str(request.customer_id)`를 전달하면 `UUID != str` 항상 True → 모든 고객에 403.

4. **ServiceRequestNotFoundError import:** `services/service_request.py`에서 `from app.core.exceptions import ServiceRequestNotFoundError` 반드시 추가.

5. **헬퍼 `_make_service_request` 직접 DB insert:** 테스트 헬퍼에서 `ServiceRequestService.create()` 경유 시 카테고리 검증이 일어남 → 헬퍼마다 카테고리 생성 필요. `ServiceRequest` 모델을 직접 db에 추가하는 방식이 더 단순 (카테고리 FK는 여전히 필요하므로 카테고리 헬퍼는 1개만 생성 후 재사용).

6. **cursor=None 시 empty 목록:** `list_by_customer`의 `if after_id is not None` 분기 미처리 시 전체 목록이 아니라 아무것도 반환되지 않는 버그 가능 → `None` 케이스는 조건절 없이 전체 조회.

7. **user-web `useParams` 타입:** Next.js App Router에서 `useParams()` 반환 타입은 `{ [key: string]: string | string[] }`. `id`를 `string`으로 사용하려면 타입 단언 또는 array 체크 필요.

8. **budget 없음/schedule 없음 필드:** 상세 페이지에서 `desiredSchedule`, `budget`이 `null` 일 수 있음 → 조건부 렌더링 필수.

---

## AR23 체크포인트 — 외부 수동 설정

**이 스토리는 외부 수동 설정 필요 없음.**

기존 Railway + Supabase(PostgreSQL) 설정과 Story 2.1의 Alembic 마이그레이션이 그대로 사용된다. 신규 테이블/마이그레이션 없음.

---

## 스토리 완료 기준

- [x] `uv run pytest tests/test_service_requests_list_detail.py -v` 전체 패스 (15/15)
- [x] `uv run pytest` 기존 테스트 회귀 없음 (5개 pre-existing 실패 제외, 92 passed)
- [x] `pnpm typecheck && pnpm lint && pnpm build` 전체 통과
- [x] `packages/api-client/src/generated/` 갱신 내용 커밋 포함
- [x] user-web `/requests` 목록 페이지: 실구현 완료 (상태 한국어 라벨, 클릭→상세 이동)
- [x] user-web `/requests/[id]` 상세 페이지: 전체 필드 렌더링 구현 완료

---

## Dev Agent Record

### 구현 계획

router → service → repository 레이어 규칙 준수. 총 8개 태스크 순서:
- Task 1: 예외 추가
- Task 2~4: 레포지토리→서비스→라우터 확장
- Task 5: 통합 테스트 (15케이스 전부 통과)
- Task 6~7: user-web 목록·상세 화면
- Task 8: Orval 재생성 + 커밋

### 완료 노트

Task 1~8 모두 완료. 백엔드 15개 테스트 신규 추가·전체 통과. 프론트엔드 typecheck/lint/build 전체 통과.

주요 구현:
- `ServiceRequestNotFoundError` 예외 추가
- `ServiceRequestRepository.list_by_customer()`: id DESC keyset cursor 페이지네이션
- `ServiceRequestService.list_mine()` / `get_detail()`: 소유권 검사 포함
- 라우터: `GET /` (목록), `GET /{request_id}` (상세) — 고정 경로 우선 등록 순서 준수
- user-web 목록·상세 페이지 구현 (Orval 생성 훅 사용)
- Orval 재생성: `useListMyServiceRequests`, `useGetServiceRequest` 훅 생성 확인

알려진 pre-existing 실패(5개, 변경과 무관): test_categories_list.py 3개, test_seed_categories.py 2개 (DB 시드 오염)

### File List

```
NEW:
  apps/api/tests/test_service_requests_list_detail.py
  apps/user-web/src/app/(customer)/requests/[id]/page.tsx

UPDATE:
  apps/api/app/core/exceptions.py
  apps/api/app/repositories/service_requests.py
  apps/api/app/services/service_request.py
  apps/api/app/routers/service_requests.py
  apps/user-web/src/app/(customer)/requests/page.tsx
  packages/api-client/src/generated/service-requests/service-requests.ts
  packages/api-client/src/generated/model/ (ServiceRequestRead 관련 업데이트)
```

---

### Review Findings

- [x] [Review][Patch] list_mine 서비스 레이어에 limit < 1 가드 없음 — limit=0이 내부 직접 호출되면 page_rows[-1] IndexError 발생. 라우터의 ge=1 검증만으론 서비스 레이어 자체 방어 미흡. [apps/api/app/services/service_request.py:list_mine]
- [x] [Review][Patch] 소프트 삭제 목록 제외 테스트 누락 — AC1 "deleted_at IS NOT NULL 요청 제외" 인수 기준에 대한 자동 검증 없음. `test_list_mine_excludes_soft_deleted` 케이스 추가 필요. [apps/api/tests/test_service_requests_list_detail.py]
- [x] [Review][Patch] 상세 조회 성공 테스트에서 desiredSchedule·budget 필드 미검증 — AC2 "요청 전체 필드 반환" 기준 미충족. `test_get_detail_success_200`에 nullable 선택 필드 assert 추가 필요. [apps/api/tests/test_service_requests_list_detail.py]
- [x] [Review][Defer] ServiceRequestRead.status: str — OpenAPI enum 범위 미노출. 기능 정상, 문서화 문제만. [apps/api/app/schemas/service_request.py] — deferred, pre-existing
- [x] [Review][Defer] desired_schedule·region 최대 길이 제한 없음 — DB/스키마 레벨 max_length 부재. 스펙 범위 외. [apps/api/app/schemas/service_request.py] — deferred, pre-existing
- [x] [Review][Defer] cursor base64 인코딩만, HMAC 서명 없음 — 위변조 방지 없으나 customer_id 필터로 데이터 노출 차단. CategoryService 동일 패턴. [apps/api/app/core/pagination.py] — deferred, pre-existing
- [x] [Review][Defer] status 컬럼 DB 레벨 server_default 없음 — ORM default만 설정(Python-side). Raw SQL insert 시 NOT NULL 위반 가능. 마이그레이션 생성 후 현재 쿼리 경로 안전. [apps/api/alembic/versions/e447c8a3f9b7] — deferred, pre-existing
- [x] [Review][Defer] 상세 화면에서 categoryId UUID 원시값 표시 — 카테고리 이름 조회 미연동. Epic 3 카테고리-견적 기능 도입 시 처리 예정. [apps/user-web/src/app/(customer)/requests/[id]/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] updatedAt UI 미표시 — AC4 "등" 열린 표현이어서 필수 위반 아님. 향후 필요 시 추가. [apps/user-web/src/app/(customer)/requests/[id]/page.tsx] — deferred, pre-existing
- [x] [Review][Defer] keyset pagination 중 신규 요청 삽입 시 2페이지 누락 — cursor 취득 후 새 요청 생성 시 해당 항목이 2페이지에서 skip됨. keyset pagination 알려진 trade-off. [apps/api/app/repositories/service_requests.py] — deferred, pre-existing
- [x] [Review][Defer] UUID7 동일 밀리초 페이지네이션 불안정성 — 밀리초 내 복수 생성 시 랜덤 비트 기반 정렬. 실용적으로 낮은 위험. [apps/api/app/repositories/service_requests.py] — deferred, pre-existing
- [x] [Review][Defer] cursor="" 빈 문자열 → 400 동작 미명세 — UUID 파싱 실패로 InvalidCursorError 발생하나 명세 없음. 실용적으로 낮은 위험. [apps/api/app/services/service_request.py] — deferred, pre-existing
- [x] [Review][Defer] 타인 ID cursor 주입 → 데이터 누출 없으나 페이지 건너뜀 — customer_id 필터로 데이터 보호됨. 의도치 않은 항목 skip 가능. 실용적으로 낮은 위험. [apps/api/app/repositories/service_requests.py] — deferred, pre-existing

## Change Log

- 2026-06-09: Story 2.2 스토리 파일 생성 (ready-for-dev)
- 2026-06-09: Story 2.2 구현 완료 (review) — 목록·상세 API + user-web 화면 + 15개 테스트
- 2026-06-09: Story 2.2 코드 리뷰 완료 — 3개 patch, 10개 defer, 7개 dismiss
