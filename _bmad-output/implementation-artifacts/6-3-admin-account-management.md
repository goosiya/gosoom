---
baseline_commit: "3cf5f3459f9063bbe0ba409bffaf0d6caa1e810f"
---

# Story 6.3: 관리자 계정 관리

Status: done

## Story

As a 관리자,
I want 관리자 계정 목록을 조회하고 신규 관리자를 추가하거나 기존 관리자를 비활성화하기를,
So that 운영 권한을 안전하게 위임·회수할 수 있다.

## Acceptance Criteria

1. **AC1 — 목록 조회:** 관리자가 `GET /api/v1/admin/admins`로 관리자 계정 목록을 조회하면 `user_role=admin`인 미삭제 계정이 `{items, nextCursor}` cursor 페이지네이션으로 반환된다 (FR21).

2. **AC2 — 신규 관리자 생성:** 관리자가 이메일+비밀번호+표시명을 제출하면 `user_role=admin` 계정이 생성되어 반환된다. 이미 존재하는 이메일은 409 반환. 자가 가입(`/signup`) 경로는 허용하지 않음 — 기존 관리자에 의한 생성 경로만 허용 (FR1/FR21).

3. **AC3 — 비활성화:** 관리자가 활성 관리자 계정을 비활성화하면 `is_active=false`로 설정된다. 단, `is_seed=true`인 시드 관리자 비활성화 시도는 거부(409)되어 잠금 방지 (FR21).

4. **AC4 — 관리 UI:** admin-web의 `/admins` 화면에서 관리자 계정 목록이 표시되고, 신규 관리자 추가 폼과 비활성화 버튼이 제공된다. 시드 관리자(`isSeed=true`) 행에는 비활성화 버튼이 비활성화된다.

## Dev Notes

### 아키텍처 핵심 제약 (위반 시 재작업)

- **패턴 A 엄수:** admin-web은 `@gosoom/api-client`만 통해 `/api/v1`에 접근. Supabase·DB 직접 접속 절대 금지 (AR8).
- **권한 최종 시행은 서버:** AdminGuard는 UX 보조. 실제 권한 검사는 FastAPI `require_role('admin')` (AR17).
- **비활성화 = 소프트:** `is_active=False`만 설정. 물리 삭제/데이터 제거 금지 (R3).
- **service 계층이 비즈니스 로직 소유:** 라우터는 HTTP 변환만. 시드 관리자 보호 규칙 등 모든 검사는 service에서 시행 (NFR4).
- **Orval 생성물 수동 수정 금지:** `packages/api-client/src/generated/` 파일 편집하지 말 것 (AR9). 백엔드 변경 후 반드시 `pnpm orval` 재실행.
- **에러는 `error.message`로 노출:** 한국어 메시지는 백엔드 envelope `message` 필드 → api-client `ApiError.message` 변환 (AR12).
- **`UserRead` 스키마에 `is_seed` 추가 필수:** 현재 `UserRead`에는 `is_seed` 필드가 없다. 프론트엔드에서 시드 관리자 비활성화 버튼 비활성화가 필요하므로 `UserRead`에 `is_seed: bool` 추가 후 `pnpm orval` 재실행 필수. 기존 `user-web`·`mobile` 클라이언트는 이 필드를 사용하지 않으므로 하위 호환.

### 기존 인프라 활용 (새로 구현 금지)

**`is_active` 차단 로직은 이미 구현됨 — 새 코드 불필요:**
```python
# apps/api/app/deps.py:77-79 — 매 요청 DB 재조회로 비활성 계정 즉시 차단
user = await UserRepository(db).get_by_id(user_id)
if user is None or not user.is_active:
    raise InvalidTokenError()  # → 401 반환
```
비활성화된 관리자 계정은 다음 API 요청부터 자동으로 401을 받아 콘솔에서 강제 로그아웃된다.

