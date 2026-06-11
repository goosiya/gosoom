---
baseline_commit: "0dbf1b6"
---

# Story 6.4: 서비스 요청 관리

Status: done

## Story

As a 관리자,
I want 전체 서비스 요청 목록·상세·상태를 조회하고 상태를 변경하거나 부적절한 요청을 숨김 처리하기를,
So that 플랫폼의 거래를 점검하고 운영할 수 있다.

## Acceptance Criteria

1. **AC1 — 목록 조회 (include_hidden 옵션):** 관리자가 `GET /api/v1/admin/service-requests`를 호출하면 서비스 요청이 `{items, nextCursor}` cursor 페이지네이션으로 반환된다. `include_hidden=false`(기본)일 때는 `deleted_at IS NULL` 요청만, `include_hidden=true`일 때는 숨김 포함 전체가 반환된다 (FR22).

2. **AC2 — 상태 변경:** 관리자가 `POST /api/v1/admin/service-requests/{id}/change-status`로 상태를 변경하면 서비스 계층의 전이 규칙 하에 상태가 변경된다. 허용 전이: `cancel`(OPEN→CANCELLED, MATCHED→CANCELLED), `complete`(MATCHED→COMPLETED). 그 외 시도는 409 반환 (NFR7).

3. **AC3 — 숨김 처리:** 관리자가 `POST /api/v1/admin/service-requests/{id}/hide`를 호출하면 `deleted_at`이 현재 시각으로 설정된다(소프트 삭제). 이미 숨김 처리된 요청은 멱등 200 반환. 상태(status)는 변경되지 않으며, 연결된 견적·채팅방·메시지는 물리적으로 삭제되지 않는다 (FR22, NFR7).

4. **AC4 — 관리 UI:** admin-web의 `/requests` 화면에서 서비스 요청 목록이 표시된다. 상태 변경·숨김 액션이 제공되며, "숨김 포함" 토글로 숨김 요청 포함 여부를 전환할 수 있고, 기본 조회에서 숨김 요청은 제외된다.

## Dev Notes

### 아키텍처 핵심 제약 (위반 시 재작업)

- **패턴 A 엄수:** admin-web은 `@gosoom/api-client`만 통해 `/api/v1`에 접근. Supabase·DB 직접 접속 절대 금지 (AR8).
- **권한 최종 시행은 서버:** AdminGuard는 UX 보조. 실제 권한 검사는 FastAPI `require_role('admin')` (AR17).
- **소프트 삭제만 허용:** `deleted_at` 타임스탬프 설정. 물리 삭제/status 강제 변경 없이 별도 필드로 관리 (R3, NFR7).
- **service 계층이 비즈니스 로직 소유:** 라우터는 HTTP 변환만. 상태 전이 규칙·숨김 처리는 service에서 시행 (NFR4).
- **Orval 생성물 수동 수정 금지:** `packages/api-client/src/generated/` 파일 편집하지 말 것 (AR9). 백엔드 변경 후 반드시 `pnpm orval` 재실행.
- **에러는 `error.message`로 노출:** 한국어 메시지는 백엔드 envelope `message` 필드 → api-client `ApiError.message` 변환 (AR12).

### 기존 인프라 활용 (새로 구현 금지)

**`ServiceRequestRepository` 기존 메서드 — 상태변경/숨김에 필요한 신규 메서드 추가 필요:**
```python
# apps/api/app/repositories/service_requests.py
# 기존 메서드들:
async def get_by_id(self, id) -> ServiceRequest | None:     # deleted_at IS NULL 필터
async def list_by_customer(self, ...) -> list[ServiceRequest]:  # 고객별 조회
async def save(self, obj) -> ServiceRequest:                # flush/refresh, commit은 service에서

# 추가 필요한 메서드들 (아래 상세 설명 참조):
# - list_all(): 전체 요청 (admin 전용, include_hidden 옵션)
# - get_by_id_any(): deleted_at 무관 조회 (admin 작업용)
```

**`ServiceRequestStatus` Enum 재사용:**
```python
# apps/api/app/models/service_request.py
from app.models.service_request import ServiceRequest, ServiceRequestStatus
# ServiceRequestStatus.OPEN, MATCHED, COMPLETED, CANCELLED
```

**기존 pagination 패턴 재사용 (Story 6.2/6.3와 동일):**
```python
from app.core.pagination import decode_cursor, encode_cursor
from app.schemas.pagination import Page
```

