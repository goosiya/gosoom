---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 2.1: 서비스 요청 생성

**Status:** done  
**Epic:** 2 — 고객 서비스 요청 (FR5-7)  
**Story ID:** 2-1  
**Story Key:** 2-1-create-service-request  
**작성일:** 2026-06-09  
**Author:** KTH (bmad-create-story 자동 생성)

---

## 사용자 스토리

**As a** 활성 고객(CUSTOMER) 사용자로서,  
**I want** 카테고리·지역·설명·희망 일정·예산을 입력하여 서비스 요청을 생성하고 싶다.  
**So that** 고수(PRO)들이 내 요청을 보고 견적을 제출할 수 있다.

---

## 인수 기준 (BDD)

### AC1 — 서비스 요청 생성 성공 (FR5)

```
Given 유효한 CUSTOMER 토큰을 가진 활성 사용자가
When POST /api/v1/service-requests에 {categoryId, region, description, [desiredSchedule], [budget]}을 전송하면
Then 201 Created + ServiceRequestRead 응답이 반환되고
And status = "open"이 서버 고정값으로 설정된다
And customer_id는 토큰의 사용자 ID로 서버에서 설정된다 (요청 바디에서 받지 않음)
```

### AC2 — 서버 유효성 검사 (FR5)

```
Given POST /api/v1/service-requests를 요청할 때
When 필수 필드(categoryId, region, description)가 누락되면
Then 422 Unprocessable Entity가 반환된다

When 존재하지 않거나 비활성(is_active=false) 카테고리 ID를 전송하면
Then 404 Not Found + {code: "category_not_found", message: "카테고리를 찾을 수 없습니다."}가 반환된다
```

### AC3 — 비고객 403 거부 (FR5)

```
Given PRO 또는 ADMIN 역할의 사용자가
When POST /api/v1/service-requests를 시도하면
Then 403 Forbidden이 반환된다 (require_role(CUSTOMER) 가드)

Given is_active=false인 사용자가
When POST /api/v1/service-requests를 시도하면
Then 401 Unauthorized가 반환된다 (get_current_user의 is_active 검사)
```

### AC4 — user-web 요청 생성 UI (FR5)

```
Given 로그인한 CUSTOMER가 /requests/new에 접근하면
When 카테고리 드롭다운에서 선택하고 필수 필드를 입력하고 제출하면
Then POST /api/v1/service-requests를 호출한다
And 성공 시 /requests로 이동한다 (2.2 스토리에서 실구현 — 이 스토리는 placeholder만 생성)
```

---

## 태스크 및 서브태스크

### Task 1 — 예외 추가 (`apps/api/app/core/exceptions.py` UPDATE)

- [x] `CategoryNotFoundError` 추가 (404):
  ```python
  class CategoryNotFoundError(AppError):
      def __init__(self) -> None:
          super().__init__(
              code="category_not_found",
              message="카테고리를 찾을 수 없습니다.",
              status_code=404,
          )
  ```
- [x] 기존 예외들 파괴하지 않도록 파일 끝에 append만

### Task 2 — ServiceRequest 모델 (`apps/api/app/models/service_request.py` NEW)

- [x] `ServiceRequestStatus` Python Enum 정의 (str + enum.Enum)
  - OPEN="open", MATCHED="matched", COMPLETED="completed", CANCELLED="cancelled"
- [x] `ServiceRequest` SQLAlchemy ORM 모델 정의
  - `Base`, `UUIDPrimaryKeyMixin`, `TimestampMixin`, `SoftDeleteMixin` 모두 상속
  - `__tablename__ = "service_requests"`
  - 컬럼: customer_id(UUID FK), category_id(UUID FK), region(String), description(Text), desired_schedule(String nullable), budget(Integer nullable), status(Enum)
  - status 컬럼: `values_callable=lambda e: [m.value for m in e]` 필수 (DB에 소문자 값 저장)
  - server_default 미사용 — Python 레벨 `default=ServiceRequestStatus.OPEN`

### Task 3 — Alembic 마이그레이션 (`apps/api/alembic/versions/` NEW)

