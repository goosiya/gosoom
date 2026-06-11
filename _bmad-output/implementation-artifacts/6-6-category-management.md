---
baseline_commit: "181ec13"
---

# Story 6.6: 카테고리 관리

Status: done

## Story

As a 관리자,
I want 서비스 카테고리를 생성·수정·(비)활성화하기를,
So that 고객 요청과 고수 활동에 사용될 카테고리 목록을 운영할 수 있다.

## Acceptance Criteria

1. **AC1 — 카테고리 생성:** 관리자가 `POST /api/v1/admin/categories`로 카테고리를 생성하면 새 카테고리가 생성되고 고객(FR5)·고수(FR9)의 선택 목록에 반영된다. 이름 중복 시 409 반환 (FR24).

2. **AC2 — 카테고리 수정:** 관리자가 `PATCH /api/v1/admin/categories/{id}`로 카테고리 이름을 수정하면 카테고리가 업데이트된다. 수정 후 이름이 다른 기존 카테고리와 중복 시 409 반환 (FR24).

3. **AC3 — 사용 중 카테고리 보호:** 어떤 요청(service_requests)이나 고수(pro_categories)가 참조 중인 카테고리를 관리자가 비활성화하면, 비활성화(is_active=False)는 허용된다. 다만 UI에서 사용 중 여부를 표시해 관리자가 인지할 수 있어야 한다 (FR24, NFR7).

4. **AC4 — 비활성화 효과:** 비활성화된 카테고리는 `GET /api/v1/categories` 활성 카테고리 조회에서 제외된다 — 고객 요청 생성(FR5) 및 고수 카테고리 설정(FR9) 선택 목록에 나타나지 않는다.

5. **AC5 — 관리자 목록 조회:** 관리자가 `GET /api/v1/admin/categories`를 호출하면 활성·비활성 모두 포함된 카테고리 목록이 cursor 페이지네이션으로 반환된다. 각 항목에는 `in_use` (사용 중 여부) 필드가 포함된다.

6. **AC6 — 관리 UI:** admin-web의 `/categories` 화면에서 생성·수정·비활성화 액션이 제공된다. 사용 중(`in_use=true`) 카테고리에는 비활성화 버튼만 노출되고, 비사용 카테고리에는 이름 변경 + 비활성화 버튼이 모두 노출된다. 비활성 카테고리에는 상태 배지만 표시된다.

## Dev Notes

### 아키텍처 핵심 제약 (위반 시 재작업)

- **패턴 A 엄수:** admin-web은 `@gosoom/api-client`만 통해 `/api/v1`에 접근. Supabase·DB 직접 접속 절대 금지 (AR8).
- **권한 최종 시행은 서버:** AdminGuard는 UX 보조. 실제 권한 검사는 FastAPI `require_role(UserRole.ADMIN)` (AR17).
- **service 계층이 비즈니스 로직 소유:** 라우터는 HTTP 변환만. 중복 검사·사용 여부 확인은 service에서 (NFR4).
- **Orval 생성물 수동 수정 금지:** `packages/api-client/src/generated/` 파일 편집하지 말 것 (AR9). 백엔드 변경 후 반드시 `pnpm orval` 재실행.
- **에러는 `error.message`로 노출:** 한국어 메시지는 백엔드 envelope `message` 필드 → api-client `ApiError.message` 변환 (AR12).
- **물리 삭제 절대 금지:** 카테고리는 `is_active=False` 비활성화만 허용, `deleted_at` 변경 엔드포인트 미제공 (FR24, NFR7).
- **Alembic 마이그레이션 불필요:** categories 테이블은 Story 1.6에서 이미 생성됨. 새 컬럼·테이블 없음.

### 기존 인프라 활용 (새로 구현 금지)

**기존 카테고리 모델 (수정 불필요):**
```python
# apps/api/app/models/category.py
class Category(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 상속: id (UUIDv7), created_at, updated_at, deleted_at
```

**기존 `CategoryRepository` 메서드 (수정 불필요):**
```python
# apps/api/app/repositories/categories.py
async def list_active(self, after_id, limit) -> list[Category]:
    """활성(is_active=True) + 미삭제(deleted_at IS NULL) 카테고리 id ASC."""
async def get_by_name(self, name: str) -> Category | None:
    """이름으로 미삭제 카테고리 조회 (중복 검사용)."""
async def get_by_id(self, id: UUID) -> Category | None:
    """활성·미삭제 카테고리만 조회 (비활성이면 None 반환)."""
async def create(self, category: Category) -> Category:
    """카테고리 추가 후 flush/refresh. commit은 호출측."""
```

**`CategoryRead` 기존 스키마 재사용:**
```python
# apps/api/app/schemas/category.py
class CategoryRead(CamelModel):
    id: UUID; name: str; is_active: bool; created_at: datetime; updated_at: datetime
```

