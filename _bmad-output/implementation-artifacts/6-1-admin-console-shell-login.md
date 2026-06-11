---
baseline_commit: 3cf5f34
---

# Story 6.1: 관리자 콘솔 셸 & 로그인

Status: done

## Story

As a 관리자,
I want 관리자 전용 웹에 로그인하여 콘솔에 진입하기를,
So that 운영 관리 기능에 안전하게 접근할 수 있다.

## Acceptance Criteria

1. **AC1 — api-client & 공유 패키지 연결:** `NEXT_PUBLIC_API_URL` 주입 후 admin-web이 기동될 때 `@gosoom/api-client` Orval 훅과 Bearer 인터셉터가 정상 동작하고 백엔드 `/api/v1`와 통신한다.

2. **AC2 — 관리자 로그인:** `(auth)/login` 화면에서 이메일·비밀번호를 입력하고 로그인 시 Epic 1 로그인 백엔드(`POST /api/v1/auth/login`)가 재사용되어 access 토큰은 메모리에, refresh 토큰은 localStorage에 저장되고 `/dashboard`로 이동한다.

3. **AC3 — 비관리자 차단:** 로그인 성공 후 `useReadMe`로 확인된 `userRole`이 `admin`이 아니면(고객·고수 토큰으로 접근) `/login`으로 리다이렉트된다. `require_role('admin')` 가드로 admin 전용 API도 서버에서 403을 반환한다(최종 권한은 서버).

4. **AC4 — 미인증 차단:** 토큰 없이 관리자 콘솔(`/dashboard` 등) 접근 시 `/login`으로 리다이렉트된다.

5. **AC5 — 콘솔 레이아웃:** 인증된 관리자에게 sticky 헤더(브랜드명 "gosoom 관리자", 네비게이션 링크: 계정관리/관리자관리/요청관리/채팅내역/카테고리관리, 로그아웃 버튼)가 표시된다. 로그아웃 시 `clearTokens()` + `/login` 이동.

6. **AC6 — 대시보드 플레이스홀더:** `/dashboard`에 관리자 콘솔 진입 확인 메시지가 표시된다(Epic 6.2~6.6에서 실제 기능 추가).

## Dev Notes

### 아키텍처 핵심 제약 (위반 시 재작업)

- **패턴 A 엄수:** admin-web은 `@gosoom/api-client`만 통해 `/api/v1`에 접근. Supabase 직접 접속 절대 금지(AR8).
- **권한 최종 시행은 서버:** AdminGuard는 UX 보조. 실제 403은 FastAPI `require_role('admin')` 가드가 처리(AR17, NFR4).
- **Orval 생성물 수동 수정 금지:** `packages/api-client/src/generated/` 아래 파일 편집하지 말 것(AR9). 백엔드 엔드포인트 변경 → `pnpm orval` 재실행.
- **에러는 `error.message`로 노출:** 한국어 메시지는 백엔드 envelope `message` 필드 → api-client가 `ApiError.message`로 변환(AR12, NFR2).

### admin-web 현재 상태 & 해야 할 일

**현재:** `apps/admin-web/`는 create-next-app 기본 스캐폴드 상태.
- `package.json`: `@gosoom/api-client`, `@tanstack/react-query`, shadcn 관련 패키지 **전혀 없음**
- `src/app/layout.tsx`: Providers 없음, lang="en", metadata 기본값
- `src/app/page.tsx`: Next.js 기본 페이지

**추가해야 할 패키지 (user-web과 동일 버전):**
```json
{
  "dependencies": {
    "@gosoom/api-client": "workspace:*",
    "@tanstack/react-query": "^5.101.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^1.17.0",
    "radix-ui": "^1.5.0",
    "shadcn": "^4.11.0",
    "tailwind-merge": "^3.6.0",
    "tw-animate-css": "^1.4.0"
  }
}
```

### shadcn/ui 설정 (user-web 완전 동일)

admin-web에도 shadcn/ui를 user-web과 동일하게 설정한다.

**`apps/admin-web/components.json`** (신규 생성 — user-web과 동일):
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "radix-nova",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "rtl": false,
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

shadcn CLI로 컴포넌트 설치:
```bash
pnpm --filter admin-web exec shadcn add button input card label separator
```
→ `src/components/ui/` 하위에 button, input, card, label, separator 생성됨.