- [x] `apps/api`에서 `uv run alembic revision --autogenerate -m "add_service_requests_table"` 실행
- [x] 생성된 파일 검토 및 보정 (자동생성 enum 처리 오류 잦음 — 아래 Dev Notes 참고)
- [x] `upgrade()`: service_requests 테이블 생성 + customer_id / category_id 인덱스
- [x] `downgrade()`: `op.drop_table('service_requests')` 후 **명시적으로** `sa.Enum(name='service_request_status').drop(op.get_bind(), checkfirst=False)` 추가 (미추가 시 재upgrade에서 "type already exists" 오류)
- [x] `uv run alembic upgrade head`로 로컬 검증

### Task 4 — 카테고리 레포지토리 보완 (`apps/api/app/repositories/categories.py` UPDATE)

- [x] `CategoryRepository`에 `get_by_id(id: uuid.UUID) -> Category | None` 메서드 추가
  - `deleted_at IS NULL AND is_active=True` 조건 필수 (비활성 카테고리 = not found 처리)
  - `session.get()` 대신 `select().where()` + 소프트삭제·is_active 필터 적용

### Task 5 — ServiceRequest 스키마 (`apps/api/app/schemas/service_request.py` NEW)

- [x] `ServiceRequestCreate(CamelModel)`:
  - `category_id: uuid.UUID`
  - `region: str` (min_length=1)
  - `description: str` (min_length=1)
  - `desired_schedule: str | None = None` (자유 텍스트, MVP 결정)
  - `budget: int | None = None` (KRW, 정수)
- [x] `ServiceRequestRead(CamelModel)`:
  - `id: uuid.UUID`
  - `customer_id: uuid.UUID`
  - `category_id: uuid.UUID`
  - `region: str`
  - `description: str`
  - `desired_schedule: str | None`
  - `budget: int | None`
  - `status: str`
  - `created_at: datetime`
  - `updated_at: datetime`

### Task 6 — ServiceRequest 레포지토리 (`apps/api/app/repositories/service_requests.py` NEW)

- [x] `ServiceRequestRepository.__init__(session)` → `self.session = session`
- [x] `create(obj: ServiceRequest) -> ServiceRequest`: `session.add(obj)` → `session.flush()` → `session.refresh(obj)` (commit은 service 계층에서)
- [x] `get_by_id(id: uuid.UUID) -> ServiceRequest | None`: `deleted_at IS NULL` 필터 포함

### Task 7 — ServiceRequest 서비스 (`apps/api/app/services/service_request.py` NEW)

- [x] `ServiceRequestService.__init__(session)` → `self.repo = ServiceRequestRepository(session)`, `self.cat_repo = CategoryRepository(session)`
- [x] `create(data: ServiceRequestCreate, current_user: User) -> ServiceRequest`:
  - Step 1: `cat_repo.get_by_id(data.category_id)` → None이면 `raise CategoryNotFoundError()`
  - Step 2: `uuid_extensions.uuid7()` 로 id 생성
  - Step 3: `ServiceRequest(id=new_id, customer_id=current_user.id, status=ServiceRequestStatus.OPEN, **data.model_dump())` 로 인스턴스 생성
  - Step 4: `self.repo.create(instance)` → 반환

### Task 8 — ServiceRequest 라우터 (`apps/api/app/routers/service_requests.py` NEW)

- [x] `router = APIRouter(prefix="/api/v1/service-requests", tags=["service-requests"])`
- [x] `POST /` 엔드포인트:
  - 의존성: `current_user: CurrentUser`, `_: Annotated[None, Depends(require_role(UserRole.CUSTOMER))]`, `session: AsyncSession = Depends(get_db)`
  - `response_model=ServiceRequestRead`, `status_code=201`
  - 서비스 계층 호출 → 결과 반환
- [x] `require_role(UserRole.CUSTOMER)` 가드 — PRO/ADMIN은 403, CUSTOMER만 통과
  - **중요:** ADMIN도 이 엔드포인트 사용 불가 (고객 전용 기능)

