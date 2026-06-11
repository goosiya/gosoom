---
baseline_commit: 8f838532fe9cd47150063589ab9c5327710562d3
---

# Story 3.1: 고수 활동 카테고리 설정

**Status:** done  
**Epic:** 3 — 고수 카테고리 & 견적 (FR9-12)  
**Story ID:** 3-1  
**Story Key:** 3-1-pro-categories-setup  
**작성일:** 2026-06-09  
**Author:** KTH (bmad-create-story 자동 생성)

---

## 사용자 스토리

**As a** 로그인한 고수(PRO)로서,  
**I want** 내 활동 카테고리를 복수로 설정·변경하고 싶다.  
**So that** 나에게 맞는 요청만 효율적으로 찾아볼 수 있다.

---

## 인수 기준 (BDD)

### AC1 — pro_categories 테이블 마이그레이션 (AR6/G1)

```
Given `pro_categories`(user_id FK→users.id, category_id FK→categories.id, 복합 PK) 테이블이 마이그레이션될 때
When `alembic upgrade head`를 실행하면
Then 테이블과 user_id 인덱스가 생성되고 멱등하게 재적용 가능하다
```

### AC2 — 카테고리 설정/교체 (FR9)

```
Given 로그인한 고수가
When PUT /api/v1/pros/me/categories에 categoryIds 배열([uuid, uuid, ...])을 보내면
Then 해당 고수의 활동 카테고리가 교체 저장되고(기존 삭제→신규 삽입)
And 현재 설정된 categoryIds 목록이 200으로 반환된다
```

```
Given 이미 카테고리가 설정된 고수가
When 다른 categoryIds 배열로 PUT을 재호출하면
Then 이전 설정이 완전히 교체되고 새 목록이 반환된다(append가 아닌 replace)
```

```
Given 고수가 빈 배열([])로 PUT을 호출하면
When 처리되면
Then 기존 카테고리가 모두 삭제되고 빈 목록이 반환된다
```

### AC3 — 현재 설정 조회 (UI 초기 표시용)

```
Given 로그인한 고수가
When GET /api/v1/pros/me/categories를 호출하면
Then 현재 설정된 categoryIds 목록이 200으로 반환된다
```

### AC4 — 유효성 검증

```
Given 존재하지 않는 category_id가 포함될 때
When PUT을 시도하면
Then 400 Bad Request + {code: "invalid_category_ids"}가 반환된다

Given is_active=false 또는 deleted_at IS NOT NULL인 카테고리 id가 포함될 때
When PUT을 시도하면
Then 400 Bad Request + {code: "invalid_category_ids"}가 반환된다
```

### AC5 — 권한 제어 (FR4, FR20)

```
Given 비인증이거나 비활성 고수(is_active=false)일 때
When 요청을 보내면
Then 401이 반환된다

Given CUSTOMER 또는 ADMIN 역할일 때
When PUT/GET /api/v1/pros/me/categories를 호출하면
Then 403 Forbidden + {code: "forbidden"}이 반환된다
```

### AC6 — user-web (pro)/categories 화면

```
Given 로그인한 PRO가 /categories 페이지에 접근하면
When 페이지가 로드되면
Then GET /api/v1/categories(시드 전체 목록)와 GET /api/v1/pros/me/categories(현재 선택)가 호출되고
And 시드 카테고리 목록이 체크박스로 표시되며 현재 선택된 것들이 체크된 상태로 보인다

When 고수가 카테고리를 선택/해제하고 저장하면
Then PUT /api/v1/pros/me/categories가 호출되고
And 성공 시 TanStack Query 캐시(pros/me/categories)가 무효화·갱신된다

When 뮤테이션이 진행 중이면
Then 저장 버튼이 disabled 처리된다(중복 클릭 방지)
```

---

## 태스크 및 서브태스크

### Task 1 — Alembic 마이그레이션 (`apps/api/alembic/versions/NEW_pro_categories.py` NEW)

- [x] `alembic revision --autogenerate -m "add_pro_categories_table"` 실행 후 생성물 검토
- [x] 생성물에 `op.create_table('pro_categories', ...)` 확인:
  - `user_id` UUID, FK→users.id, NOT NULL
  - `category_id` UUID, FK→categories.id, NOT NULL
  - PrimaryKeyConstraint('user_id', 'category_id') — **복합 PK, UUIDv7 단일 PK 없음**
  - ForeignKeyConstraint(['user_id'], ['users.id'])
  - ForeignKeyConstraint(['category_id'], ['categories.id'])
- [x] user_id 인덱스: `op.create_index(op.f('ix_pro_categories_user_id'), 'pro_categories', ['user_id'], unique=False)`
- [x] downgrade: `op.drop_index(...)`, `op.drop_table('pro_categories')`
- [x] `uv run alembic upgrade head` 통과 확인