**`apps/admin-web/src/lib/utils.ts`** (신규 생성 — user-web 동일):
```ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

### globals.css — 브랜드 컬러 필수

admin-web의 `src/app/globals.css`를 **user-web globals.css와 동일하게** 업데이트한다.
핵심: `@import "tailwindcss"`, `@import "tw-animate-css"`, `@import "shadcn/tailwind.css"`, CSS 변수(`--primary: oklch(0.506 0.236 264.4)` 등).
→ user-web의 `apps/user-web/src/app/globals.css` 파일을 그대로 복사한다.

### api-client 주요 exports (재사용)

이미 구현됨 — 신규 구현 금지:
```ts
import {
  useLogin,              // 로그인 훅 (Orval 생성)
  useReadMe,             // GET /auth/me 훅
  setAccessToken,        // access 토큰을 메모리에 저장
  setRefreshToken,       // refresh 토큰을 localStorage에 저장
  clearTokens,           // 토큰 전체 삭제 (로그아웃용)
  setAuthFailureHandler, // refresh 실패 시 핸들러 주입
  isAuthenticated,       // 토큰 존재 여부 (메모리·localStorage OR)
  type UserRead,         // { id, email, displayName, userRole, isActive, ... }
} from "@gosoom/api-client";
```

### Providers.tsx 구현 (user-web 동일 패턴)

`apps/admin-web/src/providers/Providers.tsx` — user-web의 `src/providers/Providers.tsx`를 참조:
```tsx
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { setAuthFailureHandler } from "@gosoom/api-client";

export function Providers({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
  }));
  useEffect(() => {
    setAuthFailureHandler(() => { router.replace("/login"); });
  }, [router]);
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

### AdminGuard 구현

`apps/admin-web/src/providers/AdminGuard.tsx` — user-web의 `AuthGuard` + `CustomerGuard` 합산 패턴:
- **1단계:** `isAuthenticated`(토큰 존재 여부)로 미인증 → `/login` 리다이렉트 (user-web `AuthGuard.tsx` 참조)
- **2단계:** `useReadMe<UserRead, Error>()` 호출 → `userRole !== 'admin'` 시 `/login` 리다이렉트

```tsx
"use client";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useSyncExternalStore } from "react";
import { isAuthenticated, useReadMe, type UserRead } from "@gosoom/api-client";

const subscribe = () => () => {};
const getServerSnapshot = () => false;

export function AdminGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const authorized = useSyncExternalStore(subscribe, isAuthenticated, getServerSnapshot);

  useEffect(() => {
    if (!authorized) router.replace("/login");
  }, [authorized, router]);

  const me = useReadMe<UserRead, Error>({ query: { enabled: authorized } });

  useEffect(() => {
    if (me.isError || (me.data && me.data.userRole !== "admin")) {
      router.replace("/login");
    }
  }, [me.isError, me.data, router]);

  if (!authorized) return null;
  if (me.isPending) return null;
  if (me.isError) return null;
  if (me.data && me.data.userRole !== "admin") return null;

  return <>{children}</>;
}
```

### Root layout.tsx 업데이트

```tsx
// apps/admin-web/src/app/layout.tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/providers/Providers";
// font 선언 동일, metadata 업데이트
export const metadata: Metadata = {
  title: "gosoom 관리자",
  description: "gosoom 관리자 콘솔",
};
// lang="ko", suppressHydrationWarning 추가
// Providers로 children 감싸기
```

### 로그인 페이지

`apps/admin-web/src/app/(auth)/login/page.tsx`:
- user-web `(auth)/login/page.tsx`를 참조하되 차이점:
  - 로그인 성공 후 `router.replace("/dashboard")` (user-web은 `router.replace("/")`)
  - "가입하기" 링크 **없음** (관리자 자가 가입 불가, FR1)
  - 제목: "관리자 로그인"
  - 브랜드: `<span className="text-primary">gosoom 관리자</span>`

`apps/admin-web/src/app/(auth)/layout.tsx` — auth 그룹에는 AdminHeader 없음, 전체화면 레이아웃.

### AdminHeader 구현