**`InvalidStatusTransitionError` 기존 예외 재사용:**
```python
# apps/api/app/core/exceptions.py:152-160
from app.core.exceptions import (
    InvalidCursorError,
    InvalidStatusTransitionError,  # 재사용
    ServiceRequestNotFoundError,   # 재사용
)
```

**재사용할 admin-web 컴포넌트 (신규 설치 금지):**
```ts
// Story 6.2~6.3에서 이미 존재하는 컴포넌트들
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertDialog, AlertDialogAction, AlertDialogCancel,
  AlertDialogContent, AlertDialogDescription, AlertDialogFooter,
  AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
```

**AdminHeader.tsx에 이미 `/requests` 네비 링크 존재:**
```ts
// apps/admin-web/src/components/AdminHeader.tsx
const NAV_LINKS = [
  { href: "/users", label: "계정관리" },
  { href: "/admins", label: "관리자관리" },
  { href: "/requests", label: "요청관리" },  // ← 이미 존재
  ...
];
```
→ 네비게이션 수정 불필요. `/requests` 페이지만 생성하면 된다.

### 구현 순서 (중요: 순차 실행)

1. 백엔드 구현 (repository → schema → service → router)
2. openapi.json 재생성
3. `pnpm orval` 실행 (api-client 훅 재생성)
4. admin-web 프론트엔드 구현

### 백엔드 구현 상세

#### 1. `apps/api/app/repositories/service_requests.py` — 메서드 2개 추가

```python
async def list_all(
    self,
    after_id: uuid.UUID | None,
    limit: int,
    include_hidden: bool = False,
) -> list[ServiceRequest]:
    """전체 서비스 요청 조회 (관리자 전용). include_hidden=True이면 deleted_at 필터 제거."""
    stmt = select(ServiceRequest)
    if not include_hidden:
        stmt = stmt.where(ServiceRequest.deleted_at.is_(None))
    if after_id is not None:
        stmt = stmt.where(ServiceRequest.id < after_id)
    stmt = stmt.order_by(ServiceRequest.id.desc()).limit(limit)
    return list((await self.session.execute(stmt)).scalars().all())

async def get_by_id_any(self, id: uuid.UUID) -> ServiceRequest | None:
    """id로 요청 조회. deleted_at 무관 (관리자 상태변경·숨김 처리용)."""
    result = await self.session.execute(
        select(ServiceRequest).where(ServiceRequest.id == id)
    )
    return result.scalar_one_or_none()
```

#### 2. `apps/api/app/schemas/service_request.py` — `ServiceRequestAdminRead` 추가

파일 하단에 추가:
```python
class ServiceRequestAdminRead(ServiceRequestRead):
    """관리자 전용 서비스 요청 응답 — deleted_at 포함 (Story 6.4)."""

    deleted_at: datetime | None = None
```

→ `ServiceRequestRead`를 상속하므로 기존 필드 중복 불필요. `datetime`은 상단 `from datetime import datetime` import 이미 있음.

#### 3. `apps/api/app/services/admin.py` — `AdminServiceRequestService` 클래스 추가

파일 하단에 새 클래스 추가 (기존 `AdminUserService` 클래스 아래):

```python
# 파일 상단 import에 추가
from app.models.service_request import ServiceRequest, ServiceRequestStatus
from app.repositories.service_requests import ServiceRequestRepository
from app.schemas.service_request import ServiceRequestAdminRead, ServiceRequestStatusUpdate
```