**기존 pagination 패턴 재사용 (Story 6.2~6.5와 동일):**
```python
from app.core.pagination import decode_cursor, encode_cursor
from app.schemas.pagination import Page
```

**`AdminHeader.tsx` 에 `/categories` 링크 이미 존재:**
```ts
// apps/admin-web/src/components/AdminHeader.tsx
{ href: "/categories", label: "카테고리관리" }  // ← 이미 존재
```
→ 네비게이션 수정 불필요. `/categories/page.tsx` 파일만 생성.

**재사용할 admin-web 컴포넌트 (신규 설치 금지):**
```ts
import { AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
```

### 구현 순서 (중요: 순차 실행)

1. 백엔드 구현 (schema → exceptions → repository → service → router)
2. openapi.json 재생성
3. `pnpm orval` 실행 (api-client 훅 재생성)
4. admin-web 프론트엔드 구현

---

### 백엔드 구현 상세

#### 1. `apps/api/app/schemas/category.py` — 관리자용 스키마 추가

파일 하단에 추가 (기존 `CategoryRead` 보존):
```python
class CategoryCreate(CamelModel):
    """카테고리 생성 요청 (Story 6.6, AC1)."""
    name: str


class CategoryUpdate(CamelModel):
    """카테고리 수정 요청 (Story 6.6, AC2). None 필드는 변경 안 함."""
    name: str | None = None


class CategoryAdminRead(CamelModel):
    """관리자 전용 카테고리 응답 — 비활성 포함 + 사용 여부 (Story 6.6, AC5)."""
    id: UUID
    name: str
    is_active: bool
    in_use: bool
    created_at: datetime
    updated_at: datetime
```

→ `from datetime import datetime`와 `from uuid import UUID`는 파일 상단에 이미 import됨. `from app.schemas.base import CamelModel`도 이미 있음.

#### 2. `apps/api/app/core/exceptions.py` — 예외 추가

파일 하단에 추가:
```python
class DuplicateCategoryNameError(AppError):
    """이미 존재하는 카테고리 이름 생성·수정 시 (Story 6.6). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="category_name_already_exists",
            message="이미 존재하는 카테고리 이름입니다.",
            status_code=409,
        )
```

#### 3. `apps/api/app/repositories/categories.py` — 관리자용 메서드 추가

기존 `CategoryRepository` 클래스에 메서드 4개 추가:
```python
async def get_by_id_any(self, id: UUID) -> Category | None:
    """관리자용: is_active 무관, 미삭제 카테고리 단건 조회 (Story 6.6)."""
    result = await self.session.execute(
        select(Category).where(Category.id == id, Category.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()

async def list_all(self, after_id: UUID | None, limit: int) -> list[Category]:
    """관리자용: 활성·비활성 모두 포함, 미삭제, id ASC cursor (Story 6.6, AC5)."""
    stmt = select(Category).where(Category.deleted_at.is_(None))
    if after_id is not None:
        stmt = stmt.where(Category.id > after_id)
    stmt = stmt.order_by(Category.id).limit(limit)
    return list((await self.session.execute(stmt)).scalars().all())

async def save(self, category: Category) -> Category:
    """수정 후 flush/refresh. commit은 호출측 (UserRepository.save 패턴 복제)."""
    await self.session.flush()
    await self.session.refresh(category)
    return category
```

⚠️ `get_in_use_ids`는 cross-domain 쿼리이므로 service 계층에서 직접 처리 (repository 책임 범위 초과).

#### 4. `apps/api/app/services/admin.py` — `AdminCategoryService` 추가

파일 상단 imports에 추가:
```python
from app.core.exceptions import DuplicateCategoryNameError  # 추가
from app.models.category import Category                     # 추가
from app.models.pro_category import ProCategory              # 추가
from app.models.service_request import ServiceRequest         # 추가
from app.repositories.categories import CategoryRepository   # 추가
from app.schemas.category import (                           # 추가
    CategoryAdminRead,
    CategoryCreate,
    CategoryUpdate,
)
```

⚠️ 중복 import 주의: `ServiceRequest`, `ProCategory` 모델이 이미 import되어 있는지 확인 후 추가.