### Task 2 — ORM 모델 (`apps/api/app/models/pro_category.py` NEW)

- [x] `ProCategory` 모델 작성:
  ```python
  import uuid as _uuid
  import sqlalchemy as sa
  from sqlalchemy.orm import Mapped, mapped_column
  from app.models.base import Base

  class ProCategory(Base):
      __tablename__ = "pro_categories"
      user_id: Mapped[_uuid.UUID] = mapped_column(
          sa.UUID, sa.ForeignKey("users.id"), primary_key=True, nullable=False
      )
      category_id: Mapped[_uuid.UUID] = mapped_column(
          sa.UUID, sa.ForeignKey("categories.id"), primary_key=True, nullable=False
      )
  ```
  - **UUIDPrimaryKeyMixin 미사용** — 복합 PK이므로 단일 UUID PK 없음
  - **TimestampMixin·SoftDeleteMixin 미사용** — 조인 테이블은 단순 존재 여부만
- [x] `apps/api/app/models/__init__.py` UPDATE — ProCategory import 추가:
  ```python
  from app.models.pro_category import ProCategory
  __all__ = [..., "ProCategory"]
  ```
  Alembic env.py가 `app.models`를 import해 autogenerate가 ProCategory를 감지한다.

### Task 3 — 예외 추가 (`apps/api/app/core/exceptions.py` UPDATE)

- [x] 파일 끝에 `InvalidCategoryIdsError` 추가:
  ```python
  class InvalidCategoryIdsError(AppError):
      """존재하지 않거나 비활성 카테고리 ID가 포함된 경우(Story 3.1 AC4). 400."""

      def __init__(self) -> None:
          super().__init__(
              code="invalid_category_ids",
              message="유효하지 않은 카테고리 ID가 포함되어 있습니다.",
              status_code=400,
          )
  ```
- [x] 기존 예외 파괴하지 않음 — 파일 끝에만 append

### Task 4 — 스키마 (`apps/api/app/schemas/pro_category.py` NEW)

- [x] 새 파일 생성:
  ```python
  """ProCategory Pydantic 스키마 (Story 3.1).

  ProCategoriesUpdate: 교체 대상 category_id 배열.
  ProCategoriesRead: 현재 설정된 category_id 목록 응답.
  """
  from uuid import UUID
  from app.schemas.base import CamelModel

  class ProCategoriesUpdate(CamelModel):
      category_ids: list[UUID]

  class ProCategoriesRead(CamelModel):
      category_ids: list[UUID]
  ```
- [x] `CamelModel` 상속 — JSON 경계에서 `categoryIds`로 camelCase 직렬화됨

### Task 5 — 레포지토리 (`apps/api/app/repositories/pro_categories.py` NEW)

- [x] `ProCategoryRepository` 구현:
  ```python
  """ProCategoryRepository — pro_categories 테이블 DB 접근 (Story 3.1).

  규약:
  - 트랜잭션(commit)은 소유하지 않는다 — 호출측(service)이 관리.
  - replace: 기존 행 DELETE + 신규 행 INSERT를 단일 flush에서 처리.
  """
  import uuid
  from sqlalchemy import delete, select
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.models.pro_category import ProCategory

  class ProCategoryRepository:
      def __init__(self, session: AsyncSession) -> None:
          self.session = session

      async def list_by_user(self, user_id: uuid.UUID) -> list[ProCategory]:
          result = await self.session.execute(
              select(ProCategory).where(ProCategory.user_id == user_id)
          )
          return list(result.scalars().all())

      async def replace(self, user_id: uuid.UUID, category_ids: list[uuid.UUID]) -> list[ProCategory]:
          """고수의 카테고리를 완전 교체. 기존 삭제 → 신규 삽입 → flush."""
          await self.session.execute(
              delete(ProCategory).where(ProCategory.user_id == user_id)
          )
          new_rows = [
              ProCategory(user_id=user_id, category_id=cat_id)
              for cat_id in category_ids
          ]
          for row in new_rows:
              self.session.add(row)
          await self.session.flush()
          return new_rows
  ```

### Task 6 — 서비스 (`apps/api/app/services/pro_category.py` NEW)