**재사용할 기존 패턴:**
```python
# 비밀번호 해싱 — apps/api/app/services/auth.py
from app.core.security import hash_password

# Repository create 메서드 — apps/api/app/repositories/users.py:84
async def create(self, user: User) -> User: ...

# DuplicateEmailError — apps/api/app/core/exceptions.py:39
from app.core.exceptions import DuplicateEmailError

# 목록 조회 — list_by_role() 재사용 (ADMIN role도 동일 메서드 사용)
async def list_by_role(self, role: UserRole, after_id: UUID | None, limit: int) -> list[User]: ...
```

**`SignupRequest`는 `role=admin`을 거부함 — 관리자 생성에 사용 불가:**
```python
# apps/api/app/schemas/auth.py:29
role: Literal["customer", "pro"]  # admin 불허
```
→ 별도 `AdminCreateRequest` 스키마를 `apps/api/app/schemas/auth.py`에 추가해야 한다.

**재사용할 기존 컴포넌트 (admin-web):**
```ts
// Story 6.2에서 생성된 UI 컴포넌트들
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertDialog, ... } from "@/components/ui/alert-dialog";
import { Table, TableBody, TableCell, ... } from "@/components/ui/table";

// Story 6.1에서 생성된 컴포넌트
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
```

**AdminHeader.tsx에 이미 `/admins` 네비 링크 존재:**
```ts
// apps/admin-web/src/components/AdminHeader.tsx:13-14
const NAV_LINKS = [
  { href: "/users", label: "계정관리" },
  { href: "/admins", label: "관리자관리" },  // ← 이미 존재
  ...
];
```
→ 네비게이션 수정 불필요. `/admins` 페이지만 생성하면 된다.

### 구현 순서 (중요: 순차 실행)

1. 백엔드 구현 (schemas → service → router → main.py)
2. openapi.json 재생성
3. `pnpm orval` 실행 (api-client 훅 재생성)
4. admin-web 프론트엔드 구현

### 백엔드 구현 상세

#### 1. `apps/api/app/schemas/auth.py` — `UserRead`에 `is_seed` 추가 + `AdminCreateRequest` 추가

**`UserRead`에 `is_seed: bool` 필드 추가:**
```python
class UserRead(CamelModel):
    """안전한 사용자 표현(비밀번호 제외). ORM User 객체에서 직접 직렬화."""

    id: UUID
    email: str
    display_name: str
    user_role: UserRole
    is_active: bool
    is_seed: bool       # ← 추가: 시드 관리자 잠금 방지 UI 표시에 사용 (FR21)
    created_at: datetime
    updated_at: datetime
```

**`AdminCreateRequest` 신규 추가 (파일 하단):**
```python
class AdminCreateRequest(CamelModel):
    """관리자가 신규 관리자를 생성하는 입력. role은 항상 admin으로 고정 — 입력 불필요(FR21)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("email", mode="after")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("display_name", mode="after")
    @classmethod
    def _strip_display_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("표시명은 공백일 수 없습니다.")
        return stripped
```

#### 2. `apps/api/app/core/exceptions.py` — 예외 1개 추가

기존 `UserNotFoundError` 아래에 추가:
```python
class SeedAdminDeactivationError(AppError):
    """시드 관리자 비활성화 시도 시(FR21). 409."""

    def __init__(self) -> None:
        super().__init__(
            code="seed_admin_deactivation_forbidden",
            message="시드 관리자는 비활성화할 수 없습니다.",
            status_code=409,
        )
```

#### 3. `apps/api/app/services/admin.py` — 관리자 계정 관리 메서드 추가

기존 `AdminUserService` 클래스에 메서드 3개 추가:

```python
# 파일 상단 imports에 추가
from app.core.exceptions import (
    DuplicateEmailError,
    ForbiddenError,
    InvalidCursorError,
    SeedAdminDeactivationError,  # 추가
    UserNotFoundError,
)
from app.core.security import hash_password  # 추가
from app.models.user import User, UserRole
from app.schemas.auth import AdminCreateRequest, UserRead  # AdminCreateRequest 추가
```