파일 하단에 새 클래스 추가 (`AdminChatService` 아래):
```python
class AdminCategoryService:
    """카테고리 생성·수정·비활성화 (Story 6.6, FR24)."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = CategoryRepository(session)
        self.session = session

    async def _get_in_use_ids(self, category_ids: list[UUID]) -> set[UUID]:
        """service_requests 또는 pro_categories에서 참조 중인 카테고리 ID 집합.

        service_requests: deleted_at IS NULL인 행만 (소프트 삭제된 요청 제외).
        pro_categories: 전체 (고수가 설정한 모든 카테고리 포함).
        """
        if not category_ids:
            return set()
        from sqlalchemy import select as _sel  # noqa: PLC0415 — 순환 import 방지

        sr_result = await self.session.execute(
            _sel(ServiceRequest.category_id).where(
                ServiceRequest.category_id.in_(category_ids),
                ServiceRequest.deleted_at.is_(None),
            ).distinct()
        )
        pc_result = await self.session.execute(
            _sel(ProCategory.category_id).where(
                ProCategory.category_id.in_(category_ids),
            ).distinct()
        )
        return {row[0] for row in sr_result} | {row[0] for row in pc_result}

    async def list_categories(
        self,
        cursor: str | None,
        limit: int,
    ) -> "Page[CategoryAdminRead]":
        """활성·비활성 전체 카테고리 목록 + 사용 여부 (AC5)."""
        assert limit >= 1, "limit must be >= 1"
        after_id: UUID | None = None
        if cursor:
            try:
                after_id = UUID(decode_cursor(cursor))
            except (ValueError, AttributeError) as exc:
                raise InvalidCursorError() from exc

        rows = await self.repo.list_all(after_id, limit + 1)
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = encode_cursor(str(page[-1].id)) if has_more else None

        if not page:
            return Page(items=[], next_cursor=None)

        in_use_ids = await self._get_in_use_ids([r.id for r in page])
        items = [
            CategoryAdminRead(
                id=r.id,
                name=r.name,
                is_active=r.is_active,
                in_use=(r.id in in_use_ids),
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in page
        ]
        return Page(items=items, next_cursor=next_cursor)

    async def create_category(self, data: CategoryCreate) -> CategoryAdminRead:
        """카테고리 생성 (AC1). 이름 중복 시 DuplicateCategoryNameError(409)."""
        name = data.name.strip()
        if await self.repo.get_by_name(name) is not None:
            raise DuplicateCategoryNameError()

        category = Category(name=name, is_active=True)
        category = await self.repo.create(category)
        await self.session.commit()

        in_use_ids = await self._get_in_use_ids([category.id])
        return CategoryAdminRead(
            id=category.id,
            name=category.name,
            is_active=category.is_active,
            in_use=(category.id in in_use_ids),
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    async def update_category(
        self, category_id: UUID, data: CategoryUpdate
    ) -> CategoryAdminRead:
        """카테고리 이름 수정 (AC2). 이름 중복 시 409. 비활성 카테고리도 수정 허용."""
        category = await self.repo.get_by_id_any(category_id)
        if category is None:
            raise CategoryNotFoundError()

        if data.name is not None:
            name = data.name.strip()
            existing = await self.repo.get_by_name(name)
            if existing is not None and existing.id != category_id:
                raise DuplicateCategoryNameError()
            category.name = name

        category = await self.repo.save(category)
        await self.session.commit()

        in_use_ids = await self._get_in_use_ids([category.id])
        return CategoryAdminRead(
            id=category.id,
            name=category.name,
            is_active=category.is_active,
            in_use=(category.id in in_use_ids),
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    async def deactivate_category(self, category_id: UUID) -> CategoryAdminRead:
        """카테고리 비활성화 (AC3, AC4). 사용 중 여부 무관하게 항상 허용.

        비활성화 후 GET /api/v1/categories 활성 목록에서 제외된다 (AC4).
        """
        category = await self.repo.get_by_id_any(category_id)
        if category is None:
            raise CategoryNotFoundError()

        category.is_active = False
        category = await self.repo.save(category)
        await self.session.commit()

        in_use_ids = await self._get_in_use_ids([category.id])
        return CategoryAdminRead(
            id=category.id,
            name=category.name,
            is_active=category.is_active,
            in_use=(category.id in in_use_ids),
            created_at=category.created_at,
            updated_at=category.updated_at,
        )
```

**imports 추가 시 주의:** `admin.py` 상단에서 이미 import된 항목 확인:
- `from app.models.service_request import ServiceRequest` — Story 6.4에서 이미 import됨.
- `from app.models.pro_category import ProCategory` — **신규 추가 필요**.
- `CategoryNotFoundError`는 이미 import됐는지 확인. 없으면 `app.core.exceptions` import 목록에 추가.

추가할 import 예시:
```python
from app.core.exceptions import (
    ...,
    CategoryNotFoundError,      # 신규 추가 (없을 경우)
    DuplicateCategoryNameError, # 신규 추가
)
from app.models.category import Category         # 신규 추가
from app.models.pro_category import ProCategory  # 신규 추가
from app.repositories.categories import CategoryRepository  # 신규 추가
from app.schemas.category import CategoryAdminRead, CategoryCreate, CategoryUpdate  # 신규 추가
```

#### 5. `apps/api/app/routers/admin.py` — 엔드포인트 4개 추가

기존 imports에 추가:
```python
from app.schemas.category import CategoryAdminRead, CategoryCreate, CategoryUpdate
from app.services.admin import AdminCategoryService, AdminChatService, AdminServiceRequestService, AdminUserService
```