- [x] `ProCategoryService` 구현:
  ```python
  """ProCategoryService — 고수 활동 카테고리 비즈니스 로직 (Story 3.1).

  규칙:
  - 제공된 categoryIds 전체 유효성 검증(비활성·미존재 포함 시 InvalidCategoryIdsError).
  - replace semantics: DELETE+INSERT 단일 트랜잭션.
  - user_id는 current_user.id 직접 사용(IDOR 방지 — 경로 파라미터나 바디 미수용).
  """
  import uuid
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.core.exceptions import InvalidCategoryIdsError
  from app.models.user import User
  from app.repositories.categories import CategoryRepository
  from app.repositories.pro_categories import ProCategoryRepository
  from app.schemas.pro_category import ProCategoriesRead

  class ProCategoryService:
      def __init__(self, session: AsyncSession) -> None:
          self.repo = ProCategoryRepository(session)
          self.cat_repo = CategoryRepository(session)

      async def get_my_categories(self, current_user: User) -> ProCategoriesRead:
          rows = await self.repo.list_by_user(current_user.id)
          return ProCategoriesRead(category_ids=[r.category_id for r in rows])

      async def set_my_categories(
          self, category_ids: list[uuid.UUID], current_user: User
      ) -> ProCategoriesRead:
          # 빈 배열이면 유효성 검증 건너뜀(전체 삭제 허용)
          if category_ids:
              for cat_id in category_ids:
                  cat = await self.cat_repo.get_by_id(cat_id)
                  if cat is None:
                      raise InvalidCategoryIdsError()
          rows = await self.repo.replace(current_user.id, category_ids)
          return ProCategoriesRead(category_ids=[r.category_id for r in rows])
  ```
  > **⚠️ 유효성 검증 순서:** 전체 categoryId를 먼저 검증한 뒤 replace. 부분 삽입 금지(원자성).

### Task 7 — 라우터 (`apps/api/app/routers/pros.py` NEW)

- [x] 새 파일 생성:
  ```python
  """pros 라우터 — /api/v1/pros (Story 3.1).

  require_role(PRO): CUSTOMER·ADMIN 포함 PRO 외 모든 역할 403 거부.
  user_id는 current_user.id에서 주입 — 경로·바디 미수용(IDOR 방지).
  """
  from typing import Annotated
  from fastapi import APIRouter, Depends
  from sqlalchemy.ext.asyncio import AsyncSession
  from app.core.db import get_db
  from app.deps import CurrentUser, require_role
  from app.models.user import UserRole
  from app.schemas.pro_category import ProCategoriesRead, ProCategoriesUpdate
  from app.services.pro_category import ProCategoryService

  router = APIRouter(prefix="/api/v1/pros", tags=["pros"])

  @router.get("/me/categories", response_model=ProCategoriesRead)
  async def get_pro_categories(
      current_user: CurrentUser,
      _: Annotated[None, Depends(require_role(UserRole.PRO))],
      session: AsyncSession = Depends(get_db),
  ) -> ProCategoriesRead:
      svc = ProCategoryService(session)
      return await svc.get_my_categories(current_user)

  @router.put("/me/categories", response_model=ProCategoriesRead)
  async def set_pro_categories(
      body: ProCategoriesUpdate,
      current_user: CurrentUser,
      _: Annotated[None, Depends(require_role(UserRole.PRO))],
      session: AsyncSession = Depends(get_db),
  ) -> ProCategoriesRead:
      svc = ProCategoryService(session)
      return await svc.set_my_categories(body.category_ids, current_user)
  ```
  - `GET /me/categories` — 고정 경로 먼저 등록(FastAPI 라우터 순서 규칙 준수)
  - `PUT /me/categories` — 교체(replace-all) semantics
  - `operationId` 자동: `get_pro_categories`, `set_pro_categories` (Orval 훅 이름 기반)

### Task 8 — main.py 라우터 등록 (`apps/api/app/main.py` UPDATE)

- [x] import 추가:
  ```python
  from app.routers.pros import router as pros_router
  ```
- [x] `app.include_router(pros_router)` 추가 (기존 라우터 순서 유지, 맨 아래 추가):
  ```python
  app.include_router(pros_router)
  ```
- [x] 기존 auth/users/categories/service_requests 라우터 파괴하지 않음

### Task 9 — 테스트 (`apps/api/tests/test_pro_categories.py` NEW)

- [x] **픽스처 패턴**: `client_db: AsyncClient` + `db_session: AsyncSession` **별도 인자** (tuple 아님!)
  ```python
  async def test_xxx(client_db: AsyncClient, db_session: AsyncSession):
      ...
  ```
- [x] 헬퍼 함수 정의:
  ```python
  async def _make_pro(db: AsyncSession, email: str) -> User
  async def _make_customer(db: AsyncSession, email: str) -> User
  async def _make_admin(db: AsyncSession, email: str) -> User
  async def _make_category(db: AsyncSession, name: str = "청소") -> Category
  def _auth(user: User) -> dict[str, str]
  ```