추가할 메서드들:
```python
async def list_admins(
    self,
    cursor: str | None,
    limit: int,
) -> Page[UserRead]:
    """관리자(ADMIN role) 목록 조회 — cursor 페이지네이션."""
    after_id: UUID | None = None
    if cursor:
        try:
            after_id = UUID(decode_cursor(cursor))
        except (ValueError, AttributeError) as exc:
            raise InvalidCursorError() from exc
    rows = await self.repo.list_by_role(UserRole.ADMIN, after_id, limit + 1)
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = encode_cursor(str(page[-1].id)) if has_more else None
    return Page(
        items=[UserRead.model_validate(u) for u in page],
        next_cursor=next_cursor,
    )

async def create_admin(self, data: "AdminCreateRequest") -> UserRead:
    """신규 관리자 생성 — 기존 관리자에 의한 생성 경로만 허용(FR1/FR21)."""
    existing = await self.repo.get_by_email(data.email)
    if existing is not None:
        raise DuplicateEmailError()
    from sqlalchemy.exc import IntegrityError
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        display_name=data.display_name,
        user_role=UserRole.ADMIN,
    )
    try:
        await self.repo.create(user)
        await self.session.commit()
    except IntegrityError as exc:
        await self.session.rollback()
        raise DuplicateEmailError() from exc
    return UserRead.model_validate(user)

async def deactivate_admin(self, admin_id: UUID) -> UserRead:
    """관리자 계정 비활성화 — 시드 관리자는 보호(FR21)."""
    user = await self.repo.get_by_id(admin_id)
    if user is None:
        raise UserNotFoundError()
    if user.user_role != UserRole.ADMIN:
        raise ForbiddenError()
    if user.is_seed:
        raise SeedAdminDeactivationError()
    user.is_active = False
    await self.repo.save(user)
    await self.session.commit()
    return UserRead.model_validate(user)
```

#### 4. `apps/api/app/routers/admin.py` — 관리자 엔드포인트 3개 추가

기존 `import` 섹션에 추가:
```python
from app.schemas.auth import AdminCreateRequest, UserRead  # AdminCreateRequest 추가
```

라우터 하단에 엔드포인트 3개 추가:
```python
@router.get("/admins", response_model=Page[UserRead])
async def list_admins(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> Page[UserRead]:
    return await AdminUserService(db).list_admins(cursor, limit)


@router.post("/admins", response_model=UserRead, status_code=201)
async def create_admin(
    data: AdminCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    return await AdminUserService(db).create_admin(data)


@router.post("/admins/{admin_id}/deactivate", response_model=UserRead)
async def deactivate_admin(
    admin_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    return await AdminUserService(db).deactivate_admin(admin_id)
```

#### 5. openapi.json 재생성 (백엔드 구현 완료 후)

`apps/api` 디렉토리에서 실행:
```bash
uv run python -c "
from app.main import app
import json, sys
sys.stdout.write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
" > ../../openapi.json
```

확인: `openapi.json`에 `/api/v1/admin/admins` 경로 3개 + `UserRead`에 `isSeed` 포함 여부 확인.

#### 6. pnpm orval — API 클라이언트 재생성

프로젝트 루트에서:
```bash
pnpm orval
```

생성/변경 결과 확인:
- `packages/api-client/src/generated/admin/admin.ts` — 신규 훅 3개 추가:
  - `useListAdmins({ cursor?, limit? })` → useQuery → `Page<UserRead>`
  - `useCreateAdmin()` → useMutation → `UserRead`
  - `useDeactivateAdmin()` → useMutation → `UserRead`
- `packages/api-client/src/generated/model/userRead.ts` — `isSeed: boolean` 추가 (자동)

⚠️ Orval 훅명은 operationId에서 추출. 생성된 파일에서 export 이름 확인 후 import.