라우터 하단에 추가:
```python
@router.get("/categories", response_model=Page[CategoryAdminRead])
async def list_admin_categories(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[CategoryAdminRead]:
    return await AdminCategoryService(db).list_categories(cursor, limit)


@router.post("/categories", response_model=CategoryAdminRead, status_code=201)
async def create_admin_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
) -> CategoryAdminRead:
    return await AdminCategoryService(db).create_category(data)


@router.patch("/categories/{category_id}", response_model=CategoryAdminRead)
async def update_admin_category(
    category_id: UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
) -> CategoryAdminRead:
    return await AdminCategoryService(db).update_category(category_id, data)


@router.post("/categories/{category_id}/deactivate", response_model=CategoryAdminRead)
async def deactivate_admin_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> CategoryAdminRead:
    return await AdminCategoryService(db).deactivate_category(category_id)
```

⚠️ `Page` import가 `app.schemas.pagination`에서 이미 있는지 확인 (admin.py 상단). `CategoryAdminRead`는 신규 추가.

#### 6. openapi.json 재생성 (백엔드 구현 완료 후)

`apps/api` 디렉토리에서 실행:
```bash
uv run python -c "
from app.main import app
import json
with open('../../openapi.json', 'w', encoding='utf-8') as f:
    json.dump(app.openapi(), f, ensure_ascii=False, indent=2)
print('openapi.json 재생성 완료')
"
```

확인: `openapi.json`에 `/api/v1/admin/categories` 경로 4개 + `CategoryAdminRead`·`CategoryCreate`·`CategoryUpdate` 스키마 포함 여부.

#### 7. pnpm orval — API 클라이언트 재생성

프로젝트 루트에서:
```bash
pnpm orval
```

생성/변경 결과 확인:
- `packages/api-client/src/generated/admin/admin.ts` — 신규 훅 4개:
  - `useListAdminCategories({ cursor?, limit? })` → `Page<CategoryAdminRead>` (query)
  - `useCreateAdminCategory(options?)` → `CategoryAdminRead` (mutation)
  - `useUpdateAdminCategory(options?)` → `CategoryAdminRead` (mutation)
  - `useDeactivateAdminCategory(options?)` → `CategoryAdminRead` (mutation)
- `packages/api-client/src/generated/model/categoryAdminRead.ts` — 신규 생성
- `packages/api-client/src/generated/model/categoryCreate.ts` — 신규 생성
- `packages/api-client/src/generated/model/categoryUpdate.ts` — 신규 생성
- `packages/api-client/src/generated/model/index.ts` — AUTO-UPDATED

⚠️ **Orval 훅명·파라미터 반드시 생성 파일 확인 후 import:**
- mutation 훅의 파라미터 형태: `.mutate({ categoryId, data })` vs `.mutate({ data })` — path param 유무에 따라 달라짐.
- `getListAdminCategoriesQueryKey` 함수명 확인 (cache invalidation에 사용).

---

### 프론트엔드 구현 상세

#### 8. `apps/admin-web/src/app/(admin)/categories/page.tsx` — 신규 생성

**페이지 구조:**
```
/categories 페이지
├─ 헤더: "카테고리 관리" 제목
├─ AddCategoryForm (Card)
│  └─ 이름 Input + "카테고리 추가" Button
└─ CategoryTable
   ├─ Table: 카테고리명 | 상태 | 사용여부 | 생성일 | 액션
   │  ├─ 활성 + 미사용: [이름 변경] [비활성화] 버튼
   │  ├─ 활성 + 사용중: [비활성화] 버튼 + "(사용 중)" 배지
   │  └─ 비활성: "비활성" 배지만, 버튼 없음
   └─ LoadMore: nextCursor 있을 때 "더 보기" 버튼
```