- [x] **테스트 케이스 구현:**
  - ✅ `test_set_categories_200` — 카테고리 2개 설정 → 200 + category_ids 반환
  - ✅ `test_replace_categories_200` — 기존 설정 후 다른 목록으로 PUT → 완전 교체
  - ✅ `test_set_empty_categories_200` — 빈 배열 → 200 + 빈 목록 반환
  - ✅ `test_get_categories_200` — PUT 후 GET → 동일 목록 반환
  - ✅ `test_invalid_category_id_400` — 존재하지 않는 UUID → 400 + `code == "invalid_category_ids"`
  - ✅ `test_inactive_category_400` — is_active=False 카테고리 → 400 + `code == "invalid_category_ids"`
  - ✅ `test_no_token_401` — 토큰 없음 → 401
  - ✅ `test_inactive_pro_401` — is_active=False 고수 → 401
  - ✅ `test_customer_403` — CUSTOMER 역할 → 403
  - ✅ `test_admin_403` — ADMIN 역할 → 403
- [x] `uv run pytest tests/test_pro_categories.py -v` 전체 패스

### Task 10 — user-web 화면 (NEW 파일 2개)

> **⚠️ 필독:** `apps/user-web/AGENTS.md` — "This is NOT the Next.js you know". 코드 작성 전 `node_modules/next/dist/docs/` 확인.

#### Task 10a — `(pro)/layout.tsx` NEW (PRO 역할 가드)

- [x] `(customer)/layout.tsx` 패턴 복제, `userRole !== "pro"` 조건으로 수정:
  ```typescript
  "use client";
  import { useRouter } from "next/navigation";
  import { type ReactNode, useEffect } from "react";
  import { useReadMe, type UserRead } from "@gosoom/api-client";
  import { AuthGuard } from "@/providers/AuthGuard";

  function ProGuard({ children }: { children: ReactNode }) {
    const router = useRouter();
    const me = useReadMe<UserRead, Error>();

    useEffect(() => {
      if (me.isError) {
        router.replace("/login");
      } else if (me.data && me.data.userRole !== "pro") {
        router.replace("/");
      }
    }, [me.isError, me.data, router]);

    if (me.isPending) return null;
    if (me.isError) return null;
    if (me.data && me.data.userRole !== "pro") return null;

    return <>{children}</>;
  }

  export default function ProLayout({ children }: { children: ReactNode }) {
    return (
      <AuthGuard>
        <ProGuard>{children}</ProGuard>
      </AuthGuard>
    );
  }
  ```

#### Task 10b — `(pro)/categories/page.tsx` NEW

- [x] Orval 생성 훅 import (Task 11 완료 후 실제 이름 확인):
  ```typescript
  import {
    useListCategories,         // GET /api/v1/categories — 전체 시드 목록
    useGetProCategories,       // GET /api/v1/pros/me/categories — 현재 선택
    useSetProCategories,       // PUT /api/v1/pros/me/categories — 저장
    getGetProCategoriesQueryKey,
    type PageCategoryRead,
    type ProCategoriesRead,
  } from "@gosoom/api-client";
  import { useQueryClient } from "@tanstack/react-query";
  ```
- [x] `useState`로 로컬 선택 상태 관리:
  ```typescript
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // 초기화: useGetProCategories 데이터가 로드되면 selected를 채움
  useEffect(() => {
    if (current?.categoryIds) {
      setSelected(new Set(current.categoryIds));
    }
  }, [current]);
  ```
- [x] mutation + queryClient 설정:
  ```typescript
  const queryClient = useQueryClient();
  const mutation = useSetProCategories({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetProCategoriesQueryKey() });
      },
    },
  });
  ```
- [x] 체크박스 렌더링 + 저장 버튼:
  - 카테고리 목록을 checkbox로 표시
  - `selected` Set에 있으면 checked
  - 저장 버튼: `mutation.mutate({ data: { categoryIds: [...selected] } })`
  - `disabled={mutation.isPending}` 중복 클릭 방지
  - 에러 상태: `mutation.isError` 시 에러 메시지 표시
- [x] **실제 생성된 훅 이름·타입명·시그니처를 생성물에서 확인 후 코드 수정**

### Review Findings

#### Decision Needed

- [x] [Review][Decision] 카테고리 목록 페이지네이션 미처리 — `useListCategories({ params: { limit: 100 } })`로 수정 완료. [apps/user-web/src/app/(pro)/categories/page.tsx:80]
- [x] [Review][Patch] **[D2 resolved→CASCADE]** 마이그레이션 FK `ON DELETE CASCADE` 추가 — migration + ORM 모델 모두 `ondelete='CASCADE'` 적용 완료. [apps/api/alembic/versions/fc7ff3f42acd_add_pro_categories_table.py:27]

#### Patch