### 프론트엔드 구현 상세

#### 7. `apps/admin-web/src/app/(admin)/admins/page.tsx` — 신규 생성

**페이지 구조:**
```
/admins 페이지
├─ 헤더: "관리자 계정 관리" 제목
├─ AddAdminForm (Card): 신규 관리자 추가 폼
│  ├─ Input: 이메일
│  ├─ Input: 비밀번호 (type="password")
│  ├─ Input: 표시명
│  └─ Button: "관리자 추가"
│     └─ onSuccess: 목록 무효화 + 폼 초기화
└─ AdminTable
   ├─ Table: 이름 | 이메일 | 상태 | 가입일 | 액션
   ├─ StatusBadge: 활성(default) / 비활성(secondary)
   ├─ [시드 관리자] 액션: "비활성화 불가" (disabled Button)
   ├─ [활성 비시드] 액션: AlertDialog 확인 → useDeactivateAdmin
   └─ LoadMore: nextCursor 있을 때 "더 보기" 버튼
```

**구현 패턴 (훅명은 생성 후 확인):**
```tsx
"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
// 아래 훅명은 pnpm orval 후 실제 생성 파일(packages/api-client/src/generated/admin/admin.ts)에서 확인
import {
  useListAdmins,
  useCreateAdmin,
  useDeactivateAdmin,
  type UserRead,
} from "@gosoom/api-client";

export default function AdminsPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">관리자 계정 관리</h1>
      <AddAdminForm />
      <AdminTable />
    </main>
  );
}
```

**AddAdminForm — 신규 관리자 생성 폼:**
```tsx
function AddAdminForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // 훅명은 생성 파일 확인 후 조정 (예: useCreateAdmin)
  const createAdmin = useCreateAdmin({
    mutation: {
      onSuccess: () => {
        setEmail(""); setPassword(""); setDisplayName("");
        setFormError(null);
        // 관리자 목록 쿼리 무효화 — queryKey는 생성 파일에서 확인
        queryClient.invalidateQueries({ queryKey: ["/api/v1/admin/admins"] });
      },
      onError: (error: unknown) => {
        setFormError(error instanceof Error ? error.message : "관리자 추가 중 오류가 발생했습니다.");
      },
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    createAdmin.mutate({ data: { email, password, displayName } });
  };

  return (
    <Card className="mb-8">
      <CardHeader>
        <CardTitle>신규 관리자 추가</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex gap-3 flex-wrap items-end">
          <div className="grid gap-1.5">
            <Label htmlFor="admin-email">이메일</Label>
            <Input id="admin-email" type="email" value={email}
              onChange={(e) => setEmail(e.target.value)} required placeholder="admin@example.com" />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="admin-password">비밀번호</Label>
            <Input id="admin-password" type="password" value={password}
              onChange={(e) => setPassword(e.target.value)} required minLength={8} />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="admin-displayName">표시명</Label>
            <Input id="admin-displayName" type="text" value={displayName}
              onChange={(e) => setDisplayName(e.target.value)} required />
          </div>
          <Button type="submit" disabled={createAdmin.isPending}>
            {createAdmin.isPending ? "추가 중..." : "관리자 추가"}
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
```