**구현 패턴 (admins/page.tsx의 AddAdminForm + AdminTable 패턴 적용):**
```tsx
"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  getListAdminCategoriesQueryKey,
  useCreateAdminCategory,
  useDeactivateAdminCategory,
  useListAdminCategories,
  useUpdateAdminCategory,
  type CategoryAdminRead,
} from "@gosoom/api-client";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

export default function CategoriesPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">카테고리 관리</h1>
      <AddCategoryForm />
      <CategoryTable />
    </main>
  );
}

function AddCategoryForm() {
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const createCategory = useCreateAdminCategory({
    mutation: {
      onSuccess: () => {
        setName("");
        setFormError(null);
        queryClient.invalidateQueries({ queryKey: getListAdminCategoriesQueryKey() });
      },
      onError: (error: unknown) => {
        setFormError(error instanceof Error ? error.message : "카테고리 추가 중 오류가 발생했습니다.");
      },
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    createCategory.mutate({ data: { name } });
  };

  return (
    <Card className="mb-8">
      <CardHeader>
        <CardTitle>신규 카테고리 추가</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <div className="grid gap-1.5">
            <Label htmlFor="category-name">카테고리명</Label>
            <Input
              id="category-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="예: 청소, 이사, 과외"
              className="w-64"
            />
          </div>
          <Button type="submit" disabled={createCategory.isPending}>
            {createCategory.isPending ? "추가 중..." : "카테고리 추가"}
          </Button>
        </form>
        {formError && (
          <div className="mt-3 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {formError}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CategoryTable() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<CategoryAdminRead[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useListAdminCategories({ limit: 20, cursor });

  // Story 6.2~6.5와 동일한 cursor 누적 패턴
  useEffect(() => {
    if (!data?.items) return;
    if (!cursor) {
      setAllItems(data.items);
    } else {
      setAllItems((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        return [...prev, ...data.items.filter((i) => !existingIds.has(i.id))];
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const invalidateList = () => {
    setActionError(null);
    queryClient.invalidateQueries({ queryKey: getListAdminCategoriesQueryKey() });
    setCursor(undefined);
    setAllItems([]);
  };

  const deactivate = useDeactivateAdminCategory({
    mutation: {
      onSuccess: invalidateList,
      onError: (error: unknown) => {
        setActionError(error instanceof Error ? error.message : "오류가 발생했습니다.");
      },
    },
  });

  const formatDate = (iso: string) => new Date(iso).toLocaleDateString("ko-KR");

  if (isLoading && allItems.length === 0) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="animate-pulse bg-muted rounded h-12" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {actionError && (
        <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError}
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>카테고리명</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>사용여부</TableHead>
            <TableHead>생성일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                카테고리가 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((cat) => (
              <TableRow key={cat.id}>
                <TableCell className="font-medium">{cat.name}</TableCell>
                <TableCell>
                  <Badge variant={cat.isActive ? "default" : "secondary"}>
                    {cat.isActive ? "활성" : "비활성"}
                  </Badge>
                </TableCell>
                <TableCell>
                  {cat.inUse ? (
                    <Badge variant="outline" className="text-xs">사용 중</Badge>
                  ) : (
                    <span className="text-sm text-muted-foreground">미사용</span>
                  )}
                </TableCell>
                <TableCell>{formatDate(cat.createdAt)}</TableCell>
                <TableCell>
                  <CategoryActions
                    category={cat}
                    onDeactivate={(id) => deactivate.mutate({ categoryId: id })}
                    onRenameSuccess={invalidateList}
                    isDeactivating={deactivate.isPending}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {data?.nextCursor && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => setCursor(data.nextCursor ?? undefined)}
            disabled={isFetching}
          >
            {isFetching ? "불러오는 중..." : "더 보기"}
          </Button>
        </div>
      )}
    </div>
  );
}

interface CategoryActionsProps {
  category: CategoryAdminRead;
  onDeactivate: (id: string) => void;
  onRenameSuccess: () => void;
  isDeactivating: boolean;
}

function CategoryActions({ category, onDeactivate, onRenameSuccess, isDeactivating }: CategoryActionsProps) {
  const [renameOpen, setRenameOpen] = useState(false);
  const [newName, setNewName] = useState(category.name);
  const [renameError, setRenameError] = useState<string | null>(null);

  const updateCategory = useUpdateAdminCategory({
    mutation: {
      onSuccess: () => {
        setRenameOpen(false);
        setRenameError(null);
        onRenameSuccess();
      },
      onError: (error: unknown) => {
        setRenameError(error instanceof Error ? error.message : "이름 변경 중 오류가 발생했습니다.");
      },
    },
  });

  if (!category.isActive) {
    return <span className="text-sm text-muted-foreground">비활성</span>;
  }

  return (
    <div className="flex gap-2">
      {!category.inUse && (
        <AlertDialog open={renameOpen} onOpenChange={(open) => {
          setRenameOpen(open);
          if (open) {
            setNewName(category.name);
            setRenameError(null);
          }
        }}>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm">이름 변경</Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>카테고리 이름 변경</AlertDialogTitle>
              <AlertDialogDescription>
                새 이름을 입력하세요.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <div className="py-2">
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="카테고리명"
              />
              {renameError && (
                <p className="mt-2 text-sm text-destructive">{renameError}</p>
              )}
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel>취소</AlertDialogCancel>
              <AlertDialogAction
                onClick={() =>
                  updateCategory.mutate({ categoryId: category.id, data: { name: newName } })
                }
                disabled={updateCategory.isPending || !newName.trim()}
              >
                {updateCategory.isPending ? "변경 중..." : "변경"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="outline" size="sm" disabled={isDeactivating}>
            비활성화
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>카테고리를 비활성화하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              "{category.name}"을(를) 비활성화하면 고객 요청 생성 및 고수 카테고리 설정
              목록에서 제외됩니다.
              {category.inUse && " 현재 사용 중인 카테고리입니다."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction onClick={() => onDeactivate(category.id)}>
              비활성화
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
```