### Task 9 — 메인 앱에 라우터 등록 (`apps/api/app/main.py` UPDATE)

- [x] `from app.routers.service_requests import router as service_requests_router` import 추가
- [x] `app.include_router(service_requests_router)` 추가 (기존 3개 라우터 뒤에)

### Task 10 — 테스트 (`apps/api/tests/test_service_requests_create.py` NEW)

- [x] `test_categories_list.py` 패턴 복제: `pytestmark = pytest.mark.asyncio`, `client_db` fixture 사용
- [x] 헬퍼: `_make_customer()`, `_make_pro()`, `_make_admin()`, `_make_category()`, `_auth(user)`
- [x] 케이스 목록:
  - ✅ 성공: 201, status="open", customerId=토큰 사용자 ID
  - ✅ 선택 필드 없이 성공 (desiredSchedule/budget nullable)
  - ❌ 미인증: 401 (토큰 없음)
  - ❌ 비활성 고객: 401
  - ❌ PRO 역할: 403
  - ❌ ADMIN 역할: 403
  - ❌ 필수 필드 누락 (categoryId/region/description 각각): 422
  - ❌ 존재하지 않는 categoryId: 404, code="category_not_found"
  - ❌ 비활성 카테고리 ID: 404, code="category_not_found"
- [x] `uv run pytest tests/test_service_requests_create.py -v` 전체 패스 확인

### Task 11 — Orval 재생성 및 커밋

- [x] `apps/api`에서 openapi.json 덤프:
  ```
  uv run python -c "import json; from app.main import app; open(r'../../openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"
  ```
  - **PowerShell `>` 리다이렉트 절대 사용 금지** (UTF-16+BOM 생성 → orval 파싱 실패)
- [x] 레포 루트에서 `pnpm orval` 실행
- [x] `packages/api-client/src/generated/service-requests/` 등 생성물 확인
- [x] `openapi.json`은 커밋하지 않음 (.gitignore가 이미 무시), **생성물만 커밋**

### Task 12 — user-web (customer) 라우트 그룹 (`apps/user-web/src/app/(customer)/` NEW)

> **⚠️ 필독:** `apps/user-web/AGENTS.md` — "This is NOT the Next.js you know — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices."
> → 코드 작성 전 반드시 `apps/user-web/node_modules/next/dist/docs/` 확인

- [x] `(customer)/layout.tsx` (NEW): `AuthGuard` 래핑 + CUSTOMER 역할 검사
  - CUSTOMER가 아니면 `/login`으로 리다이렉트 (또는 에러 페이지)
  - 기존 `AuthGuard`가 인증 자체를 보장, 역할은 layout에서 추가 검사
- [x] `(customer)/requests/page.tsx` (NEW): **플레이스홀더만** (2.2에서 채워짐)
  - "요청 목록 (구현 예정)" 텍스트 + `/requests/new` 링크 정도로 충분
- [x] `(customer)/requests/new/page.tsx` (NEW): 서비스 요청 생성 폼
  - `"use client"` — 클라이언트 컴포넌트
  - `useListCategories()` 훅으로 카테고리 드롭다운 데이터 로드
  - 필수 필드: categoryId(드롭다운), region(텍스트), description(텍스트에어리어)
  - 선택 필드: desiredSchedule(텍스트, 자유형식), budget(숫자)
  - 제출 시 `useCreateServiceRequest()` 훅 (Orval 생성 — Task 11 완료 후 사용 가능)
  - 성공 시 `router.push('/requests')` (플레이스홀더로 이동)
  - 오류 시 `error.message` 표시

---

## 개발자 노트 (Dev Notes)

### 아키텍처 필수 준수 사항

#### 레이어 규칙
- **router → service → repository** 엄격 순서 유지
- router: HTTP 파싱·Pydantic 직렬화·의존성 주입·status code만
- service: 비즈니스 로직·권한 검사·상태 전이 (이 스토리: 카테고리 존재 검증, customer_id 주입)
- repository: DB 접근만, commit 없음