- [x] [Review][Patch] **CRITICAL: `ProCategoryService`에 `commit()` 없음 — 수정 완료** `self.session = session` 저장 + `await self.session.commit()` 추가. [apps/api/app/services/pro_category.py]
- [x] [Review][Patch] **CRITICAL: 중복 category_id 입력 시 IntegrityError → 500 — 수정 완료** `list(dict.fromkeys(category_ids))`로 중복 제거 (순서 보존). [apps/api/app/services/pro_category.py]
- [x] [Review][Patch] `category_ids` 배열 크기 상한 없음 — `Field(max_length=100)` 추가 완료. [apps/api/app/schemas/pro_category.py]
- [x] [Review][Patch] stale `initialIds`가 저장 실패 유발 — `allIdsSet` 필터 적용 완료. [apps/user-web/src/app/(pro)/categories/page.tsx]
- [x] [Review][Patch] PUT 엔드포인트 인증/권한 테스트 미커버 — `test_no_token_put_401`, `test_inactive_pro_put_401`, `test_customer_put_403`, `test_admin_put_403` 추가 완료. [apps/api/tests/test_pro_categories.py]
- [x] [Review][Patch] AC4 `deleted_at IS NOT NULL` 케이스 테스트 누락 — `test_soft_deleted_category_400` 추가 완료. [apps/api/tests/test_pro_categories.py]
- [x] [Review][Patch] `CategoryForm` `key` prop 순서 의존성 — `[...initialIds].sort().join(",")` 적용 완료. [apps/user-web/src/app/(pro)/categories/page.tsx]

#### Defer

- [x] [Review][Defer] N+1 쿼리 — 카테고리 유효성 검증 시 ID별 단건 SELECT 반복 [apps/api/app/services/pro_category.py:34-37] — deferred, `CategoryRepository.get_by_ids(list)` IN 쿼리로 최적화 필요하나 기능 정확성에 영향 없음. 성능 최적화 패스에서 처리.
- [x] [Review][Defer] 동시 PUT 요청 last-writer-wins — 동일 고수가 동시에 PUT 시 최종 상태 비결정론적 [apps/api/app/repositories/pro_categories.py:26-38] — deferred, 현재 규모에서 발생 가능성 낮음. 동시성 요구 증가 시 SELECT FOR UPDATE 또는 SERIALIZABLE 격리 도입.
- [x] [Review][Defer] AC4 fail-fast 검증 — 첫 번째 invalid ID에서 중단, 나머지 미검증 [apps/api/app/services/pro_category.py:33-37] — deferred, 부분 삽입은 발생하지 않으므로 기능적 무결성 유지. 전체 검증은 UX 개선 사항으로 분류.
- [x] [Review][Defer] ProGuard 클라이언트사이드 역할 검사 — 서버사이드 미들웨어 없음 [apps/user-web/src/app/(pro)/layout.tsx] — deferred, (customer)/layout.tsx와 동일 패턴. Next.js middleware 기반 보호는 인증 아키텍처 정비 시 일괄 처리.

### Task 11 — Orval 재생성 및 커밋

- [x] openapi.json 덤프 (**PowerShell `>` 리다이렉트 절대 금지**, Python `open` 방식):
  ```powershell
  cd apps/api
  uv run python -c "import json; from app.main import app; open(r'../../openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"
  ```
- [x] 레포 루트에서 `pnpm orval` 실행
- [x] `packages/api-client/src/generated/pros/` 디렉터리 확인:
  - `useGetProCategories` 훅 생성 확인
  - `useSetProCategories` 훅(PUT) 생성 확인
  - `ProCategoriesRead`, `ProCategoriesUpdate` 타입 생성 확인
  - `getGetProCategoriesQueryKey` queryKey 헬퍼 확인
- [x] `packages/api-client/src/index.ts`에 pros 모듈 export 추가 여부 확인(기존 패턴 따름)
- [x] **실제 생성된 함수명·타입명·시그니처를 생성물에서 확인 후 Task 10b 코드 수정**
- [x] `openapi.json` 삭제(커밋 제외), **생성물만 커밋 대상**:
  ```powershell
  Remove-Item openapi.json
  git add packages/api-client/src/generated/
  ```

---

## 개발자 노트 (Dev Notes)

### 핵심 설계 결정

#### pro_categories 복합 PK — UUIDv7 단일 PK 없음

```python
class ProCategory(Base):
    __tablename__ = "pro_categories"
    user_id: Mapped[uuid.UUID] = mapped_column(..., primary_key=True)
    category_id: Mapped[uuid.UUID] = mapped_column(..., primary_key=True)
```

- `UUIDPrimaryKeyMixin` **미사용** — M:N 조인 테이블은 복합 PK가 자연키
- `TimestampMixin`·`SoftDeleteMixin` **미사용** — 존재=선택, 부재=미선택의 단순 조인
- `id`·`created_at`·`updated_at`·`deleted_at` 컬럼 없음

#### PUT replace-all semantics