⚠️ **주의사항:**
- `useCreateAdminCategory`의 mutate 파라미터 형태 (`{ data: CategoryCreate }`) — 생성된 `admin.ts` 파일에서 반드시 확인.
- `useUpdateAdminCategory`의 mutate 파라미터 형태: `{ categoryId: string, data: CategoryUpdate }` — path param 분리 여부 확인 (Story 6.5의 `useListAdminChatMessages(chatRoomId: string, params?)` 사례처럼 분리될 수 있음).
- `useDeactivateAdminCategory`의 mutate 파라미터: `{ categoryId: string }` — 생성 파일 확인.
- camelCase 변환: 백엔드 `is_active` → Orval이 `isActive`로, `in_use` → `inUse`로 변환. 생성 파일 확인 필수.
- `getListAdminCategoriesQueryKey` 함수명 — 생성 파일에서 확인 후 import.
- Next.js 15 breaking changes 주의: `apps/admin-web/AGENTS.md` 참조.

### 기존 코드 패턴 참조

| 패턴 | 참조 파일 |
|------|----------|
| cursor 누적 패턴 (useEffect) | `apps/admin-web/src/app/(admin)/admins/page.tsx:139` |
| Form + invalidateQueries 패턴 | `apps/admin-web/src/app/(admin)/admins/page.tsx:56-75` |
| AlertDialog 확인 패턴 | `apps/admin-web/src/app/(admin)/admins/page.tsx:235-259` |
| Table + LoadMore 패턴 | `apps/admin-web/src/app/(admin)/admins/page.tsx:130-281` |
| Cursor 페이지네이션 service | `apps/api/app/services/admin.py:AdminUserService.list_users` |
| list_all 패턴 | `apps/api/app/repositories/chat_rooms.py:list_all` |
| CategoryRepository.create 패턴 | `apps/api/app/repositories/categories.py:64` |
| UserRepository.save 패턴 | `apps/api/app/repositories/users.py:78` |

### Story 6.5 주요 학습사항 (적용 필수)

- **Orval 훅명:** 실제 생성 파일(`packages/api-client/src/generated/admin/admin.ts`)에서 export 이름 반드시 확인. 특히 mutation 훅의 파라미터 구조.
- **Windows cp949 인코딩 이슈:** `openapi.json` 재생성 시 stdout 대신 `open(..., encoding='utf-8')` 파일 직접 쓰기.
- **TypeScript 타입체크:** `node_modules/.bin/tsc --noEmit -p apps/admin-web/tsconfig.json`
- **ruff lint 확인:** `uv run ruff check app/` — 미사용 import (F401) 제거 필수.
- **camelCase alias:** Orval은 `is_active` → `isActive`, `in_use` → `inUse`로 변환. 생성 파일 타입 확인 필수.
- **AlertDialogAction + isPending:** `onClick` 핸들러 안에서 mutate 호출 시 AlertDialog가 닫히지 않아도 동작함. disabled 처리 필요.
- **queryClient.invalidateQueries 후 setCursor(undefined):** pagination 상태 초기화 필수. 그렇지 않으면 목록 갱신 안 됨.
- **`_sel` 지역 alias:** `services/admin.py` 상단에 이미 `from sqlalchemy import select`가 import됐을 수 있음. 재정의 충돌 방지를 위해 지역 변수 `_sel = select`로 사용하거나, 상단 import가 이미 있으면 그대로 사용.

## 파일 구조 (이 스토리에서 생성/수정)

```
apps/api/app/
├─ schemas/category.py         ← MODIFY: CategoryCreate, CategoryUpdate, CategoryAdminRead 추가
├─ core/exceptions.py          ← MODIFY: DuplicateCategoryNameError 추가
├─ repositories/categories.py  ← MODIFY: get_by_id_any, list_all, save 메서드 추가
├─ services/admin.py           ← MODIFY: imports 추가 + AdminCategoryService 클래스 추가
└─ routers/admin.py            ← MODIFY: imports 추가 + GET/POST/PATCH/POST 엔드포인트 4개 추가

openapi.json                   ← REGENERATE: CategoryAdminRead + /admin/categories 경로 4개

packages/api-client/src/
└─ generated/
   ├─ admin/admin.ts            ← AUTO-UPDATED: 신규 훅 4개 추가
   ├─ model/categoryAdminRead.ts ← AUTO-CREATED
   ├─ model/categoryCreate.ts   ← AUTO-CREATED
   ├─ model/categoryUpdate.ts   ← AUTO-CREATED
   └─ model/index.ts            ← AUTO-UPDATED

apps/admin-web/src/
└─ app/(admin)/categories/
   └─ page.tsx                  ← CREATE: 카테고리 관리 화면
```

## Tasks / Subtasks

- [x] Task 1 — 백엔드: Schema 추가 (AC1, AC2, AC5)
  - [x] 1.1: `apps/api/app/schemas/category.py` 하단에 `CategoryCreate` 추가 — `name: str`
  - [x] 1.2: `CategoryUpdate` 추가 — `name: str | None = None`
  - [x] 1.3: `CategoryAdminRead` 추가 — `id, name, is_active, in_use, created_at, updated_at` (CamelModel)