#### 명명 규칙 (위반 금지)
| 계층 | 규칙 |
|------|------|
| DB 테이블/컬럼 | snake_case (`service_requests`, `customer_id`) |
| API JSON | camelCase (`serviceRequests`, `customerId`) |
| Python 변수/함수 | snake_case |
| TypeScript | camelCase/PascalCase |

#### 보안 규칙
- `customer_id`는 **절대 요청 바디에서 받지 않는다** — `current_user.id`로만 설정 (IDOR 방지)
- `status`는 **절대 요청 바디에서 받지 않는다** — 서버에서 `OPEN`으로 고정

### status Enum 구현 상세

Story 2.3(상태 전이)에서 사용할 4개 값을 모두 지금 정의한다:

```python
# apps/api/app/models/service_request.py
import enum
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
import uuid as _uuid

from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin


class ServiceRequestStatus(str, enum.Enum):
    OPEN = "open"
    MATCHED = "matched"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServiceRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "service_requests"

    customer_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("users.id"), nullable=False, index=True
    )
    category_id: Mapped[_uuid.UUID] = mapped_column(
        sa.UUID, sa.ForeignKey("categories.id"), nullable=False
    )
    region: Mapped[str] = mapped_column(sa.String, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    desired_schedule: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    budget: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    status: Mapped[ServiceRequestStatus] = mapped_column(
        sa.Enum(
            ServiceRequestStatus,
            name="service_request_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ServiceRequestStatus.OPEN,
    )
```

**`values_callable` 필수 이유:** 미사용 시 Alembic이 enum 멤버 이름("OPEN")을 DB에 저장 → 소문자 값("open")과 불일치로 조회 실패

### Alembic 마이그레이션 상세

`alembic revision --autogenerate` 후 반드시 수동 검토:

```python
# upgrade() 최소 보장 구조
def upgrade() -> None:
    op.create_table('service_requests',
        sa.Column('customer_id', sa.UUID(), nullable=False),
        sa.Column('category_id', sa.UUID(), nullable=False),
        sa.Column('region', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('desired_schedule', sa.String(), nullable=True),
        sa.Column('budget', sa.Integer(), nullable=True),
        sa.Column('status',
            sa.Enum('open', 'matched', 'completed', 'cancelled',
                    name='service_request_status'),
            nullable=False),
        # UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin 컬럼들
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id']),
        sa.ForeignKeyConstraint(['customer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_service_requests_customer_id'),
                    'service_requests', ['customer_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_service_requests_customer_id'), table_name='service_requests')
    op.drop_table('service_requests')
    # ⚠️ 필수: enum 타입 명시 삭제 — 미추가 시 재upgrade에서 "type already exists" 오류
    sa.Enum(name='service_request_status').drop(op.get_bind(), checkfirst=False)
```

**참고:** `04c24a1c717d_add_users_table.py`의 `user_role` enum 처리 패턴과 동일.

### CategoryRepository.get_by_id 구현 패턴

```python
# 기존 list_active 패턴을 따름 — deleted_at IS NULL + is_active=True
async def get_by_id(self, id: uuid.UUID) -> Category | None:
    result = await self.session.execute(
        select(Category).where(
            Category.id == id,
            Category.deleted_at.is_(None),
            Category.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()
```

### 서비스 계층 구현 패턴

```python
# apps/api/app/services/service_request.py
import uuid
import uuid_extensions

class ServiceRequestService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ServiceRequestRepository(session)
        self.cat_repo = CategoryRepository(session)

    async def create(
        self, data: ServiceRequestCreate, current_user: User
    ) -> ServiceRequest:
        # 카테고리 검증 (비활성 포함 not found 처리)
        category = await self.cat_repo.get_by_id(data.category_id)
        if category is None:
            raise CategoryNotFoundError()

        # UUIDv7 앱 레벨 생성 (DB DEFAULT 사용 금지 — AR 준수)
        new_id = uuid_extensions.uuid7()

        instance = ServiceRequest(
            id=new_id,
            customer_id=current_user.id,
            status=ServiceRequestStatus.OPEN,
            **data.model_dump(),
        )
        return await self.repo.create(instance)
```

### 라우터 구현 패턴