```python
# repository.replace() 내부:
await session.execute(delete(ProCategory).where(ProCategory.user_id == user_id))
for cat_id in category_ids:
    session.add(ProCategory(user_id=user_id, category_id=cat_id))
await session.flush()  # commit은 service가 아닌 라우터의 세션 컨텍스트에서
```

- 빈 배열 허용: 전체 삭제 후 빈 목록 반환 (고수가 카테고리 없이도 존재 가능)
- `append` 아닌 `replace` — 한 번의 PUT으로 완전한 상태로 갱신

#### 유효성 검증 순서

```
제공된 categoryIds 전체 유효성 검증 → replace
↑ 부분 삽입 금지: 일부만 유효하더라도 전체 실패 → 원자성 보장
```

`CategoryRepository.get_by_id()`는 `is_active=True AND deleted_at IS NULL` 둘 다 필터(categories.py:53). 비활성 또는 소프트삭제된 카테고리는 `None` 반환 → `InvalidCategoryIdsError` (400).

#### 라우터 등록 순서

```python
# pros.py 내부
GET  /me/categories   ← 고정 경로 먼저(FastAPI 순서 규칙)
PUT  /me/categories   ← 메서드 달라 충돌 없음
```

### 기존 파일 참조 (변경 대상)

| 파일 | 현재 상태 | 이 스토리 변경 |
|------|-----------|----------------|
| `apps/api/app/models/__init__.py` | User, Category, ServiceRequest 임포트 | ProCategory 임포트 추가 |
| `apps/api/app/core/exceptions.py` | InvalidStatusTransitionError까지 정의됨 | InvalidCategoryIdsError append |
| `apps/api/app/main.py` | service_requests_router까지 등록됨 | pros_router 등록 추가 |
| `packages/api-client/src/generated/` | service-requests까지 생성됨 | pros 모듈 추가 (Orval 재생성) |

### 아키텍처 필수 준수

#### 레이어 규칙 (2.x 계승)
- **router**: HTTP 파싱·의존성 주입·status code만 — 비즈니스 로직 없음
- **service**: 유효성 검증·replace 조율·소유권 보장 — **라우터/클라이언트 분산 금지**
- **repository**: DB 접근만, commit 없음

#### user_id 주입 방식 — IDOR 방지

```python
# ✅ 서비스 메서드: current_user.id에서 직접 추출
await svc.set_my_categories(body.category_ids, current_user)

# ❌ 절대 금지: 경로 파라미터나 바디에서 user_id 수용
PUT /api/v1/pros/{user_id}/categories  # IDOR 위험
```

#### ensure_owner_or_admin 미사용

이 스토리는 `me` 고정 경로 → `current_user.id` 직접 사용. `ensure_owner_or_admin`이 필요한 타인 자원 접근 패턴이 아님.

### 테스트 픽스처 패턴 — 핵심 함정

```python
# ✅ 올바른 패턴: client_db와 db_session 별도 인자
async def test_set_categories_200(client_db: AsyncClient, db_session: AsyncSession):
    cat = await _make_category(db_session, "청소")
    pro = await _make_pro(db_session, "pro@test.com")
    r = await client_db.put(
        "/api/v1/pros/me/categories",
        json={"categoryIds": [str(cat.id)]},
        headers=_auth(pro),
    )
    assert r.status_code == 200

# ❌ 틀린 패턴: client_db를 튜플로 취급
async def test_xxx(client_db):
    client, db = client_db  # ← conftest와 불일치, AttributeError 발생!
```

`client_db`는 `AsyncClient` 단일 객체, `db_session`은 별도 `AsyncSession` 픽스처.

### Orval 훅 예측 (생성물 확인 후 Task 10b 적용)

operationId `get_pro_categories`, `set_pro_categories` 기반 예측:

| 생성물 | 예측 이름 |
|--------|-----------|
| GET 훅 | `useGetProCategories` |
| PUT 뮤테이션 훅 | `useSetProCategories` |
| GET queryKey | `getGetProCategoriesQueryKey` |
| 입력 타입 | `ProCategoriesUpdate` |
| 응답 타입 | `ProCategoriesRead` |

> ⚠️ 실제 이름은 `packages/api-client/src/generated/pros/pros.ts` 확인 후 Task 10b 코드에 반영.  
> Orval은 operationId→함수명 변환 시 예측과 다를 수 있음.

**PUT 뮤테이션 시그니처 예측:**
```typescript
mutation.mutate({ data: ProCategoriesUpdate })
// data.categoryIds: string[] (UUID는 문자열로 직렬화됨)
```

### _make_category 중복 이름 함정

테스트 내 여러 테스트가 각자 카테고리를 생성할 때 같은 name 사용 시 unique 제약 위반:
```python
# ✅ 테스트마다 고유한 이름 사용
cat = await _make_category(db_session, "청소_c1")
# 다른 테스트에서:
cat = await _make_category(db_session, "청소_c2")
```