- [x] Task 2 — 백엔드: 예외 추가 (AC1, AC2)
  - [x] 2.1: `apps/api/app/core/exceptions.py` 하단에 `DuplicateCategoryNameError` 추가 — 409, `category_name_already_exists`

- [x] Task 3 — 백엔드: Repository 메서드 추가 (AC2, AC3, AC5)
  - [x] 3.1: `apps/api/app/repositories/categories.py`에 `get_by_id_any(id)` 추가 — is_active 무관, 미삭제 카테고리 단건 조회
  - [x] 3.2: `list_all(after_id, limit)` 추가 — 활성·비활성 포함, 미삭제, id ASC cursor
  - [x] 3.3: `save(category)` 추가 — flush/refresh, UserRepository.save 패턴 복제

- [x] Task 4 — 백엔드: AdminCategoryService 구현 (AC1~AC5)
  - [x] 4.1: `apps/api/app/services/admin.py` 상단 imports에 `DuplicateCategoryNameError`, `CategoryNotFoundError`, `Category`, `ProCategory`, `ServiceRequest`, `CategoryRepository`, `CategoryAdminRead`, `CategoryCreate`, `CategoryUpdate` 추가 (중복 import 주의)
  - [x] 4.2: `AdminCategoryService` 클래스 추가 — `__init__`, `_get_in_use_ids` (private, 2개 SELECT 쿼리)
  - [x] 4.3: `list_categories(cursor, limit)` 구현 — `repo.list_all` + `_get_in_use_ids` 배치 호출 + `Page[CategoryAdminRead]` 반환
  - [x] 4.4: `create_category(data)` 구현 — name strip + `get_by_name` 중복 검사 + `repo.create` + commit
  - [x] 4.5: `update_category(category_id, data)` 구현 — `get_by_id_any` + 중복 검사(name 변경 시) + `repo.save` + commit
  - [x] 4.6: `deactivate_category(category_id)` 구현 — `get_by_id_any` + `is_active=False` + `repo.save` + commit

- [x] Task 5 — 백엔드: 라우터 엔드포인트 추가 (AC1~AC5)
  - [x] 5.1: `apps/api/app/routers/admin.py` imports에 `CategoryAdminRead`, `CategoryCreate`, `CategoryUpdate`, `AdminCategoryService` 추가
  - [x] 5.2: `GET /categories` 추가 — cursor, limit 쿼리 파라미터, `Page[CategoryAdminRead]` 응답
  - [x] 5.3: `POST /categories` 추가 — `CategoryCreate` body, `CategoryAdminRead` 응답, status_code=201
  - [x] 5.4: `PATCH /categories/{category_id}` 추가 — `CategoryUpdate` body, `CategoryAdminRead` 응답
  - [x] 5.5: `POST /categories/{category_id}/deactivate` 추가 — `CategoryAdminRead` 응답

- [x] Task 6 — openapi.json 재생성 및 api-client 갱신 (AC1~AC5)
  - [x] 6.1: `apps/api` 디렉토리에서 `open(..., encoding='utf-8')` 방식으로 openapi.json 재생성 (Windows cp949 이슈 회피)
  - [x] 6.2: openapi.json에 `CategoryAdminRead` 스키마 + `inUse` 필드 포함 확인
  - [x] 6.3: openapi.json에 `/api/v1/admin/categories` 경로 4개 (GET, POST, PATCH, POST deactivate) 확인
  - [x] 6.4: 프로젝트 루트에서 `pnpm orval` 실행
  - [x] 6.5: 생성된 `packages/api-client/src/generated/admin/admin.ts`에서 훅 4개 이름 + 파라미터 구조 확인
  - [x] 6.6: `packages/api-client/src/generated/model/categoryAdminRead.ts` 생성 확인 + camelCase 변환 (`inUse`) 확인

- [x] Task 7 — admin-web: 카테고리 관리 페이지 구현 (AC6)
  - [x] 7.1: `apps/admin-web/src/app/(admin)/categories/page.tsx` 신규 생성 — `"use client"` 선언
  - [x] 7.2: `AddCategoryForm` 구현 — Input + submit, `useCreateAdminCategory` 훅 + `onSuccess` invalidate
  - [x] 7.3: `CategoryTable` 구현 — cursor 누적 패턴 (admins/page.tsx와 동일), `useListAdminCategories` 훅
  - [x] 7.4: 테이블 열 구성: 카테고리명 | 상태(활성/비활성 Badge) | 사용여부(사용중/미사용) | 생성일 | 액션
  - [x] 7.5: `CategoryActions` 컴포넌트 구현 — 활성+미사용: [이름 변경] + [비활성화], 활성+사용중: [비활성화]만, 비활성: 텍스트만
  - [x] 7.6: "이름 변경" AlertDialog 구현 — Input 포함, `useUpdateAdminCategory` 훅, 에러 표시
  - [x] 7.7: "비활성화" AlertDialog 확인 — `useDeactivateAdminCategory` 훅 + onSuccess invalidate
  - [x] 7.8: cursor 기반 "더 보기" 버튼 — `data.nextCursor` 있을 때 표시