**AdminTable — 관리자 목록 + 비활성화:**
```tsx
function AdminTable() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<UserRead[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useListAdmins({ limit: 20, cursor });

  // 데이터 누적 로직 (Story 6.2 UserTable과 동일 패턴)
  useEffect(() => {
    if (!data?.items) return;
    if (!cursor) {
      setAllItems(data.items);
    } else {
      setAllItems((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        const newItems = data.items.filter((i) => !existingIds.has(i.id));
        return [...prev, ...newItems];
      });
    }
  }, [data]);

  const invalidateList = () => {
    setActionError(null);
    queryClient.invalidateQueries({ queryKey: ["/api/v1/admin/admins"] });
    setCursor(undefined);
    setAllItems([]);
  };

  // 훅명은 생성 파일 확인 후 조정
  const deactivate = useDeactivateAdmin({
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
        {Array.from({ length: 3 }).map((_, i) => (
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
            <TableHead>이름</TableHead>
            <TableHead>이메일</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>가입일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                관리자 계정이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((admin) => (
              <TableRow key={admin.id}>
                <TableCell className="font-medium">
                  {admin.displayName}
                  {admin.isSeed && (
                    <Badge variant="outline" className="ml-2 text-xs">시드</Badge>
                  )}
                </TableCell>
                <TableCell>{admin.email}</TableCell>
                <TableCell>
                  <Badge variant={admin.isActive ? "default" : "secondary"}>
                    {admin.isActive ? "활성" : "비활성"}
                  </Badge>
                </TableCell>
                <TableCell>{formatDate(admin.createdAt)}</TableCell>
                <TableCell>
                  {admin.isSeed ? (
                    <Button variant="outline" size="sm" disabled title="시드 관리자는 비활성화할 수 없습니다">
                      비활성화 불가
                    </Button>
                  ) : admin.isActive ? (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="outline" size="sm">비활성화</Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>관리자를 비활성화하시겠습니까?</AlertDialogTitle>
                          <AlertDialogDescription>
                            비활성화하면 {admin.displayName} 관리자가 즉시 콘솔에서 로그아웃되고
                            재로그인이 불가능합니다.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>취소</AlertDialogCancel>
                          <AlertDialogAction onClick={() => deactivate.mutate({ adminId: admin.id })}>
                            비활성화
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  ) : (
                    <span className="text-sm text-muted-foreground">비활성</span>
                  )}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {data?.nextCursor && (
        <div className="mt-4 flex justify-center">
          <Button variant="outline" onClick={() => setCursor(data.nextCursor ?? undefined)}
            disabled={isFetching}>
            {isFetching ? "불러오는 중..." : "더 보기"}
          </Button>
        </div>
      )}
    </div>
  );
}
```

⚠️ **주의사항:**
- `useListAdmins`의 queryKey는 생성된 `getListAdminsQueryKey` 헬퍼 함수 확인 후 `invalidateQueries`에 사용. 없으면 `["/api/v1/admin/admins"]` 문자열 배열로 대체.
- `useDeactivateAdmin`의 mutation 파라미터명(`adminId`)은 생성 파일 확인 필수.
- `admin.isSeed` 필드는 `pnpm orval` 후 `UserRead` 타입에 자동 추가됨.

### 기존 코드 패턴 참조

| 패턴 | 참조 파일 |
|------|----------|
| Cursor 페이지네이션 service | `apps/api/app/services/admin.py:list_users` |
| 관리자 생성(hash_password + create) | `apps/api/app/services/auth.py:signup` 패턴 참조 |
| ForbiddenError / UserNotFoundError | `apps/api/app/core/exceptions.py` |
| 라우터 엔드포인트 구조 | `apps/api/app/routers/admin.py` 기존 패턴 |
| `useListAdminUsers` + cursor 누적 | `apps/admin-web/src/app/(admin)/users/page.tsx` |
| AlertDialog 비활성화 버튼 | `apps/admin-web/src/app/(admin)/users/page.tsx` |
| AddAdminForm (Card + Input + Label) | `apps/admin-web/src/app/(auth)/login/page.tsx` (Input/Label 패턴) |
| queryClient.invalidateQueries | `apps/admin-web/src/app/(admin)/users/page.tsx:invalidateList` |

### Story 6.2 주요 학습사항 (적용 필수)