### api-client index.ts 확인 필요

기존 `packages/api-client/src/index.ts`에 service-requests 등이 export됨. Orval 재생성 후 `pros` 모듈도 자동 export되는지 확인. 수동 추가가 필요할 수 있음.

---

## 파일 구조 요약

```
NEW (생성):
  apps/api/alembic/versions/xxx_add_pro_categories_table.py
  apps/api/app/models/pro_category.py
  apps/api/app/repositories/pro_categories.py
  apps/api/app/services/pro_category.py
  apps/api/app/routers/pros.py
  apps/api/app/schemas/pro_category.py
  apps/api/tests/test_pro_categories.py
  apps/user-web/src/app/(pro)/layout.tsx
  apps/user-web/src/app/(pro)/categories/page.tsx

UPDATE (수정):
  apps/api/app/models/__init__.py              ← ProCategory import 추가
  apps/api/app/core/exceptions.py             ← InvalidCategoryIdsError append
  apps/api/app/main.py                        ← pros_router 등록
  packages/api-client/src/generated/          ← Orval 재생성 (pros/ 추가)
```

---

## 테스트 요구사항

### 백엔드 테스트

**픽스처:** `client_db: AsyncClient` + `db_session: AsyncSession` (별도, **conftest.py 수정 금지**)

```
test_set_categories_200        — 카테고리 2개 설정 → 200 + category_ids 반환
test_replace_categories_200    — 기존 설정 후 다른 목록 PUT → 완전 교체 확인
test_set_empty_categories_200  — 빈 배열 → 200 + 빈 목록 반환
test_get_categories_200        — GET → 현재 설정 반환
test_invalid_category_id_400   — 존재하지 않는 UUID → 400 + code == "invalid_category_ids"
test_inactive_category_400     — is_active=False 카테고리 → 400 + code == "invalid_category_ids"
test_no_token_401
test_inactive_pro_401
test_customer_403
test_admin_403
```

### 프론트엔드 검증 게이트

```
pnpm typecheck   ← 타입 오류 없음 (생성물 포함)
pnpm lint        ← ESLint 통과
pnpm build       ← Next.js 빌드 성공
```

---

## 이전 스토리 학습 사항 (2.x → 3.1 계승)

1. **`uuid_extensions.uuid7()`** — `uuid7` 패키지 아님, `uuid_extensions` 패키지의 함수
2. **`ensure_owner_or_admin` UUID 타입 일치** — str 변환 절대 금지 (이 스토리는 `me` 경로라 해당 없음)
3. **PowerShell `>` 리다이렉트 절대 금지** — openapi.json 덤프는 Python `open(encoding='utf-8')` 방식만
4. **Orval 생성물은 커밋 대상** — `packages/api-client/src/generated/` gitignore 추가 금지
5. **conftest.py 수정 금지** — `join_transaction_mode="create_savepoint"` 건드리지 말 것
6. **FastAPI 라우터 등록 순서**: `GET /me/categories` → `PUT /me/categories` (고정 경로 우선)
7. **AGENTS.md 필독 의무**: user-web 코드 작성 전 `node_modules/next/dist/docs/` 확인
8. **기존 테스트 pre-existing 실패**: test_categories_list.py 3개, test_seed_categories.py 2개 (DB 시드 오염) — 내 변경과 무관
9. **Orval 훅 이름 확인 필수** — 생성물(`pros/pros.ts`)에서 실제 이름 확인 후 Task 10b 코드에 반영
10. **`client_db` 튜플 패턴 금지** — `client_db: AsyncClient` + `db_session: AsyncSession` 별도 인자

---

## 알려진 함정

1. **ProCategory 복합 PK와 alembic autogenerate:** `UUIDPrimaryKeyMixin` 없으면 Alembic이 `id` 컬럼 없이 생성 — `PrimaryKeyConstraint('user_id', 'category_id')` 확인 필수.

2. **DELETE+INSERT flush 순서:** `replace`에서 DELETE가 flush 전에 실행되지 않으면 INSERT unique 충돌 가능. `delete()` statement 실행 후 `add()` → 단일 `flush()` 순서 지켜야 함.

3. **`category_ids` camelCase:** Pydantic `CamelModel`의 `alias_generator=to_camel`로 `categoryIds`로 직렬화됨. 클라이언트는 `{"categoryIds": [...]}` 전송. 테스트에서도 `json={"categoryIds": [...]}` 사용.

4. **`_make_category` is_active 초기값:** `Category(is_active=True)` 로 생성해야 `CategoryRepository.get_by_id`가 활성 카테고리로 인식. 기본값 누락 시 비활성으로 처리돼 모든 PUT이 400 실패.