- [x] Task 8 — 타입체크 및 lint 확인 (AC1~AC6)
  - [x] 8.1: `uv run ruff check app/` → All checks passed
  - [x] 8.2: `node_modules/.bin/tsc --noEmit -p apps/admin-web/tsconfig.json` → 오류 없음

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- 기존 테스트 5개 실패(`test_users_me.py`) — `secret-password` 대문자 부재로 인한 비밀번호 검증 오류, Story 6.6 이전부터 존재한 pre-existing 이슈. 189개 통과 확인.

### Completion Notes List

- Task 1~5: 백엔드 schema/exception/repository/service/router 순차 구현 완료.
- `ServiceRequest`는 기존 import에 없어 `from app.models.service_request import ServiceRequest, ServiceRequestStatus`로 확장.
- `AdminCategoryService._get_in_use_ids`: `service_requests`(deleted_at IS NULL 필터) + `pro_categories`(전체) 2쿼리 배치 방식으로 사용 중 여부 판별.
- `update_category`: 비활성 카테고리도 수정 허용 (`get_by_id_any` 사용).
- ruff lint → All checks passed.
- openapi.json 재생성 (Windows cp949 우회: `open(..., encoding='utf-8')`), 경로 4개 + `CategoryAdminRead` 스키마 확인.
- `pnpm orval` 실행 — 훅 4개(`useListAdminCategories`, `useCreateAdminCategory`, `useUpdateAdminCategory`, `useDeactivateAdminCategory`) + `categoryAdminRead.ts` 생성, `inUse`/`isActive` camelCase 변환 확인.
- admin-web `categories/page.tsx` 신규 생성 — admins/page.tsx 패턴 준수, AC6 조건별 액션 버튼 로직 구현.
- TypeScript 타입체크 → 오류 없음.

### File List

- `apps/api/app/schemas/category.py` — CategoryCreate, CategoryUpdate, CategoryAdminRead 추가
- `apps/api/app/core/exceptions.py` — DuplicateCategoryNameError 추가
- `apps/api/app/repositories/categories.py` — get_by_id_any, list_all, save 메서드 추가
- `apps/api/app/services/admin.py` — imports 확장 + AdminCategoryService 클래스 추가
- `apps/api/app/routers/admin.py` — imports 확장 + 엔드포인트 4개 추가
- `openapi.json` — /api/v1/admin/categories 경로 4개 + CategoryAdminRead 스키마 포함으로 재생성
- `packages/api-client/src/generated/admin/admin.ts` — 훅 4개 추가 (AUTO-UPDATED)
- `packages/api-client/src/generated/model/categoryAdminRead.ts` — 신규 생성 (AUTO-CREATED)
- `packages/api-client/src/generated/model/categoryCreate.ts` — 신규 생성 (AUTO-CREATED)
- `packages/api-client/src/generated/model/categoryUpdate.ts` — 신규 생성 (AUTO-CREATED)
- `packages/api-client/src/generated/model/index.ts` — AUTO-UPDATED
- `apps/admin-web/src/app/(admin)/categories/page.tsx` — 신규 생성

### Review Findings

- [x] [Review][Decision] in_use=true 카테고리 이름 수정에 대한 서버 측 가드 없음 — dismissed: UI 단 제한으로 충분 (관리자 콘솔 전용, AC6 충족)
- [x] [Review][Decision] get_by_name이 비활성(is_active=False) 카테고리도 이름 중복으로 처리 — dismissed: 현재 동작 유지 (비활성 이름 재사용 차단이 데이터 일관성 측면에서 안전)
- [x] [Review][Patch] list_categories: `if not page` 가드가 `next_cursor` 계산 이후에 위치 (dead code) [`services/admin.py`] — fixed
- [x] [Review][Patch] CategoryCreate.name 빈 문자열 허용 — `field_validator`로 strip 후 비어있으면 422 반환 [`schemas/category.py`] — fixed
- [x] [Review][Patch] CategoryUpdate.name 빈 문자열 허용 — `field_validator`로 strip 후 비어있으면 422 반환 [`schemas/category.py`] — fixed
- [x] [Review][Patch] TOCTOU: 이름 중복 체크와 INSERT/UPDATE 사이 경쟁 조건 — IntegrityError를 catch하여 DuplicateCategoryNameError(409)로 변환 [`services/admin.py`] — fixed
- [x] [Review][Defer] deactivate_category 이미 비활성화된 카테고리에 불필요한 flush/commit [`services/admin.py`] — deferred, 멱등성은 유지되나 불필요한 DB write 발생

## Change Log

- 2026-06-12: Story 6.6 스토리 파일 생성
- 2026-06-12: Story 6.6 구현 완료 — 백엔드 4엔드포인트 + api-client 재생성 + admin-web 카테고리 관리 페이지