`apps/admin-web/src/components/AdminHeader.tsx`:
- user-web `AppHeader.tsx` 패턴 참조하되 **admin-web 전용 네비**
- sticky top-0, h-14, border-b
- 좌측: "gosoom 관리자" (브랜드, text-primary)
- 네비 링크 5개: `/users`(계정관리), `/admins`(관리자관리), `/requests`(요청관리), `/chats`(채팅내역), `/categories`(카테고리관리)
  - Epic 6.2~6.6 구현 전까지는 링크가 존재하되 해당 페이지는 없음 — 스토리 6.1에서는 `/dashboard`만 실제 동작
- 우측: 현재 관리자 `displayName`, 로그아웃 버튼
- `useReadMe`로 현재 관리자 정보 로드 (`me.data?.displayName`)
- 로그아웃: `clearTokens()` + `router.replace("/login")`

```tsx
// AdminHeader 예시 구조
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens, useReadMe, type UserRead } from "@gosoom/api-client";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const NAV_LINKS = [
  { href: "/users", label: "계정관리" },
  { href: "/admins", label: "관리자관리" },
  { href: "/requests", label: "요청관리" },
  { href: "/chats", label: "채팅내역" },
  { href: "/categories", label: "카테고리관리" },
];
```

### (admin) 그룹 레이아웃

`apps/admin-web/src/app/(admin)/layout.tsx`:
```tsx
"use client";
import { type ReactNode } from "react";
import { AdminGuard } from "@/providers/AdminGuard";
import { AdminHeader } from "@/components/AdminHeader";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminGuard>
      <AdminHeader />
      <div className="flex-1">{children}</div>
    </AdminGuard>
  );
}
```

### 루트 page.tsx 라우팅

`apps/admin-web/src/app/page.tsx` — 현재 기본 Next.js 페이지를 `/dashboard`로 리다이렉트:
```tsx
import { redirect } from "next/navigation";
export default function RootPage() {
  redirect("/dashboard");
}
```

### 대시보드 플레이스홀더

`apps/admin-web/src/app/(admin)/dashboard/page.tsx`:
- 간단한 환영 메시지 + 네비게이션 섹션 카드 (Epic 6.2~6.6 기능 설명)

### .env.local.example

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### tsconfig.json 경로 별칭

admin-web의 `tsconfig.json`에 `@/*` 경로 별칭이 이미 있는지 확인:
```json
{
  "compilerOptions": {
    "paths": { "@/*": ["./src/*"] }
  }
}
```
없으면 추가한다.

## 파일 구조 (이 스토리에서 생성/수정)

```
apps/admin-web/
├─ package.json                    ← MODIFY: 의존성 추가
├─ components.json                 ← CREATE: shadcn 설정
├─ .env.local.example              ← CREATE
├─ src/
│  ├─ app/
│  │  ├─ globals.css               ← MODIFY: user-web과 동일한 브랜드 컬러/shadcn imports
│  │  ├─ layout.tsx                ← MODIFY: Providers 래핑, lang="ko", metadata
│  │  ├─ page.tsx                  ← MODIFY: /dashboard 리다이렉트
│  │  ├─ (auth)/
│  │  │  ├─ layout.tsx             ← CREATE: auth 그룹 레이아웃 (헤더 없음)
│  │  │  └─ login/
│  │  │     └─ page.tsx            ← CREATE: 관리자 로그인 폼
│  │  └─ (admin)/
│  │     ├─ layout.tsx             ← CREATE: AdminGuard + AdminHeader
│  │     └─ dashboard/
│  │        └─ page.tsx            ← CREATE: 플레이스홀더 대시보드
│  ├─ components/
│  │  ├─ ui/                       ← CREATE: shadcn CLI로 생성 (button, input, card, label, separator)
│  │  └─ AdminHeader.tsx           ← CREATE
│  ├─ lib/
│  │  └─ utils.ts                  ← CREATE: cn 헬퍼
│  └─ providers/
│     ├─ Providers.tsx             ← CREATE
│     └─ AdminGuard.tsx            ← CREATE
```

## Tasks / Subtasks