- **Orval 훅명:** 실제 생성 파일(`packages/api-client/src/generated/admin/admin.ts`)에서 export 이름 반드시 확인. 예상과 다를 수 있음.
- **queryKey 확인:** `getListAdminUsersQueryKey` 패턴처럼 Orval이 `getList*QueryKey` 헬퍼를 생성한다. 생성된 헬퍼 사용 권장.
- **pnpm shadcn CLI Windows baseUrl 이슈:** shadcn 추가 필요 시 user-web에서 직접 파일 복사. 이 스토리에서는 기존 컴포넌트 재사용이라 해당 없음.
- **TypeScript 타입체크 방법:** `pnpm --filter admin-web typecheck` 대신 `node_modules/.bin/tsc --noEmit -p apps/admin-web/tsconfig.json` 사용 가능.
- **useReadMe 옵션 이슈:** Orval의 queryKey required 이슈로 `useReadMe()` 옵션 없이 호출. 신규 훅도 동일 이슈 발생 시 동일 해법 적용.
- **SeedAdminDeactivationError(409):** 프론트엔드에서 `isSeed` 확인으로 버튼을 비활성화하지만, 서버 측 검증도 필수 (클라이언트 우회 방지).

### 6.2 deferred 항목 중 6.3 연관 사항

- **commit 후 model_validate async 위험 (deferred):** `services/admin.py`의 `deactivate_admin`/`create_admin`도 동일 패턴(`flush → commit → model_validate`). 6.2와 동일하게 프로젝트 기존 패턴 의존으로 처리.

## 파일 구조 (이 스토리에서 생성/수정)

```
apps/api/app/
├─ schemas/auth.py               ← MODIFY: UserRead에 is_seed 필드 추가 + AdminCreateRequest 추가
├─ core/exceptions.py            ← MODIFY: SeedAdminDeactivationError 추가
├─ services/admin.py             ← MODIFY: list_admins/create_admin/deactivate_admin 메서드 추가
└─ routers/admin.py              ← MODIFY: GET/POST /admins, POST /admins/{id}/deactivate 추가

openapi.json                     ← REGENERATE: is_seed 포함된 UserRead + 신규 admin 경로 3개

packages/api-client/src/
└─ generated/
   ├─ admin/admin.ts             ← AUTO-UPDATED: pnpm orval 후 신규 훅 추가
   └─ model/userRead.ts         ← AUTO-UPDATED: isSeed 필드 추가

apps/admin-web/src/
└─ app/(admin)/admins/
   └─ page.tsx                   ← CREATE: 관리자 계정 관리 화면
```

## Tasks / Subtasks

- [x] Task 1 — 백엔드: UserRead 스키마 수정 + AdminCreateRequest 추가 (AC1, AC2)
  - [x] 1.1: `apps/api/app/schemas/auth.py`의 `UserRead`에 `is_seed: bool` 필드 추가
  - [x] 1.2: `apps/api/app/schemas/auth.py` 하단에 `AdminCreateRequest` 클래스 추가 (email, password, display_name)

- [x] Task 2 — 백엔드: 예외 추가 (AC3)
  - [x] 2.1: `apps/api/app/core/exceptions.py`에 `SeedAdminDeactivationError` 추가 (code="seed_admin_deactivation_forbidden", message="시드 관리자는 비활성화할 수 없습니다.", status_code=409)

- [x] Task 3 — 백엔드: admin service에 관리자 관리 메서드 추가 (AC1, AC2, AC3)
  - [x] 3.1: `apps/api/app/services/admin.py`의 imports에 `hash_password`, `AdminCreateRequest`, `SeedAdminDeactivationError`, `DuplicateEmailError` 추가
  - [x] 3.2: `AdminUserService`에 `list_admins(cursor, limit)` 메서드 추가 — `list_by_role(ADMIN, after_id, limit+1)` 호출
  - [x] 3.3: `AdminUserService`에 `create_admin(data: AdminCreateRequest)` 메서드 추가 — 중복 이메일 체크 → hash_password → User(role=ADMIN) 생성 → commit
  - [x] 3.4: `AdminUserService`에 `deactivate_admin(admin_id)` 메서드 추가 — ADMIN role 확인, is_seed 체크 → ForbiddenError/SeedAdminDeactivationError, is_active=False, save, commit