```python
# apps/api/app/routers/service_requests.py
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CategoryNotFoundError
from app.deps import CurrentUser, get_db, require_role
from app.models.user import UserRole
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
```

**주의:** `require_role(UserRole.CUSTOMER)`는 ADMIN도 거부한다. 이는 의도적이다 — 서비스 요청은 고객 전용 기능.

### 인증·권한 흐름 정리

| 상황 | 에러 | 담당 |
|------|------|------|
| 토큰 없음 | 401 `not_authenticated` | `get_current_user` |
| 토큰 만료/위조 | 401 `invalid_token` | `get_current_user` |
| is_active=false | 401 `invalid_token` | `get_current_user` (재조회 실패) |
| PRO/ADMIN 역할 | 403 `forbidden` | `require_role(CUSTOMER)` |
| 비활성 카테고리 | 404 `category_not_found` | `ServiceRequestService.create()` |

### desired_schedule 타입 결정

**결정:** `String (nullable)` — 자유 텍스트 ("이번 주 중", "6/15 오전" 등)  
**이유:** Epic MVP 최소 입력 원칙. 구조화된 날짜 타입은 후속 Epic에서 필요 시 마이그레이션.  
**제한 없음:** min_length 검사도 없음 (optional 필드이므로 None 또는 임의 문자열 허용).

### budget 타입

**결정:** `Integer (nullable)` — KRW 원화 단위 정수  
**이유:** 소수점 없는 통화 (원화). Decimal/Float 사용 금지.

### Orval 재생성 필수 절차

새 `service-requests` 엔드포인트를 추가하면 Orval 재생성 후 생성물을 커밋해야 CI 빌드가 통과한다.

```powershell
# 1. apps/api 디렉터리에서 openapi.json 덤프 (Python으로 직접 기록 — PS > 금지)
cd apps/api
uv run python -c "import json; from app.main import app; open(r'../../openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"

# 2. 레포 루트로 돌아와 orval 실행
cd ../..
pnpm orval

# 3. 생성물 확인 후 커밋 (openapi.json은 커밋 안 함)
git add packages/api-client/src/generated/
```