추가할 클래스:
```python
class AdminServiceRequestService:
    """서비스 요청 관리 (Story 6.4) — 소유권 검사 없는 관리자 전용 로직."""

    def __init__(self, session: AsyncSession) -> None:
        self.repo = ServiceRequestRepository(session)
        self.session = session

    async def list_requests(
        self,
        cursor: str | None,
        limit: int,
        include_hidden: bool = False,
    ) -> Page[ServiceRequestAdminRead]:
        """전체 서비스 요청 목록 조회 — cursor id DESC 페이지네이션."""
        assert limit >= 1, "limit must be >= 1"
        after_id: UUID | None = None
        if cursor:
            try:
                after_id = UUID(decode_cursor(cursor))
            except (ValueError, AttributeError) as exc:
                raise InvalidCursorError() from exc
        rows = await self.repo.list_all(after_id, limit + 1, include_hidden)
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = encode_cursor(str(page[-1].id)) if has_more else None
        return Page(
            items=[ServiceRequestAdminRead.model_validate(r) for r in page],
            next_cursor=next_cursor,
        )

    async def change_status(
        self,
        request_id: UUID,
        action: str,
    ) -> ServiceRequestAdminRead:
        """상태 전이 시행 (관리자 버전 — 소유권 검사 없음, MATCHED 취소 허용).

        허용: cancel(OPEN→CANCELLED, MATCHED→CANCELLED), complete(MATCHED→COMPLETED).
        그 외: 409 InvalidStatusTransitionError.
        """
        request = await self.repo.get_by_id_any(request_id)
        if request is None:
            raise ServiceRequestNotFoundError()

        if action == "cancel":
            if request.status not in (
                ServiceRequestStatus.OPEN,
                ServiceRequestStatus.MATCHED,
            ):
                raise InvalidStatusTransitionError()
            request.status = ServiceRequestStatus.CANCELLED
        elif action == "complete":
            if request.status != ServiceRequestStatus.MATCHED:
                raise InvalidStatusTransitionError()
            request.status = ServiceRequestStatus.COMPLETED
        else:
            raise InvalidStatusTransitionError()

        result = await self.repo.save(request)
        await self.session.commit()
        return ServiceRequestAdminRead.model_validate(result)

    async def hide_request(self, request_id: UUID) -> ServiceRequestAdminRead:
        """서비스 요청 숨김 처리 (deleted_at 설정). 이미 숨김 처리된 경우 멱등 200.

        status는 변경하지 않는다. 연결된 quotes·chat_rooms·messages는 보존.
        """
        from datetime import datetime, timezone

        request = await self.repo.get_by_id_any(request_id)
        if request is None:
            raise ServiceRequestNotFoundError()
        if request.deleted_at is None:
            request.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self.repo.save(request)
            await self.session.commit()
        return ServiceRequestAdminRead.model_validate(request)
```

**imports 추가 위치:** 파일 상단 기존 imports 블록에 편입. 중복 import 주의.

#### 4. `apps/api/app/routers/admin.py` — 엔드포인트 3개 추가

기존 import에 추가:
```python
from app.schemas.service_request import ServiceRequestAdminRead, ServiceRequestStatusUpdate
from app.services.admin import AdminServiceRequestService, AdminUserService
```

라우터 하단에 추가:
```python
@router.get("/service-requests", response_model=Page[ServiceRequestAdminRead])
async def list_admin_service_requests(
    cursor: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    include_hidden: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> Page[ServiceRequestAdminRead]:
    return await AdminServiceRequestService(db).list_requests(cursor, limit, include_hidden)


@router.post("/service-requests/{request_id}/change-status", response_model=ServiceRequestAdminRead)
async def admin_change_service_request_status(
    request_id: UUID,
    data: ServiceRequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> ServiceRequestAdminRead:
    return await AdminServiceRequestService(db).change_status(request_id, data.action)


@router.post("/service-requests/{request_id}/hide", response_model=ServiceRequestAdminRead)
async def admin_hide_service_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ServiceRequestAdminRead:
    return await AdminServiceRequestService(db).hide_request(request_id)
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

확인: `openapi.json`에 `/api/v1/admin/service-requests` 경로 3개 + `ServiceRequestAdminRead` 스키마 + `deletedAt` 필드 포함 여부.

#### 6. pnpm orval — API 클라이언트 재생성

프로젝트 루트에서:
```bash
pnpm orval
```

생성/변경 결과 확인:
- `packages/api-client/src/generated/admin/admin.ts` — 신규 훅 3개:
  - `useListAdminServiceRequests({ cursor?, limit?, includeHidden? })` → `Page<ServiceRequestAdminRead>`
  - `useAdminChangeServiceRequestStatus()` → mutation → `ServiceRequestAdminRead`
  - `useAdminHideServiceRequest()` → mutation → `ServiceRequestAdminRead`
- `packages/api-client/src/generated/model/serviceRequestAdminRead.ts` — 신규 생성
- `packages/api-client/src/generated/model/listAdminServiceRequestsParams.ts` — 신규 생성

⚠️ **Orval 훅명은 operationId에서 추출.** 생성된 파일에서 export 이름 확인 후 import.

### 프론트엔드 구현 상세

#### 7. `apps/admin-web/src/app/(admin)/requests/page.tsx` — 신규 생성

**페이지 구조:**
```
/requests 페이지
├─ 헤더: "서비스 요청 관리" 제목
├─ 툴바: "숨김 포함" Checkbox 토글 (include_hidden 파라미터 제어)
└─ RequestsTable
   ├─ Table: ID(앞 8자리) | 카테고리 | 지역 | 상태 | 숨김여부 | 생성일 | 액션
   ├─ 상태 Badge: OPEN(기본), MATCHED(outline), COMPLETED(secondary), CANCELLED(destructive)
   ├─ 숨김 여부: deletedAt != null이면 "숨김" Badge(secondary), null이면 "표시" Badge
   ├─ 액션 (상태별):
   │  ├─ OPEN: "취소" 버튼 (AlertDialog) → change-status cancel
   │  ├─ MATCHED: "완료" 버튼 + "취소" 버튼 (각 AlertDialog)
   │  ├─ COMPLETED/CANCELLED: "-" (상태 변경 불가)
   │  └─ 숨김 미처리 요청에만 "숨김" 버튼 (AlertDialog) → hide
   └─ LoadMore: nextCursor 있을 때 "더 보기" 버튼