- [x] Task 4 — 백엔드: admin 라우터에 엔드포인트 3개 추가 (AC1, AC2, AC3)
  - [x] 4.1: `apps/api/app/routers/admin.py`에 `AdminCreateRequest` import 추가
  - [x] 4.2: `GET /admins` 엔드포인트 추가 (`list_admins`) — cursor, limit 쿼리 파라미터
  - [x] 4.3: `POST /admins` 엔드포인트 추가 (`create_admin`) — status_code=201, AdminCreateRequest body
  - [x] 4.4: `POST /admins/{admin_id}/deactivate` 엔드포인트 추가 (`deactivate_admin`)

- [x] Task 5 — openapi.json 재생성 및 api-client 갱신 (AC1, AC2, AC3)
  - [x] 5.1: `apps/api` 디렉토리에서 uv run python으로 openapi.json 재생성
  - [x] 5.2: openapi.json의 `UserRead` 컴포넌트에 `isSeed` 포함 확인
  - [x] 5.3: openapi.json에 `/api/v1/admin/admins` 경로 3개 포함 확인
  - [x] 5.4: 프로젝트 루트에서 `pnpm orval` 실행
  - [x] 5.5: `packages/api-client/src/generated/admin/admin.ts`에 신규 훅 추가 확인 (list, create, deactivate)
  - [x] 5.6: `packages/api-client/src/generated/model/userRead.ts`에 `isSeed: boolean` 포함 확인

- [x] Task 6 — admin-web: 관리자 계정 관리 페이지 구현 (AC4)
  - [x] 6.1: `apps/admin-web/src/app/(admin)/admins/page.tsx` 신규 생성 — "use client" 선언
  - [x] 6.2: `AddAdminForm` 컴포넌트 구현 — email/password/displayName Input + 추가 버튼 + `useCreateAdmin` mutation
  - [x] 6.3: `AdminTable` 컴포넌트 구현 — `useListAdmins` 훅으로 목록 조회
  - [x] 6.4: 테이블 열 구성: 이름(시드 배지 포함) / 이메일 / 상태 배지 / 가입일 / 액션
  - [x] 6.5: 시드 관리자(`isSeed=true`) 행에 비활성화 불가 버튼(disabled) 표시 (AC4)
  - [x] 6.6: 활성 비시드 관리자 행에 AlertDialog + 비활성화 버튼 — `useDeactivateAdmin` mutation 연결 (AC4)
  - [x] 6.7: 비활성 관리자 행에 "비활성" 텍스트만 표시 (재활성화 기능은 미구현 — 스코프 외)
  - [x] 6.8: mutation onSuccess에서 `queryClient.invalidateQueries` + 상태 초기화로 목록 자동 갱신
  - [x] 6.9: cursor 기반 "더 보기" 버튼 — `data.nextCursor` 있을 때 표시
  - [x] 6.10: 폼 에러/액션 에러 인라인 배너 표시 (AR12 준수)

- [x] Task 7 — 타입체크 및 동작 확인 (AC1~AC4)
  - [x] 7.1: `uv run ruff check app/` → All checks passed
  - [x] 7.2: `tsc --noEmit -p apps/admin-web/tsconfig.json` → 오류 없음

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

없음

### Completion Notes List

- UserRead 스키마에 `is_seed: bool` 추가 — 하위 호환(기존 클라이언트는 미사용 필드 무시)
- AdminCreateRequest 신규 스키마 추가 — role 고정(ADMIN), /signup 경로 차단
- SeedAdminDeactivationError(409) 예외 추가 — 시드 관리자 잠금 방지
- AdminUserService에 list_admins/create_admin/deactivate_admin 메서드 추가
  - list_admins: list_by_role(ADMIN) 재사용, cursor 페이지네이션
  - create_admin: hash_password + IntegrityError 이중 보호
  - deactivate_admin: role 확인 → is_seed 확인 → is_active=False