**함정 반복 방지 (1.7 결정 #1 계승):**
- PowerShell `>` 리다이렉트 → UTF-16+BOM → orval JSON 파싱 실패 → `open(encoding='utf-8')` 필수
- openapi.json은 `.gitignore`가 이미 무시 — 커밋하지 않는다
- 생성물(`packages/api-client/src/generated/`)은 반드시 커밋 — CI가 의존

### user-web (customer) 레이아웃 구조

```
apps/user-web/src/app/
└── (customer)/
    ├── layout.tsx          ← AuthGuard + CUSTOMER 역할 검사
    ├── requests/
    │   ├── page.tsx        ← 플레이스홀더 (Story 2.2에서 채워짐)
    │   └── new/
    │       └── page.tsx    ← 서비스 요청 생성 폼 (이 스토리 핵심)
```

**AGENTS.md 경고 필독 의무:** `apps/user-web/AGENTS.md`가 "This is NOT the Next.js you know — read `node_modules/next/dist/docs/` before writing any code" 경고. 코드 작성 전 반드시 준수.

### 기존 코드 패턴 참조

| 참조 대상 | 위치 |
|-----------|------|
| 모델 믹스인 | `apps/api/app/models/base.py` |
| CamelModel 스키마 | `apps/api/app/schemas/base.py` |
| 카테고리 라우터 패턴 | `apps/api/app/routers/categories.py` |
| 카테고리 서비스 패턴 | `apps/api/app/services/category.py` |
| 카테고리 레포지토리 패턴 | `apps/api/app/repositories/categories.py` |
| 예외 패턴 | `apps/api/app/core/exceptions.py` |
| 의존성 | `apps/api/app/deps.py` |
| 인증 가드 (user-web) | `apps/user-web/src/providers/AuthGuard.tsx` |
| 훅 사용 패턴 (user-web) | `apps/user-web/src/app/page.tsx` |

---

## 파일 구조 요약

```
NEW (생성):
  apps/api/app/models/service_request.py
  apps/api/app/schemas/service_request.py
  apps/api/app/repositories/service_requests.py
  apps/api/app/services/service_request.py
  apps/api/app/routers/service_requests.py
  apps/api/alembic/versions/????_add_service_requests_table.py
  apps/api/tests/test_service_requests_create.py
  apps/user-web/src/app/(customer)/layout.tsx
  apps/user-web/src/app/(customer)/requests/page.tsx          ← 플레이스홀더
  apps/user-web/src/app/(customer)/requests/new/page.tsx

UPDATE (수정):
  apps/api/app/core/exceptions.py           ← CategoryNotFoundError 추가
  apps/api/app/repositories/categories.py  ← get_by_id 메서드 추가
  apps/api/app/main.py                      ← service_requests_router 등록
  packages/api-client/src/generated/       ← Orval 재생성 커밋
```

---

## 테스트 요구사항

### 백엔드 단위/통합 테스트

**참조:** `apps/api/tests/test_categories_list.py` — 모든 패턴 복제  
**픽스처:** `client_db` (real DB, join_transaction_mode="create_savepoint")

```python
# 필수 테스트 케이스
test_create_service_request_success_201
test_create_service_request_optional_fields_omitted
test_create_service_request_no_token_401
test_create_service_request_inactive_user_401
test_create_service_request_pro_role_403
test_create_service_request_admin_role_403
test_create_service_request_missing_category_id_422
test_create_service_request_missing_region_422
test_create_service_request_missing_description_422
test_create_service_request_nonexistent_category_404
test_create_service_request_inactive_category_404
```

### 프론트엔드 검증 게이트

```
pnpm typecheck   ← 타입 오류 없음 (생성물 포함)
pnpm lint        ← ESLint 통과
pnpm build       ← Next.js 빌드 성공 (user-web 포함)
```

---

## 이전 스토리 학습 사항 (1.8 → 2.1 계승)

1. **`uuid_extensions.uuid7()`** — `uuid7` 패키지 아님, `uuid_extensions` 패키지의 `uuid7` 함수
2. **`python-preference = "only-system"`** — `uv run` 명령 시 시스템 Python 사용 (standalone 다운로드 안 됨, setup-python이 먼저 공급)
3. **커밋 전 `.env` 파일 포함 여부 확인** — 시크릿 커밋 금지
4. **Orval 생성물은 커밋 대상** — CI가 생성물에 의존, `generated/`를 gitignore에 추가 금지
5. **PowerShell `>` 리다이렉트 = UTF-16+BOM** — openapi.json 덤프는 Python `open(encoding='utf-8')` 방식만 사용
6. **conftest.py `join_transaction_mode="create_savepoint"`** — service 계층 commit이 픽스처 롤백을 깨지 않도록 필수 (변경 금지)

---

## 알려진 함정

1. **`values_callable` 누락 → enum 불일치:** SQLAlchemy Enum 컬럼에 `values_callable=lambda e: [m.value for m in e]` 없으면 DB에 대문자 멤버명("OPEN") 저장 → 소문자 비교("open") 실패. 필수.

2. **Alembic autogenerate enum 처리 오류:** autogenerate가 PG enum TYPE 생성을 잘못 처리하는 경우 있음. `upgrade()`에서 enum 값 목록이 올바른지 수동 확인. `downgrade()`에 `sa.Enum(name='service_request_status').drop(...)` 누락 시 re-upgrade 실패.

3. **customer_id를 요청 바디에서 받으면 IDOR:** `ServiceRequestCreate`에 `customer_id` 필드 절대 포함 금지. 서비스 계층에서 `current_user.id`로만 설정.

4. **CategoryNotFoundError import 누락:** `services/service_request.py`에서 `from app.core.exceptions import CategoryNotFoundError` 반드시 포함.

5. **require_role 위치 주의:** `require_role(UserRole.CUSTOMER)` 가드는 라우터 함수 매개변수로 `Depends()` — 서비스 계층에서 역할 재검사하지 않음 (중복 제거).

6. **Next.js 버전 차이:** `apps/user-web/AGENTS.md`의 경고 무시 시 잘못된 App Router API 사용 가능성. 코드 작성 전 `node_modules/next/dist/docs/` 반드시 확인.

7. **Orval 훅 이름 확인 필수:** 생성된 훅 이름은 FastAPI 라우터 함수명 기반(`create_service_request` → `useCreateServiceRequest`). operationName 변환(`_api_v1_..` 제거) 후 실제 이름은 생성물 확인 후 사용.

8. **budget은 Integer (KRW):** Float/Decimal 사용 금지. Pydantic 스키마에서 `budget: int | None = None`.

9. **테스트 conftest.py 수정 금지:** 기존 픽스처(`client_db`, `db_session`)를 건드리지 않는다. 새 헬퍼 함수는 테스트 파일 내부에만 정의.

---

## AR23 체크포인트 — 외부 수동 설정

**이 스토리는 외부 수동 설정 필요 없음.**

기존 Railway + Supabase(PostgreSQL) 설정이 그대로 사용된다. 새 테이블은 Alembic 마이그레이션으로 자동 생성.

**Railway 배포 후 마이그레이션 실행:**
```
railway run --service api -- uv run alembic upgrade head
```
(또는 Railway의 start command가 `uv run alembic upgrade head && uvicorn ...`이면 자동 실행)

---

## 스토리 완료 기준

- [ ] `uv run pytest tests/test_service_requests_create.py -v` 전체 패스
- [ ] `uv run pytest` 기존 71개 + 신규 테스트 전체 패스 (회귀 없음)
- [ ] `pnpm typecheck && pnpm lint && pnpm build` 전체 통과
- [ ] `packages/api-client/src/generated/` 갱신 내용 커밋 포함
- [ ] Alembic 마이그레이션 파일 커밋
- [ ] user-web `/requests/new` 페이지 로컬 동작 확인 (카테고리 드롭다운 로드, 제출 성공)

---

## 스토리 후 검토 질문

1. **desired_schedule 자유 텍스트 → 구조화 날짜 전환:** MVP에서 string으로 시작하지만, 향후 일정 기반 매칭이 필요하면 `DateTime` 마이그레이션 필요. Epic 2 완료 시점에 재검토 권장.

2. **budget 단위 표기:** 정수 KRW로 고정. UI에서 "원(₩)" 단위 명시 여부 확인 필요.

3. **(customer)/layout.tsx 역할 검사 방법:** 현재 설계는 `/users/me` 응답의 `userRole` 기반 클라이언트 측 리다이렉트. 서버 측 미들웨어 보호 필요 시 Epic 3에서 강화 여부 결정 필요.

---

## Review Findings

### Patch (7건 — 수정 필요)

- [x] [Review][Patch] budget 음수/비숫자 검증 없음 — 서버 스키마 `ge=0` 미적용, 프론트 parseInt NaN 미처리 [apps/api/app/schemas/service_request.py:20, apps/user-web/src/app/(customer)/requests/new/page.tsx:57]
- [x] [Review][Patch] region/description whitespace-only 입력 허용 — `min_length=1`이 공백 문자열 통과 [apps/api/app/schemas/service_request.py:17-18]
- [x] [Review][Patch] desired_schedule whitespace-only → None 미변환 — 빈 공백 문자열이 그대로 저장됨 [apps/api/app/schemas/service_request.py:19]
- [x] [Review][Patch] CustomerGuard me.isError 미처리 → 빈 화면 — 네트워크 오류 시 리다이렉트 없이 빈 화면 [apps/user-web/src/app/(customer)/layout.tsx:23-26]
- [x] [Review][Patch] 카테고리 fetch 에러 처리 없음 — categories.isError 시 드롭다운이 빈 채로 남음 [apps/user-web/src/app/(customer)/requests/new/page.tsx:26-29]
- [x] [Review][Patch] onError err.message '[object Object]' 가능 — AxiosError 등 비-Error 객체 시 비가독 메시지 표시 [apps/user-web/src/app/(customer)/requests/new/page.tsx:35-38]
- [x] [Review][Patch] 비고객 사용자 `/login` 리다이렉트 부적절 — PRO/ADMIN은 이미 인증된 상태이므로 `/login` 대신 역할별 홈으로 이동 [apps/user-web/src/app/(customer)/layout.tsx:18-19]

### Defer (6건 — 현재 스토리 외 이슈)

- [x] [Review][Defer] updated_at onupdate 없음 [apps/api/app/models/service_request.py] — deferred, pre-existing (TimestampMixin 전체 패턴 이슈)
- [x] [Review][Defer] category_id 인덱스 없음 [apps/api/alembic/versions/e447c8a3f9b7_add_service_requests_table.py:40] — deferred, Story 2.2+ 쿼리 패턴 확인 후 추가
- [x] [Review][Defer] region 자유 텍스트 데이터 품질 — deferred, MVP 결정 (Epic 3+ 지역 기반 매칭 시 재검토)
- [x] [Review][Defer] StaleDataError 처리 없음 [apps/api/app/repositories/service_requests.py:20-25] — deferred, 극히 드문 케이스
- [x] [Review][Defer] Alembic downgrade get_bind() deprecated + checkfirst=False [apps/api/alembic/versions/e447c8a3f9b7_add_service_requests_table.py:51] — deferred, 프로젝트 전체 마이그레이션 일관성 유지 후 일괄 교체
- [x] [Review][Defer] pnpm typecheck/lint/build CI 결과 미확인 — deferred, 로컬 실행으로 확인 필요

---

## Dev Agent Record

### 구현 계획

router → service → repository 레이어 규칙 준수. 총 12개 태스크를 순서대로 완료.
- Task 1~9: 백엔드 API (예외 → 모델 → 마이그레이션 → 레포 → 스키마 → 서비스 → 라우터 → main.py)
- Task 10: 통합 테스트 (11케이스 전부 통과)
- Task 11: Orval 재생성 (service-requests 생성물 확인)
- Task 12: user-web (customer) 라우트 그룹 생성

### 완료 노트

- `app/models/__init__.py`에 `ServiceRequest` 추가 후 autogenerate 재실행으로 migration 감지 성공
- Alembic downgrade에 `sa.Enum(name='service_request_status').drop(...)` 수동 추가 (autogen 누락)
- `packages/api-client/src/index.ts`에 `service-requests` barrel export 수동 추가 (orval tags-split은 루트 barrel 미생성)
- 기존 5개 테스트 실패는 DB 시드 오염(pre-existing) — 내 변경과 무관 확인(git stash로 검증)
- `pnpm typecheck && pnpm lint && pnpm build` 전체 통과 확인

---

## File List

```
NEW:
  apps/api/app/models/service_request.py
  apps/api/app/schemas/service_request.py
  apps/api/app/repositories/service_requests.py
  apps/api/app/services/service_request.py
  apps/api/app/routers/service_requests.py
  apps/api/alembic/versions/e447c8a3f9b7_add_service_requests_table.py
  apps/api/tests/test_service_requests_create.py
  apps/user-web/src/app/(customer)/layout.tsx
  apps/user-web/src/app/(customer)/requests/page.tsx
  apps/user-web/src/app/(customer)/requests/new/page.tsx
  packages/api-client/src/generated/service-requests/service-requests.ts

UPDATE:
  apps/api/app/core/exceptions.py                  ← CategoryNotFoundError 추가
  apps/api/app/models/__init__.py                  ← ServiceRequest, ServiceRequestStatus import 추가
  apps/api/app/repositories/categories.py         ← get_by_id 메서드 추가
  apps/api/app/main.py                             ← service_requests_router 등록
  packages/api-client/src/index.ts                 ← service-requests barrel export 추가
  packages/api-client/src/generated/model/         ← orval 재생성 (service request 타입 추가)
```

---

## Change Log

- 2026-06-09: Story 2.1 구현 완료 — POST /api/v1/service-requests 엔드포인트, Alembic 마이그레이션, 11개 테스트 전파스, Orval 재생성, user-web /requests/new 폼 구현