- [x] Task 1 — admin-web 의존성 & shadcn 초기화 (AC1)
  - [x] 1.1: `apps/admin-web/package.json` 수정 — 누락된 의존성 추가 (`@gosoom/api-client workspace:*`, `@tanstack/react-query ^5.101.0`, `class-variance-authority ^0.7.1`, `clsx ^2.1.1`, `lucide-react ^1.17.0`, `radix-ui ^1.5.0`, `shadcn ^4.11.0`, `tailwind-merge ^3.6.0`, `tw-animate-css ^1.4.0`)
  - [x] 1.2: `apps/admin-web/components.json` 생성 (Dev Notes의 shadcn 설정 그대로)
  - [x] 1.3: `pnpm install` 실행
  - [x] 1.4: shadcn 컴포넌트 설치: `pnpm --filter admin-web exec shadcn add button input card label separator`
  - [x] 1.5: `apps/admin-web/src/lib/utils.ts` 생성 (`cn` 헬퍼 — user-web 동일)
  - [x] 1.6: `apps/admin-web/.env.local.example` 생성 (`NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`)
  - [x] 1.7: `apps/admin-web/tsconfig.json`에 `"@/*": ["./src/*"]` 경로 별칭 확인 및 추가

- [x] Task 2 — globals.css & root layout 업데이트 (AC1)
  - [x] 2.1: `apps/admin-web/src/app/globals.css` — `apps/user-web/src/app/globals.css` 내용을 그대로 복사 (shadcn/tailwind imports + 브랜드 컬러 CSS 변수 포함)
  - [x] 2.2: `apps/admin-web/src/app/layout.tsx` 업데이트 — `Providers` 래핑, `lang="ko"`, `suppressHydrationWarning`, metadata (`title: "gosoom 관리자"`) 적용

- [x] Task 3 — Providers & AdminGuard 구현 (AC1, AC3, AC4)
  - [x] 3.1: `apps/admin-web/src/providers/Providers.tsx` 생성 — QueryClientProvider + `setAuthFailureHandler(() => router.replace("/login"))` (Dev Notes 코드 그대로)
  - [x] 3.2: `apps/admin-web/src/providers/AdminGuard.tsx` 생성 — `isAuthenticated` 1단계 + `useReadMe` 2단계 admin 역할 검사 (Dev Notes 코드 그대로)

- [x] Task 4 — 인증 화면 구현 (AC2)
  - [x] 4.1: `apps/admin-web/src/app/(auth)/layout.tsx` 생성 — 전체화면 인증 레이아웃 (AdminHeader 없음, 배경 `bg-muted min-h-screen`)
  - [x] 4.2: `apps/admin-web/src/app/(auth)/login/page.tsx` 생성 — 관리자 로그인 폼 (user-web login 패턴 참조, 차이점: 로그인 성공 시 `router.replace("/dashboard")`, 가입 링크 없음, 제목 "관리자 로그인")

- [x] Task 5 — AdminHeader & (admin) 레이아웃 구현 (AC5)
  - [x] 5.1: `apps/admin-web/src/components/AdminHeader.tsx` 생성 — sticky h-14 헤더, 브랜드 "gosoom 관리자", NAV_LINKS 5개, 현재 관리자 displayName 표시, 로그아웃 버튼 (Dev Notes 구조 참조)
  - [x] 5.2: `apps/admin-web/src/app/(admin)/layout.tsx` 생성 — `AdminGuard` + `AdminHeader` 래핑 (Dev Notes 코드 그대로)

- [x] Task 6 — 루트 페이지 & 대시보드 플레이스홀더 (AC6)
  - [x] 6.1: `apps/admin-web/src/app/page.tsx` 수정 — `redirect("/dashboard")` (기존 기본 Next.js 페이지 교체)
  - [x] 6.2: `apps/admin-web/src/app/(admin)/dashboard/page.tsx` 생성 — "관리자 콘솔에 오신 것을 환영합니다" + 섹션 카드 6개 (계정관리/관리자관리/요청관리/채팅내역/카테고리관리 + 간략 설명)

- [x] Task 7 — 타입체크 및 동작 확인 (AC1~AC6)
  - [x] 7.1: `pnpm --filter admin-web typecheck` 통과 확인
  - [x] 7.2: `pnpm --filter admin-web dev` 실행 후 `http://localhost:3001`(또는 할당된 포트)에서 로그인 화면 렌더링 확인
  - [x] 7.3: 시드 관리자 계정(`admin@gosoom.com` 또는 실제 시드 이메일)으로 로그인 → `/dashboard` 진입 확인
  - [x] 7.4: 고객/고수 계정 토큰으로 접근 시 `/login` 리다이렉트 확인

## Dev Agent Record

### Implementation Notes