- GET/POST /admins, POST /admins/{id}/deactivate 엔드포인트 3개 추가
- openapi.json 재생성(UTF-8 강제 지정), pnpm orval 실행
  - useListAdmins, useCreateAdmin, useDeactivateAdmin 훅 생성 확인
  - userRead.ts에 isSeed: boolean 자동 추가 확인
- admin-web /admins 페이지 구현
  - AddAdminForm: email/password/displayName 입력 + createAdmin mutation
  - AdminTable: 목록 조회 + cursor "더 보기" + 시드 비활성화 불가(disabled) + AlertDialog 확인
  - getListAdminsQueryKey 헬퍼로 invalidateQueries 처리
- ruff check: All checks passed
- tsc --noEmit: 오류 없음

### File List

apps/api/app/schemas/auth.py (수정: UserRead에 is_seed 추가, AdminCreateRequest 신규)
apps/api/app/core/exceptions.py (수정: SeedAdminDeactivationError 추가)
apps/api/app/services/admin.py (수정: list_admins/create_admin/deactivate_admin 추가)
apps/api/app/routers/admin.py (수정: GET/POST /admins, POST /admins/{id}/deactivate 추가)
openapi.json (재생성)
packages/api-client/src/generated/admin/admin.ts (자동 갱신: useListAdmins/useCreateAdmin/useDeactivateAdmin)
packages/api-client/src/generated/model/userRead.ts (자동 갱신: isSeed: boolean 추가)
packages/api-client/src/generated/model/adminCreateRequest.ts (자동 생성)
packages/api-client/src/generated/model/listAdminsParams.ts (자동 생성)
apps/admin-web/src/app/(admin)/admins/page.tsx (신규 생성)

### Review Findings

- [x] [Review][Decision→Dismiss] 자기 자신 비활성화 — UI에서 자기 행에도 동일하게 비활성화 버튼이 노출되나, 허용으로 결정. 잠금 시 시드 관리자로 복구 가능.
- [x] [Review][Decision→Dismiss] 이미 비활성화된 관리자 재비활성화 — UI에서 비활성 행에는 버튼 자체 없음. API 직접 호출 시 멱등 200은 표준 REST 동작. dismiss.
- [x] [Review][Patch] `AdminCreateRequest` 비밀번호 복잡도 validator 추가 — 대문자+소문자+숫자+특수문자 각 1개 이상 필수 (시드 계정은 seed 스크립트 경유라 자동 제외) [apps/api/app/schemas/auth.py]
- [x] [Review][Patch] 서비스 레이어에서 `limit=0` 직접 호출 시 IndexError 가능 — `assert limit >= 1` 추가 [apps/api/app/services/admin.py]
- [x] [Review][Patch] `GET /api/v1/admin/users` `role` 파라미터 description에 admin 불허 명시 [apps/api/app/routers/admin.py]
- [x] [Review][Defer] commit 실패 시 rollback 누락 (`deactivate_admin`/`deactivate_user`/`activate_user`) [apps/api/app/services/admin.py:77,89,142] — deferred, pre-existing
- [x] [Review][Defer] 유효 형식이나 존재하지 않는 UUID cursor 입력 시 빈 결과 반환 (에러 없음) [apps/api/app/services/admin.py:98-111] — deferred, pre-existing
- [x] [Review][Defer] `list_admins`/`list_users` cursor 페이지네이션 로직 완전 중복 (DRY 위반) [apps/api/app/services/admin.py:36-58,92-111] — deferred, pre-existing

## Change Log

- 2026-06-11: Story 6.3 스토리 파일 생성
- 2026-06-11: Story 6.3 구현 완료 — 백엔드(schemas/exceptions/service/router) + openapi.json 재생성 + pnpm orval + admin-web /admins 페이지 구현. 타입체크/린트 통과.