```

**구현 패턴 (훅명은 생성 후 확인):**
```tsx
"use client";
import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader,
  AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
// 아래 훅명은 pnpm orval 후 packages/api-client/src/generated/admin/admin.ts에서 확인
import {
  useListAdminServiceRequests,
  useAdminChangeServiceRequestStatus,
  useAdminHideServiceRequest,
  getListAdminServiceRequestsQueryKey,  // 존재하면 사용, 없으면 문자열 배열 대체
  type ServiceRequestAdminRead,
} from "@gosoom/api-client";

export default function RequestsPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">서비스 요청 관리</h1>
      <RequestsTable />
    </main>
  );
}
```

**RequestsTable — include_hidden 토글 + 목록 + 액션:**
```tsx
function RequestsTable() {
  const [includeHidden, setIncludeHidden] = useState(false);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<ServiceRequestAdminRead[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // include_hidden 토글 시 전체 리셋
  const handleToggleHidden = (checked: boolean) => {
    setIncludeHidden(checked);
    setCursor(undefined);
    setAllItems([]);
  };

  const { data, isLoading, isFetching } = useListAdminServiceRequests({
    limit: 20,
    cursor,
    includeHidden,
  });

  // Story 6.2/6.3과 동일한 cursor 누적 패턴
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
  }, [data]);

  const invalidateList = () => {
    setActionError(null);
    queryClient.invalidateQueries({ queryKey: ["/api/v1/admin/service-requests"] });
    setCursor(undefined);
    setAllItems([]);
  };

  const changeStatus = useAdminChangeServiceRequestStatus({
    mutation: {
      onSuccess: invalidateList,
      onError: (error: unknown) => {
        setActionError(error instanceof Error ? error.message : "상태 변경 중 오류가 발생했습니다.");
      },
    },
  });

  const hideRequest = useAdminHideServiceRequest({
    mutation: {
      onSuccess: invalidateList,
      onError: (error: unknown) => {
        setActionError(error instanceof Error ? error.message : "숨김 처리 중 오류가 발생했습니다.");
      },
    },
  });

  const STATUS_LABEL: Record<string, string> = {
    open: "대기중",
    matched: "매칭됨",
    completed: "완료",
    cancelled: "취소됨",
  };

  const STATUS_VARIANT: Record<string, "default" | "outline" | "secondary" | "destructive"> = {
    open: "default",
    matched: "outline",
    completed: "secondary",
    cancelled: "destructive",
  };

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
      {/* include_hidden 토글 */}
      <div className="flex items-center gap-2 mb-4">
        <Checkbox
          id="include-hidden"
          checked={includeHidden}
          onCheckedChange={(checked) => handleToggleHidden(checked === true)}
        />
        <Label htmlFor="include-hidden" className="cursor-pointer">숨김 요청 포함</Label>
      </div>

      {actionError && (
        <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError}
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>요청 ID</TableHead>
            <TableHead>카테고리</TableHead>
            <TableHead>지역</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>숨김여부</TableHead>
            <TableHead>생성일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                서비스 요청이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((req) => (
              <TableRow key={req.id} className={req.deletedAt ? "opacity-50" : ""}>
                <TableCell className="font-mono text-xs">
                  {String(req.id).substring(0, 8)}
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {String(req.categoryId).substring(0, 8)}
                </TableCell>
                <TableCell>{req.region}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[req.status] ?? "default"}>
                    {STATUS_LABEL[req.status] ?? req.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={req.deletedAt ? "secondary" : "default"}>
                    {req.deletedAt ? "숨김" : "표시"}
                  </Badge>
                </TableCell>
                <TableCell>{formatDate(req.createdAt)}</TableCell>
                <TableCell>
                  <div className="flex gap-2 flex-wrap">
                    {/* 상태 변경 액션 — 상태별 조건부 표시 */}
                    {req.status === "open" && (
                      <StatusActionButton
                        label="취소"
                        description={`요청 ${String(req.id).substring(0, 8)}의 상태를 취소로 변경합니다.`}
                        onConfirm={() => changeStatus.mutate({ requestId: req.id, data: { action: "cancel" } })}
                        variant="outline"
                      />
                    )}
                    {req.status === "matched" && (
                      <>
                        <StatusActionButton
                          label="완료"
                          description={`요청 ${String(req.id).substring(0, 8)}을 완료 처리합니다.`}
                          onConfirm={() => changeStatus.mutate({ requestId: req.id, data: { action: "complete" } })}
                          variant="outline"
                        />
                        <StatusActionButton
                          label="취소"
                          description={`요청 ${String(req.id).substring(0, 8)}의 상태를 취소로 변경합니다.`}
                          onConfirm={() => changeStatus.mutate({ requestId: req.id, data: { action: "cancel" } })}
                          variant="outline"
                        />
                      </>
                    )}
                    {/* 숨김 처리 — 이미 숨김인 경우 버튼 미표시 */}
                    {!req.deletedAt && (
                      <StatusActionButton
                        label="숨김"
                        description={`요청 ${String(req.id).substring(0, 8)}을 숨김 처리합니다. 연결된 견적·채팅은 보존됩니다.`}
                        onConfirm={() => hideRequest.mutate({ requestId: req.id })}
                        variant="destructive"
                      />
                    )}
                    {req.status !== "open" && req.status !== "matched" && req.deletedAt && (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </div>
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

// AlertDialog 공통 버튼 컴포넌트
function StatusActionButton({
  label,
  description,
  onConfirm,
  variant = "outline",
}: {
  label: string;
  description: string;
  onConfirm: () => void;
  variant?: "outline" | "destructive";
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant={variant} size="sm">{label}</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>확인</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>취소</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>확인</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
```

⚠️ **주의사항:**
- `useAdminChangeServiceRequestStatus`의 mutation 파라미터명(`requestId`, `data`)은 생성 파일 확인 필수. Orval이 path parameter를 다르게 명명할 수 있음.
- `useAdminHideServiceRequest`도 동일하게 생성 파일 확인 후 정확한 파라미터 사용.
- `useListAdminServiceRequests`의 queryKey: `getListAdminServiceRequestsQueryKey` 헬퍼가 생성되면 사용, 없으면 `["/api/v1/admin/service-requests"]` 문자열 배열 대체.
- `req.categoryId`는 UUID이므로 이름 표시 불가. 카테고리 이름은 별도 API 없이 ID 앞 8자리로 표시 (이 스토리 스코프 밖).
- `Checkbox` 컴포넌트가 admin-web에 없다면 `shadcn/ui` 설치: admin-web 내에서 직접 복사 (Story 6.3의 shadcn Windows 이슈 동일 적용).

### 기존 코드 패턴 참조

| 패턴 | 참조 파일 |
|------|----------|
| Cursor 페이지네이션 service | `apps/api/app/services/admin.py:list_users` (36-59행) |
| include_hidden 없는 list_all 패턴 | `apps/api/app/repositories/service_requests.py:list_by_customer` (37-48행) |
| 상태 전이 로직 | `apps/api/app/services/service_request.py:change_status` (141-167행) |
| ServiceRequestNotFoundError | `apps/api/app/core/exceptions.py:141-149` |
| InvalidStatusTransitionError | `apps/api/app/core/exceptions.py:152-160` |
| cursor 누적 패턴 (useEffect) | `apps/admin-web/src/app/(admin)/users/page.tsx` |
| AlertDialog + invalidateList | `apps/admin-web/src/app/(admin)/admins/page.tsx` |
| `queryClient.invalidateQueries` | `apps/admin-web/src/app/(admin)/users/page.tsx:invalidateList` |

### Story 6.3 주요 학습사항 (적용 필수)

- **Orval 훅명:** 실제 생성 파일(`packages/api-client/src/generated/admin/admin.ts`)에서 export 이름 반드시 확인.
- **queryKey 확인:** `getList*QueryKey` 헬퍼 함수가 생성되면 사용. 없으면 `["/api/v1/admin/service-requests"]` 문자열 배열.
- **TypeScript 타입체크:** `node_modules/.bin/tsc --noEmit -p apps/admin-web/tsconfig.json`
- **`useListAdminServiceRequests` 옵션 문제:** Orval queryKey required 이슈 발생 시 옵션 없이 파라미터만 전달.
- **`Checkbox` 컴포넌트:** admin-web에 미설치 시 `apps/user-web/src/components/ui/checkbox.tsx`에서 복사.
- **commit 후 model_validate:** `AdminServiceRequestService`의 `change_status`/`hide_request`도 기존 패턴 준수(flush → commit → model_validate).

## 파일 구조 (이 스토리에서 생성/수정)

```
apps/api/app/
├─ repositories/service_requests.py  ← MODIFY: list_all/get_by_id_any 메서드 추가
├─ schemas/service_request.py        ← MODIFY: ServiceRequestAdminRead 클래스 추가
├─ services/admin.py                 ← MODIFY: AdminServiceRequestService 클래스 추가
└─ routers/admin.py                  ← MODIFY: GET/POST /service-requests 엔드포인트 3개 추가

openapi.json                         ← REGENERATE: ServiceRequestAdminRead + /admin/service-requests 경로 3개

packages/api-client/src/
└─ generated/
   ├─ admin/admin.ts                 ← AUTO-UPDATED: 신규 훅 3개 추가
   ├─ model/serviceRequestAdminRead.ts ← AUTO-CREATED
   └─ model/listAdminServiceRequestsParams.ts ← AUTO-CREATED

apps/admin-web/src/
├─ app/(admin)/requests/
│  └─ page.tsx                       ← CREATE: 서비스 요청 관리 화면
└─ components/ui/checkbox.tsx        ← CREATE if missing (shadcn 복사)
```

## Tasks / Subtasks

- [x] Task 1 — 백엔드: Repository 메서드 추가 (AC1, AC2, AC3)
  - [x] 1.1: `apps/api/app/repositories/service_requests.py`에 `list_all(after_id, limit, include_hidden)` 메서드 추가
  - [x] 1.2: `apps/api/app/repositories/service_requests.py`에 `get_by_id_any(id)` 메서드 추가 (deleted_at 무관 조회)

- [x] Task 2 — 백엔드: Schema 추가 (AC1)
  - [x] 2.1: `apps/api/app/schemas/service_request.py` 하단에 `ServiceRequestAdminRead(ServiceRequestRead)` 추가 — `deleted_at: datetime | None = None` 필드 추가

- [x] Task 3 — 백엔드: AdminServiceRequestService 구현 (AC1, AC2, AC3)
  - [x] 3.1: `apps/api/app/services/admin.py` 상단 imports에 `ServiceRequestStatus`, `ServiceRequestRepository`, `ServiceRequestAdminRead` 추가
  - [x] 3.2: `AdminServiceRequestService` 클래스 추가 — `list_requests(cursor, limit, include_hidden)` 메서드 (cursor 페이지네이션, `list_all` 호출)
  - [x] 3.3: `change_status(request_id, action)` 메서드 추가 — `get_by_id_any` 호출, cancel(OPEN/MATCHED→CANCELLED), complete(MATCHED→COMPLETED), 그 외 409
  - [x] 3.4: `hide_request(request_id)` 메서드 추가 — `get_by_id_any` 호출, `deleted_at` 설정, 이미 숨김이면 멱등 200

- [x] Task 4 — 백엔드: 라우터 엔드포인트 추가 (AC1, AC2, AC3)
  - [x] 4.1: `apps/api/app/routers/admin.py`에 `ServiceRequestAdminRead`, `ServiceRequestStatusUpdate`, `AdminServiceRequestService` import 추가
  - [x] 4.2: `GET /service-requests` 엔드포인트 추가 — cursor, limit, include_hidden 쿼리 파라미터
  - [x] 4.3: `POST /service-requests/{request_id}/change-status` 엔드포인트 추가 — `ServiceRequestStatusUpdate` body
  - [x] 4.4: `POST /service-requests/{request_id}/hide` 엔드포인트 추가

- [x] Task 5 — openapi.json 재생성 및 api-client 갱신 (AC1, AC2, AC3)
  - [x] 5.1: `apps/api` 디렉토리에서 uv run python으로 openapi.json 재생성
  - [x] 5.2: openapi.json에 `ServiceRequestAdminRead` 스키마 + `deletedAt` 필드 포함 확인
  - [x] 5.3: openapi.json에 `/api/v1/admin/service-requests` 경로 3개 포함 확인
  - [x] 5.4: 프로젝트 루트에서 `pnpm orval` 실행
  - [x] 5.5: 생성된 `packages/api-client/src/generated/admin/admin.ts`에서 훅명 3개 확인 (list/change-status/hide)
  - [x] 5.6: `packages/api-client/src/generated/model/serviceRequestAdminRead.ts` 생성 확인

- [x] Task 6 — admin-web: 서비스 요청 관리 페이지 구현 (AC4)
  - [x] 6.1: `Checkbox` 컴포넌트 존재 확인 — 없어서 radix-ui 패턴으로 신규 생성 (`apps/admin-web/src/components/ui/checkbox.tsx`)
  - [x] 6.2: `apps/admin-web/src/app/(admin)/requests/page.tsx` 신규 생성 — `"use client"` 선언
  - [x] 6.3: `RequestsTable` 컴포넌트 구현 — `useListAdminServiceRequests` 훅 + cursor 누적 패턴
  - [x] 6.4: 테이블 열 구성: 요청ID | 카테고리 | 지역 | 상태 Badge | 숨김여부 Badge | 생성일 | 액션
  - [x] 6.5: "숨김 포함" Checkbox 토글 구현 — 토글 시 cursor/allItems 리셋 후 refetch
  - [x] 6.6: 상태별 액션 버튼 조건부 표시 — OPEN: 취소, MATCHED: 완료+취소, COMPLETED/CANCELLED: 없음
  - [x] 6.7: 숨김 미처리 요청에 "숨김" AlertDialog 버튼 표시 — `useAdminHideServiceRequest` mutation 연결
  - [x] 6.8: `StatusActionButton` 공통 AlertDialog 컴포넌트 추출 (코드 중복 제거)
  - [x] 6.9: mutation onSuccess에서 `queryClient.invalidateQueries` + 상태 초기화로 목록 자동 갱신
  - [x] 6.10: cursor 기반 "더 보기" 버튼 — `data.nextCursor` 있을 때 표시
  - [x] 6.11: 에러 인라인 배너 표시 (AR12 준수)

- [x] Task 7 — 타입체크 및 동작 확인 (AC1~AC4)
  - [x] 7.1: `uv run ruff check app/` → All checks passed
  - [x] 7.2: `node_modules/.bin/tsc --noEmit -p apps/admin-web/tsconfig.json` → 오류 없음

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- ruff F401: admin.py에서 `ServiceRequest`, `ServiceRequestStatusUpdate` 미사용 import 제거
- openapi.json Windows cp949 인코딩 이슈: stdout 대신 파일 직접 쓰기(`open(..., encoding='utf-8')`)로 해결
- Checkbox 컴포넌트 미존재: user-web에도 없어 `radix-ui` 통합 패키지 패턴으로 신규 생성
- Orval 파라미터 `include_hidden`은 snake_case 유지 (camelCase 변환 없음) — 프론트 코드에 `include_hidden` 적용

### Completion Notes List

- **백엔드 (AC1~AC3):**
  - `ServiceRequestRepository`에 `list_all(after_id, limit, include_hidden)` + `get_by_id_any(id)` 추가
  - `ServiceRequestAdminRead` 스키마: `ServiceRequestRead` 상속 + `deleted_at` 필드 추가
  - `AdminServiceRequestService` 구현: `list_requests`(cursor 페이지네이션), `change_status`(OPEN/MATCHED 취소·MATCHED 완료·그 외 409), `hide_request`(소프트삭제 멱등)
  - 라우터 엔드포인트 3개 추가: GET `/service-requests`, POST `/{id}/change-status`, POST `/{id}/hide`
- **API 클라이언트 (AC1~AC3):**
  - openapi.json 재생성: 3개 경로 + `ServiceRequestAdminRead` + `deletedAt` 확인
  - `pnpm orval` 실행: `useListAdminServiceRequests`, `useAdminChangeServiceRequestStatus`, `useAdminHideServiceRequest` 훅 생성
- **프론트엔드 (AC4):**
  - `Checkbox` 컴포넌트 신규 생성 (`radix-ui` 통합 패키지 패턴)
  - `/requests` 페이지: `include_hidden` 토글 + 테이블(ID·카테고리·지역·상태·숨김여부·생성일·액션)
  - 상태별 액션: OPEN→취소, MATCHED→완료+취소, 숨김 미처리→숨김 AlertDialog
  - mutation onSuccess: `queryClient.invalidateQueries` + cursor/allItems 초기화

### File List

- `apps/api/app/repositories/service_requests.py` — MODIFIED: `list_all`, `get_by_id_any` 메서드 추가
- `apps/api/app/schemas/service_request.py` — MODIFIED: `ServiceRequestAdminRead` 클래스 추가
- `apps/api/app/services/admin.py` — MODIFIED: imports 추가 + `AdminServiceRequestService` 클래스 추가
- `apps/api/app/routers/admin.py` — MODIFIED: imports 추가 + 엔드포인트 3개 추가
- `openapi.json` — REGENERATED: `ServiceRequestAdminRead` + 3개 경로 추가
- `packages/api-client/src/generated/admin/admin.ts` — AUTO-UPDATED: 훅 3개 추가
- `packages/api-client/src/generated/model/serviceRequestAdminRead.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/serviceRequestAdminReadBudget.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/serviceRequestAdminReadDeletedAt.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/serviceRequestAdminReadDesiredSchedule.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/listAdminServiceRequestsParams.ts` — AUTO-CREATED
- `packages/api-client/src/generated/model/index.ts` — AUTO-UPDATED
- `apps/admin-web/src/components/ui/checkbox.tsx` — CREATED: radix-ui 통합 패키지 패턴 Checkbox 컴포넌트
- `apps/admin-web/src/app/(admin)/requests/page.tsx` — CREATED: 서비스 요청 관리 페이지

### Review Findings

- [x] [Review][Decision] 숨겨진 요청(`deleted_at IS NOT NULL`)에 대한 상태 전이 허용 — KTH 결정: 허용 유지 (2026-06-12)
- [x] [Review][Patch] 액션 열 "-" placeholder 조건 버그 — 재검토 후 false positive: COMPLETED/CANCELLED + not-hidden 행에서 `!req.deletedAt` 조건으로 "숨김" 버튼이 올바르게 표시되므로 셀 공백 없음. 코드 정확함.
- [x] [Review][Patch] `hide_request` naive datetime 저장 [apps/api/app/services/admin.py] — 수정 완료: `datetime.now(timezone.utc).replace(tzinfo=None)` → `datetime.now(timezone.utc)`. `datetime`/`timezone` import를 함수 내 local import에서 파일 상단으로 이동.
- [x] [Review][Patch] `list_requests`의 `assert` → 명시적 ValueError [apps/api/app/services/admin.py] — 수정 완료: `assert limit >= 1` → `if limit < 1: raise ValueError("limit must be >= 1")`.
- [x] [Review][Patch] `getListAdminServiceRequestsQueryKey()` 파라미터 누락 — 재검토 후 false positive: 파라미터 없는 호출이 TanStack Query partial match로 모든 list 캐시를 무효화하는 의도적 설계. 뮤테이션 후 cursor 리셋 시 새 쿼리 캐시도 올바르게 무효화됨. 코드 정확함.
- [x] [Review][Defer] `change_status` TOCTOU 경쟁 조건 [apps/api/app/services/admin.py] — deferred, pre-existing: 두 관리자가 동시에 같은 요청 상태를 변경하면 마지막 commit이 이기는 last-write-wins 구조. `SELECT FOR UPDATE` 적용은 프로젝트 전반의 인프라 변경이 필요하므로 현 스코프 밖.
- [x] [Review][Defer] 서비스-리포지토리 이중 commit 패턴 [apps/api/app/services/admin.py] — deferred, pre-existing: 기존 `AdminUserService`와 동일한 패턴. 트랜잭션 경계 일원화는 리팩토링 이슈로 현 스코프 밖.

## Change Log

- 2026-06-12: Story 6.4 스토리 파일 생성
- 2026-06-12: Story 6.4 구현 완료 (백엔드 3개 엔드포인트 + api-client 재생성 + admin-web /requests 페이지)
- 2026-06-12: Story 6.4 코드 리뷰 완료 — 1 decision-needed, 4 patch, 2 defer, 7 dismiss