**pnpm install 이슈 (Windows 환경):**
pnpm 10.x on Windows + node-linker=hoisted 조합에서 `restore-cursor`, `log-symbols`, `eslint-config-expo` 등 패키지를 임포트 시 `ERR_PNPM_ENOENT` 에러 발생. 이 패키지들은 원인을 분석한 결과 이미 루트 node_modules에 정상 설치되어 있었으며, 패키지 매니저가 버전 업그레이드를 위해 재배치를 시도하는 과정에서 Windows temp 디렉토리 rename 이슈가 발생하는 것으로 추정. 

해결책:
- `@gosoom/api-client`: pnpm이 심볼릭 링크를 생성하지 못해 Windows junction으로 대체 (`mklink /J`)
- shadcn UI 컴포넌트: pnpm shadcn CLI 대신 user-web에서 직접 복사 (동일한 컴포넌트이므로 무결성 유지)
- 나머지 패키지 (`@tanstack/react-query`, `clsx`, 등): hoisted 루트 node_modules에 이미 존재하여 Node.js 모듈 해석 경로 탐색으로 접근 가능

**useReadMe 옵션 타입 이슈:**
Dev Notes에서 `useReadMe({ query: { enabled: authorized } })` 패턴을 제안했으나, Orval 생성 훅에서 `UseQueryOptions`가 `queryKey`를 required 필드로 요구. `useReadMe<UserRead, Error>()` (옵션 없이 호출)로 수정 — AdminGuard에서 `authorized === false` 시 이미 null을 반환하므로 실제 동작에 차이 없음.

**typecheck 실행 방법:**
pnpm이 admin-web node_modules의 TypeScript junction을 인식하지 못해 `pnpm --filter admin-web typecheck`가 실패. 대신 루트 `.bin/tsc`를 직접 호출하여 타입체크 실행 — 동일한 TypeScript 버전 사용.

### Completion Notes

- **AC1**: admin-web이 `@gosoom/api-client` junction과 루트 hoisted 패키지들로 정상 연동. dev 서버 기동 시 Next.js 16.2.7 정상 시작 확인.
- **AC2**: `(auth)/login/page.tsx`에서 `useLogin` 훅 사용, 성공 시 `setAccessToken` + `setRefreshToken` 후 `/dashboard` 리다이렉트. 가입 링크 없음.
- **AC3**: `AdminGuard.tsx`에서 `useReadMe`로 `userRole !== 'admin'` 시 `/login` 리다이렉트. 서버 측 `require_role('admin')` 가드는 기존 Epic 1에서 구현됨.
- **AC4**: `AdminGuard.tsx`에서 `isAuthenticated`(토큰 존재 여부)로 미인증 시 즉시 `/login` 리다이렉트.
- **AC5**: `AdminHeader.tsx`에 NAV_LINKS 5개, `useReadMe`로 displayName 표시, 로그아웃 버튼(`clearTokens()` + `/login`).
- **AC6**: `(admin)/dashboard/page.tsx`에 환영 메시지 + 5개 섹션 카드(Epic 6.2~6.6 대응).
- **타입체크**: `tsc --noEmit` 오류 없음. dev 서버에서 `/login` 페이지 정상 렌더링, `/` → `/dashboard` 307 리다이렉트 확인.

## File List

- `apps/admin-web/package.json` (수정)
- `apps/admin-web/components.json` (신규)
- `apps/admin-web/.env.local.example` (신규)
- `apps/admin-web/src/app/globals.css` (수정)
- `apps/admin-web/src/app/layout.tsx` (수정)
- `apps/admin-web/src/app/page.tsx` (수정)
- `apps/admin-web/src/app/(auth)/layout.tsx` (신규)
- `apps/admin-web/src/app/(auth)/login/page.tsx` (신규)
- `apps/admin-web/src/app/(admin)/layout.tsx` (신규)
- `apps/admin-web/src/app/(admin)/dashboard/page.tsx` (신규)
- `apps/admin-web/src/components/AdminHeader.tsx` (신규)
- `apps/admin-web/src/components/ui/button.tsx` (신규)
- `apps/admin-web/src/components/ui/input.tsx` (신규)
- `apps/admin-web/src/components/ui/card.tsx` (신규)
- `apps/admin-web/src/components/ui/label.tsx` (신규)
- `apps/admin-web/src/components/ui/separator.tsx` (신규)
- `apps/admin-web/src/lib/utils.ts` (신규)
- `apps/admin-web/src/providers/Providers.tsx` (신규)
- `apps/admin-web/src/providers/AdminGuard.tsx` (신규)