5. **Alembic autogenerate 실행 전 모델 import:** `models/__init__.py`에 `ProCategory` import 추가 **후** `alembic revision --autogenerate`를 실행해야 테이블이 감지됨. 순서 반대 시 빈 마이그레이션 생성.

6. **GET /api/v1/categories vs GET /api/v1/pros/me/categories:** 프론트엔드는 두 API를 모두 호출함. categories는 전체 시드 목록(Story 1.6), pros/me/categories는 현재 고수의 선택 목록. 혼동 주의.

7. **user-web (pro) 라우트 그룹:** `(pro)/` 그룹 디렉터리를 먼저 생성 후 `layout.tsx`와 `categories/page.tsx`를 만들 것. 디렉터리 구조가 Next.js App Router에서 라우트 매핑됨.

---

## AR23 체크포인트 — 외부 수동 설정

**이 스토리는 외부 수동 설정 필요 없음.**

`pro_categories`는 신규 Alembic 마이그레이션만 필요하며, 기존 Railway + Supabase(PostgreSQL) 인프라를 그대로 사용한다. 마이그레이션은 `alembic upgrade head`로 적용됨.

---

## 스토리 완료 기준

- [x] `uv run alembic upgrade head` 통과 (`pro_categories` 테이블 생성 확인)
- [x] `uv run pytest tests/test_pro_categories.py -v` 전체 패스 (10/10)
- [x] `uv run pytest` 기존 테스트 회귀 없음 (pre-existing 5개 실패 제외)
- [x] `pnpm typecheck && pnpm lint && pnpm build` 전체 통과
- [x] `packages/api-client/src/generated/pros/` 생성 및 커밋 포함
- [x] user-web `/categories` 화면: 시드 카테고리 체크박스 표시 + 저장 동작

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `create_access_token` 시그니처 확인: `(user_id: UUID, user_role: UserRole)` — dict 방식 아님. 테스트 `_auth` 헬퍼 수정.
- ESLint `react-hooks/set-state-in-effect` 규칙: `useEffect` 내 `setState` 금지. `key` prop 패턴으로 자식 컴포넌트(`CategoryForm`)에 초기값 전달하는 방식으로 해결.

### Completion Notes List

- AC1: `pro_categories` 복합 PK 테이블 마이그레이션 + user_id 인덱스 생성 완료.
- AC2/AC3: PUT/GET `/api/v1/pros/me/categories` 엔드포인트 구현. replace semantics (DELETE+INSERT) 적용.
- AC4: 비활성·미존재 카테고리 → 400 `invalid_category_ids`. 유효성 검증 먼저(부분 삽입 금지).
- AC5: `require_role(PRO)` 가드. 비인증 401, PRO 외 역할 403.
- AC6: user-web `(pro)/categories/page.tsx` — 전체 카테고리 체크박스 + 저장. `CategoryForm` 자식 컴포넌트로 분리(ESLint set-state-in-effect 규칙 준수).
- 테스트 10/10 통과. `create_access_token(user.id, user.user_role)` 패턴 사용.
- Orval 재생성: `packages/api-client/src/generated/pros/pros.ts` 생성. `index.ts`에 수동 export 추가.

### File List

- `apps/api/alembic/versions/fc7ff3f42acd_add_pro_categories_table.py` (NEW)
- `apps/api/app/models/pro_category.py` (NEW)
- `apps/api/app/models/__init__.py` (UPDATED)
- `apps/api/app/core/exceptions.py` (UPDATED)
- `apps/api/app/schemas/pro_category.py` (NEW)
- `apps/api/app/repositories/pro_categories.py` (NEW)
- `apps/api/app/services/pro_category.py` (NEW)
- `apps/api/app/routers/pros.py` (NEW)
- `apps/api/app/main.py` (UPDATED)
- `apps/api/tests/test_pro_categories.py` (NEW)
- `apps/user-web/src/app/(pro)/layout.tsx` (NEW)
- `apps/user-web/src/app/(pro)/categories/page.tsx` (NEW)
- `packages/api-client/src/generated/pros/pros.ts` (NEW - Orval 생성)
- `packages/api-client/src/generated/model/proCategoriesRead.ts` (NEW - Orval 생성)
- `packages/api-client/src/generated/model/proCategoriesUpdate.ts` (NEW - Orval 생성)
- `packages/api-client/src/generated/model/index.ts` (UPDATED - Orval 재생성)
- `packages/api-client/src/index.ts` (UPDATED)

## Change Log

- 2026-06-09: Story 3.1 스토리 파일 생성 (ready-for-dev)
- 2026-06-09: Story 3.1 구현 완료 — pro_categories 마이그레이션, API 엔드포인트(GET/PUT), 테스트 10/10, user-web 카테고리 화면, Orval 재생성. Status → review.