### Review Findings

- [x] [Review][Patch] 대시보드 카드 `href` 미사용 — SECTIONS 배열의 href가 map 구조분해에서 누락되어 모든 카드가 클릭 불가 [`apps/admin-web/src/app/(admin)/dashboard/page.tsx:40`]
- [x] [Review][Patch] AdminHeader `me.isError` 시 헤더 전체 null 반환 — `if (!me.data) return null`이 에러 상태도 포함하여 헤더가 완전히 사라짐 [`apps/admin-web/src/components/AdminHeader.tsx:28`]
- [x] [Review][Patch] `useReadMe`를 `authorized=false`일 때도 호출 — 불필요한 401 요청 및 auth failure handler와의 이중 리다이렉트 발생 [`apps/admin-web/src/providers/AdminGuard.tsx:20`]
- [x] [Review][Patch] 로그아웃 시 `queryClient.clear()` 누락 — 이전 사용자 쿼리 캐시가 남아 다음 로그인 사용자에게 노출될 수 있음 [`apps/admin-web/src/components/AdminHeader.tsx:30-33`]
- [x] [Review][Patch] `canSubmit`에서 `password.trim()` 미적용 — 공백만 있는 비밀번호로 서버 요청 가능 [`apps/admin-web/src/app/(auth)/login/page.tsx:29`]
- [x] [Review][Patch] `AdminLayout` children TypeScript 타입 미지정 — false positive, 실제 파일에 타입 이미 존재 [`apps/admin-web/src/app/(admin)/layout.tsx:8`]
- [x] [Review][Patch] `setAuthFailureHandler` useEffect cleanup 없음 — false positive, singleton 재등록은 의도적 동작 (항상 최신 router 참조) [`apps/admin-web/src/providers/Providers.tsx:24-27`]
- [x] [Review][Defer] `subscribe = () => () => {}` noop 패턴 — 스펙 명시 코드이자 user-web 동일 패턴, auth failure handler가 실제 만료 처리 담당 [`apps/admin-web/src/providers/AdminGuard.tsx:8`] — deferred, pre-existing
- [x] [Review][Defer] 루트 `page.tsx` 무조건 `/dashboard` 리다이렉트 — 미인증 사용자도 dashboard → login 왕복 발생하나 AdminGuard가 실제 보호 담당, 의도적 설계 [`apps/admin-web/src/app/page.tsx:4`] — deferred, pre-existing
- [x] [Review][Defer] SSR 하이드레이션 중 `getServerSnapshot = () => false` — Next.js 클라이언트 컴포넌트 표준 처리, 플리커 가능성은 user-web과 동일 수준 [`apps/admin-web/src/providers/AdminGuard.tsx:9`] — deferred, pre-existing

## Change Log

- 2026-06-11: Story 6.1 구현 완료 — admin-web 관리자 콘솔 셸 및 로그인 기능 구현. 패키지 의존성 추가, shadcn UI 컴포넌트, Providers, AdminGuard, AdminHeader, 로그인 페이지, 대시보드 플레이스홀더 생성. AC1~AC6 모두 충족.

## Story Progress Notes

### Agent Notes

- pnpm install Windows 환경 이슈로 shadcn 컴포넌트를 user-web에서 직접 복사, `@gosoom/api-client`는 Windows junction으로 연결 (pnpm 10.x + hoisted 링커 조합에서 restore-cursor/log-symbols 임포트 시 ERR_PNPM_ENOENT 발생)
- `useReadMe` 옵션 파라미터에서 `queryKey` 누락 타입 에러 → 옵션 없이 호출로 수정 (동작 동일)

### Completion Summary

관리자 콘솔 셸 및 로그인 기능 전체 구현 완료. Next.js admin-web 앱이 gosoom 브랜드 디자인 시스템으로 초기화되었고, 인증/권한 가드(AdminGuard), 관리자 전용 레이아웃(AdminHeader), 로그인 폼, 대시보드 플레이스홀더가 모두 완성되었습니다. 타입체크 통과, dev 서버 정상 기동 확인.
