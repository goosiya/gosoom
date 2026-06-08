---
baseline_commit: NO_VCS
---
# Story 1.7: 인증 UI(user-web) + api-client 확립

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 고객·고수,
I want user-web에서 가입·로그인 화면을 통해 계정을 만들고 로그인하기를,
So that 웹에서 즉시 서비스에 진입할 수 있다.

이 스토리는 **프로젝트 첫 프론트엔드 슬라이스**이며, Epic 2~6의 모든 웹 화면이 상속할 **4가지 프리미티브를 확립**한다(1.6이 "첫 목록 응답" 프리미티브를 확립한 것과 동일한 "첫 슬라이스가 선례를 만든다" 패턴):
① **api-client 생성 파이프라인** — FastAPI `openapi.json` → Orval → `packages/api-client/src/generated`(TS 타입 + TanStack Query 훅). 이후 모든 도메인 훅이 이 파이프라인으로 생성된다(수동 수정 금지, AR9).
② **단일 인증 인터셉터(`apiClient` mutator)** — `Authorization: Bearer` 부착 + 401→refresh 1회→재요청. 웹·모바일·관리자 3클라이언트가 공유(AR10). **가장 정확성 위험이 높은 코드** — 재귀 방지·토큰 스토어 설계가 핵심.
③ **TanStack Query Provider + 토큰 스토어** — 서버 상태 단일 소스(`isPending`/`error` 일관 처리). access=메모리, refresh=localStorage.
④ **클라이언트 라우트 가드** — 미인증 시 로그인 리다이렉트(UX 보조, 최종 권한은 서버).

> ⚠️ **범위의 본질(반드시 인지):** 이 스토리는 **인증 UI(가입·로그인) + 위 4프리미티브 확립 + 인증 후 최소 홈**만 한다. 고객/고수 도메인 화면(요청·견적·채팅 — Epic 2/3/4), 모바일(Epic 5), 관리자(Epic 6)는 **범위 밖**. 가드의 "보호 화면"도 이 스토리에선 **인증 후 홈 1개**만 존재한다(실제 도메인 화면은 후속 에픽). UI는 **기능 완결 우선**(가입→로그인 E2E) — 디자인 폴리시·반응형 정교화는 과설계 금지.

> 🔴 **CRITICAL — Next.js 16은 "기존에 알던 Next.js가 아니다"(`apps/user-web/AGENTS.md`):** API·규약·파일 구조가 학습 데이터와 다를 수 있다. **Next 코드를 작성하기 전에 번들된 공식 문서를 반드시 읽는다** → `apps/user-web/node_modules/next/dist/docs/01-app/`(특히 `01-getting-started/`, `03-api-reference/03-file-conventions/`, `03-api-reference/01-directives/use-client.md`). 이미 확인된 v16 파괴 변경: **`middleware.ts` 규약이 폐기되고 `proxy.ts`로 이름 변경**(아래 결정 #5). 그 외 async API 변경(cookies/headers/params 등)도 문서로 확인 후 작성.

## Acceptance Criteria

**AC1 — Orval 파이프라인 + 단일 Bearer 인터셉터(401→refresh 1회→재요청)**
**Given** FastAPI OpenAPI(`openapi.json`)가 준비되었을 때
**When** `pnpm orval`을 실행하면
**Then** `packages/api-client/src/generated`에 TS 타입 + TanStack Query 훅이 생성되고(수동 수정 금지, AR9), `packages/api-client/src/client.ts`에 단일 인터셉터(`apiClient` mutator)가 구성되어 모든 요청에 `Authorization: Bearer <access>`를 부착하고 **401 응답 시 refresh를 1회만 시도→성공하면 원요청 재시도, 실패하면 토큰 폐기+로그인 리다이렉트**한다(AR10). refresh 호출 자체의 401은 **재귀하지 않는다**(무한 루프 금지).

**AC2 — 가입→로그인 E2E 완결 + 토큰 저장 규약 + 인증 후 식별**
**Given** user-web에 `(auth)/signup`·`(auth)/login` 화면이 있을 때
**When** 사용자가 역할(customer|pro)을 선택하고 **표시명(displayName)**·이메일·비밀번호를 입력해 가입하고, 이어서 로그인하면
**Then** Orval 훅을 통해 백엔드(`POST /auth/signup` → `POST /auth/login`)와 통신하여 가입→로그인 플로우가 **E2E로 완결**되고, **access는 메모리·refresh는 웹 localStorage**에 보관된다(AR10). 로그인 성공 후 인증 후 홈으로 이동하며, 홈은 `GET /users/me`로 현재 사용자의 **displayName을 표시**(E2E 완결의 가시적 증거). 가입 폼에는 **표시명 입력이 포함**된다(Story 1.3 `display_name` 계약).

**AC3 — 로딩·오류 상태를 TanStack Query 상태로 일관 처리(한국어 메시지)**
**Given** 로딩·오류 상태가 발생할 때
**When** TanStack Query의 `isPending`/`error`를 사용하면(자체 boolean 난립 금지, architecture line 318)
**Then** 로딩 UI(버튼 비활성/스피너 등)와 에러 UI가 일관되게 표시되고, 에러 메시지는 **표준 envelope의 `message`(한국어)**로 노출된다(예: 중복 이메일 409 → "이미 가입된 이메일입니다." 류). 잘못된 자격증명 로그인(401)도 동일하게 `message`로 표시된다.

**AC4 — 미인증 보호 화면 접근 시 클라이언트 가드가 로그인으로 리다이렉트**
**Given** 미인증 상태로 보호 화면(인증 후 홈)에 접근할 때
**When** **클라이언트 라우트 가드**가 동작하면
**Then** 로그인 화면(`/login`)으로 리다이렉트된다(UX 보조, 최종 권한은 서버, AR17). 가드는 **클라이언트 컴포넌트**로 구현한다 — access는 메모리, refresh는 localStorage에 있어 **서버 `proxy.ts`는 이 토큰을 읽을 수 없으므로** 서버 가드로 구현하지 않는다(결정 #5).

## Tasks / Subtasks

- [x] **Task 1 — 의존성 추가 + openapi.json 생성 파이프라인 확립** (AC: 1)
  - [x] **루트 `package.json`** (UPDATE, devDependencies append): `orval` 최신 **7.x** 추가. (루트엔 이미 `"orval": "orval --config ./orval.config.ts"` 스크립트 존재 — 패키지만 누락.) 설치 후 `pnpm-lock.yaml`에 고정된 정확한 해소 버전을 `package.json`에도 캐럿 핀으로 기록.
  - [x] **`packages/api-client/package.json`** (UPDATE): Orval react-query 생성물이 `import ... from '@tanstack/react-query'` 하므로 **`@tanstack/react-query` 최신 5.x를 `dependencies`에 추가**(generated 훅이 해소 가능해야 함). `react`를 `peerDependencies`에 추가(훅이 React 의존). 생성물 소비를 위해 user-web도 같은 패키지를 의존(Task 4) — **버전 단일화**: pnpm-workspace `overrides`에 `@tanstack/react-query` 핀 추가 검토(react/react-dom 단일 해석과 동일 사유, AR2/G5 — QueryClient는 모듈 싱글턴이라 중복 인스턴스 시 Provider-훅 불일치).
  - [x] **`apps/user-web/package.json`** (UPDATE, dependencies append): `@gosoom/api-client: "workspace:*"` + `@tanstack/react-query`(api-client와 동일 버전) 추가. (기존 `@gosoom/ui`·next·react 보존.)
  - [x] **openapi.json 생성(오프라인 덤프 — 서버 기동 불요):** `apps/api`에서 FastAPI 앱의 `app.openapi()`를 **레포 루트 `./openapi.json`**(orval.config의 input이 기대하는 위치)로 기록.
    - 권장 명령(apps/api 디렉터리에서, **Python으로 직접 파일 기록** — Windows PowerShell `>` 리다이렉트는 UTF-16+BOM을 생성해 orval 파싱을 깨뜨림, 함정 참조):
      ```bash
      uv run python -c "import json; from app.main import app; open(r'../../openapi.json','w',encoding='utf-8').write(json.dumps(app.openapi(), ensure_ascii=False, indent=2))"
      ```
    - `ensure_ascii=False`: 스키마 description의 한국어 보존. `indent=2`: diff 가독성(선택).
    - **커밋 정책(결정 #1):** `openapi.json`은 **커밋하지 않는다**(재생성 아티팩트). 루트 `.gitignore`의 `openapi.json` 줄을 **그대로 유지**(제거·force-add 금지). `pnpm orval` 직전에 항상 덤프해 input으로 사용. 커밋 대상은 생성물(`generated/`)뿐.
  - [x] `pnpm install` 후 `pnpm orval`이 동작하는지 Task 3에서 검증.

- [x] **Task 2 — `apiClient` mutator 구현(client.ts): Bearer + 401→refresh 1회→재요청** (AC: 1) — **🔴 최고 정확성 위험**
  - [x] **`packages/api-client/src/client.ts`** (UPDATE — 기존 `resolveBaseUrl` 보존, append): orval.config가 이미 `override.mutator = { path: './packages/api-client/src/client.ts', name: 'apiClient' }`로 배선됨 → **`apiClient`라는 이름의 함수를 export**해야 한다(현재 미존재 — 생성 전 추가 필수).
  - [x] **mutator 시그니처는 설치된 orval 버전 문서로 확정**(메모리 하드코딩 금지): `pnpm install` 후 `node_modules/orval` 또는 orval.dev의 *custom mutator (react-query)* 규약 확인. fetch 기반 커스텀 mutator의 일반형은 단일 config 객체를 받아 **파싱된 데이터를 반환**:
    ```ts
    // 형태 예시(설치 버전으로 검증 후 확정) — 생성 훅이 apiClient<T>({url, method, params, data, headers, signal})로 호출.
    export const apiClient = async <T>(config: {
      url: string; method: string; params?: ...; data?: ...; headers?: ...; signal?: AbortSignal;
    }): Promise<T> => { ... }
    ```
    Orval이 `ErrorType`/`BodyType` 헬퍼 export를 요구하면 함께 export(버전 문서 기준).
  - [x] **(a) 토큰 스토어(모듈 레벨 단일 소스):** access는 **메모리(모듈 변수)**, refresh는 **localStorage**. 별도 모듈 권장(`src/token-store.ts` 신규) export:
    - `getAccessToken()/setAccessToken(t|null)` — 메모리 변수.
    - `getRefreshToken()/setRefreshToken(t|null)` — `localStorage`(SSR 안전 가드: `typeof window === 'undefined'`면 no-op/null). 키 예: `gosoom.refresh`.
    - `clearTokens()` — 둘 다 비움.
    - 로그인 성공 시 화면이 `setAccessToken`+`setRefreshToken` 호출(Task 5). mutator는 `getAccessToken`을 읽어 헤더 부착.
  - [x] **(b) baseURL:** 기존 `resolveBaseUrl()` 사용(`NEXT_PUBLIC_API_URL` → 폴백 `http://localhost:8000/api/v1`). mutator가 `url`을 baseURL에 합성.
  - [x] **(c) 401→refresh 1회→재요청(단발성·비재귀):**
    - 요청에 access 부착 → 응답 401이면 **refresh 1회 시도**(`POST /auth/refresh`, body `{refreshToken}` → 응답 `{accessToken}`). 성공 시 `setAccessToken(new)` 후 **원요청 1회 재시도**.
    - **refresh 호출은 인터셉터를 재귀하지 않는다** — refresh 요청 자체가 401/실패면 `clearTokens()` → **로그인 리다이렉트**(`window.location.href = '/login'` 또는 주입된 콜백) → 에러 throw. (refresh 엔드포인트로의 요청에는 401-refresh 로직을 적용하지 않도록 분기. 재시도 플래그/별도 경로로 무한 루프 차단.)
    - **동시 401 다발 시** 중복 refresh를 막는 단일 in-flight refresh promise(선택, 권장) — 여러 요청이 동시에 401이면 refresh를 1회만 수행하고 모두 그 결과를 공유.
  - [x] **(d) 에러 정규화:** 비-2xx 응답 본문(표준 envelope `{code, message, detail?}`)을 파싱해 **`message`를 가진 Error**로 throw(AC3가 `error.message`로 한국어 노출). TanStack Query `error.message`에 그대로 들어가도록.
  - [x] ❌ **axios 강제 아님:** fetch 기반으로 충분(과설계 금지). orval 커스텀 mutator는 반환 타입만 맞으면 구현 자유.

- [x] **Task 3 — Orval 생성 실행 → src/generated 확인** (AC: 1, 2)
  - [x] Task 1(openapi.json)·Task 2(apiClient export) 완료 후 **`pnpm orval`** 실행. `packages/api-client/src/generated/`에 tags-split(auth/users/categories) 훅 + `model/` 타입 생성 확인.
  - [x] 생성된 함수명이 **operationId(=라우트 함수명)** 기반인지 확인: `signup`/`login`/`refresh`(auth), `readMe`(users), `listCategories`(categories) → useMutation/useQuery 훅(예: `useSignup`/`useLogin`/`useReadMe`). 정확한 훅 네이밍은 생성물로 확인(orval react-query 규칙).
  - [x] **생성물 수동 수정 절대 금지(AR9)** — 스키마 변경이 필요하면 백엔드 수정 후 openapi 재덤프+재생성.
  - [x] `packages/api-client/src/index.ts` (UPDATE): generated barrel을 re-export(예: `export * from './generated';`) 추가 + 기존 `resolveBaseUrl` export 보존. user-web이 `@gosoom/api-client`에서 훅을 import할 수 있게.

- [x] **Task 4 — providers: QueryClientProvider + AuthProvider(클라이언트 가드)** (AC: 1, 3, 4)
  - [x] **`apps/user-web/src/providers/`** (NEW): `QueryProvider`(또는 `Providers`) — `"use client"`, `QueryClient` 1개 생성(`useState(() => new QueryClient())` 패턴으로 재렌더 시 재생성 방지), `<QueryClientProvider>`로 children 감쌈. layout에서 사용(Task 7).
  - [x] **`AuthProvider`/가드(클라이언트)** — `"use client"`. 인증 여부 판단(메모리 access 또는 localStorage refresh 존재)으로 보호 라우트에서 미인증 시 `useRouter().replace('/login')`. **서버 `proxy.ts` 아님**(결정 #5). 보호 영역은 인증 후 홈 레이아웃에 적용(Task 6).
  - [x] mutator의 "refresh 실패 시 로그인 리다이렉트"와 가드를 일관되게: 토큰 폐기 시 가드가 자연히 `/login`으로 보냄.

- [x] **Task 5 — `(auth)/signup` + `(auth)/login` 화면** (AC: 2, 3)
  - [x] **App Router route group** `(auth)`(URL에 미포함) 하위에 `signup/page.tsx`·`login/page.tsx` — route-groups 규약은 v16 문서로 확인(`03-file-conventions/route-groups.md`). 둘 다 `"use client"`(폼 상태·훅·RN-Web 컴포넌트 사용).
  - [x] **회원가입 폼:** 입력 = 이메일·비밀번호·**표시명(displayName)**·**역할(customer|pro)**. 입력 컴포넌트는 **`@gosoom/ui`의 `Input`**(value/onChangeText, `secureTextEntry`로 비밀번호, `keyboardType="email-address"`)·**`Button`**(label/onPress) 재사용. 상태는 `useState`.
    - **역할 선택:** `@gosoom/ui`엔 선택 프리미티브가 없다(Button/Input/Card만). **네이티브 라디오**(`<label><input type="radio" name="role">고객</label>` / `고수`)로 구현 — user-web 전용 웹 화면이므로 허용. ❌ 이 스토리에서 `@gosoom/ui`에 Select/Radio를 추가하지 않는다(모바일은 Epic 5에서 자체 구현 — ui 확장은 과설계).
    - 제출 → Orval `useSignup` 뮤테이션. 성공 → **`/login`으로 이동**(성공 메시지 표시) 또는 자동 로그인은 하지 않음(단순화 — 가입과 로그인 경계 명확). `isPending`으로 버튼 비활성, `error.message`로 오류(중복 이메일 409 등) 표시(AC3).
  - [x] **로그인 폼:** 이메일·비밀번호 → Orval `useLogin` 뮤테이션. 성공 시 응답 `{accessToken, refreshToken}`을 **토큰 스토어에 저장**(`setAccessToken`/`setRefreshToken`) 후 인증 후 홈으로 `router.replace('/')`(또는 `/home`). `isPending`/`error.message`(401 "이메일 또는 비밀번호가 올바르지 않습니다." 류) 처리(AC3).
  - [x] 폼 검증은 백엔드 신뢰(서버 422 envelope를 `error`로 표시). 클라이언트 최소 검증(빈 값 비활성)만 — 중복 검증 로직 난립 금지.

- [x] **Task 6 — 인증 후 홈 + 클라이언트 가드 적용** (AC: 2, 4)
  - [x] 인증 후 홈 화면(예: `src/app/page.tsx` 교체 또는 `(app)/home/page.tsx`) — `"use client"`. **클라이언트 가드 적용**(Task 4): 미인증이면 `/login` 리다이렉트.
  - [x] 홈은 Orval **`useReadMe`**(`GET /users/me`)로 현재 사용자 조회 → **`displayName` 표시**(예: "{displayName}님 환영합니다"). 로그아웃 버튼(`@gosoom/ui` Button) → `clearTokens()` + `/login` 리다이렉트(서버 토큰 무효화 없음 — 무상태, Story 1.4 AC4 계승).
  - [x] 현재 `src/app/page.tsx`는 Story 1.1 검증 슬라이스(@gosoom/ui Button 렌더) — **이 스토리에서 인증 후 홈으로 교체**(검증 목적 달성, 더 이상 불필요). 미인증 진입 시 가드가 `/login`으로 보냄.

- [x] **Task 7 — layout.tsx 업데이트(ko + metadata + providers)** (AC: 1, 3)
  - [x] **`apps/user-web/src/app/layout.tsx`** (UPDATE): `<html lang="en">`→**`lang="ko"`**, metadata `title:"Create Next App"`/`description:"Generated by create next app"`→**실제 값**(예: title "gosoom", description "고객·고수 서비스 매칭"). **Geist 폰트 변수·className·body 구조는 보존**. children을 **`<Providers>`(QueryClientProvider)로 래핑**(Task 4).
  - [x] layout은 서버 컴포넌트 유지 가능(Providers가 `"use client"`) — v16 문서로 layout 규약 확인(`03-file-conventions/layout.md`).

- [x] **Task 8 — 환경변수: .env.local.example + 로컬 .env.local** (AC: 1, 2)
  - [x] **`apps/user-web/.env.local.example`** (NEW): `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`(루트 `.env.example`·architecture line 371 정합). `NEXT_PUBLIC_*`만 클라이언트 노출(시크릿 금지, AR18). env 규약은 v16 문서(`02-guides/environment-variables.md`)로 확인.
  - [x] 실제 `apps/user-web/.env.local`(gitignore 대상)은 **KTH 체크포인트**에서 생성 안내(아래). dev는 example만 커밋.

- [x] **Task 9 — 테스트(thin slice) + 수동 E2E 체크리스트** (AC: 1, 2, 3, 4)
  - [x] **결정(아래 #6): 풀 E2E(Playwright) 대신 thin slice** — ① mutator/refresh 로직 단위 테스트(순수·고위험), ② 수동 E2E 체크리스트. 풀 자동화 E2E·CI 연동은 Story 1.8(CI 소유) 또는 후속으로 연기.
  - [x] **단위 테스트(Vitest 권장):** `packages/api-client`에 Vitest 도입(devDep + `"test": "vitest run"` 스크립트). `client.ts`/`token-store.ts`의 **인터셉터 핵심 로직** 검증 — `fetch`를 mock하여:
    - 200 정상: access 헤더 부착 확인.
    - 401→refresh 성공→원요청 재시도: refresh가 **정확히 1회**, 원요청 재시도 후 성공 반환.
    - refresh 실패(401): `clearTokens()` 호출 + 리다이렉트 콜백 발동 + **재귀/무한루프 없음**(refresh 호출은 1회로 종료).
    - 토큰 스토어: access=메모리, refresh=localStorage 분리(SSR `window` 부재 가드 포함).
    - (생성물 generated 훅은 빌드 아티팩트라 테스트 대상 아님 — mutator 계약만 검증.)
  - [x] **수동 E2E 체크리스트(스토리 완료 증거):** apps/api 기동(`uv run uvicorn app.main:app --reload`) + user-web 기동(`pnpm --filter user-web dev`) 상태에서:
    1. `/signup`에서 customer 역할·표시명·이메일·비밀번호 가입 → 성공 → `/login` 이동.
    2. 같은 이메일 재가입 시도 → 409 한국어 메시지 노출(AC3).
    3. `/login` 로그인 → 인증 후 홈으로 이동, **displayName 표시**(AC2).
    4. 잘못된 비밀번호 로그인 → 401 한국어 메시지(AC3).
    5. 로그아웃 → `/login` 리다이렉트, 보호 홈 재진입 시 가드가 `/login`으로 보냄(AC4).
    6. (선택) access 만료 시뮬레이션(짧은 만료 토큰 또는 메모리 access 강제 폐기) → 다음 요청 401→refresh→재요청 성공(AC1).
  - [x] ❌ 백엔드 pytest는 변경 없음(이 스토리는 프론트 전용 — API 계약 동결). 회귀 0.

- [x] **Task 10 — 품질 게이트: typecheck/lint/build 통과** (AC: 전체)
  - [x] `pnpm typecheck`(turbo) — api-client(생성물 포함)·user-web 타입 통과. 생성물 타입 오류는 openapi/orval 설정 문제 → 수정은 설정/백엔드, 생성물 직접 수정 금지.
  - [x] `pnpm lint`(turbo) — eslint(next config). 생성물은 lint 제외 설정 필요 시 `.eslintignore`/flat config ignore에 `packages/api-client/src/generated` 추가(생성물은 빌드 아티팩트).
  - [x] `pnpm build`(turbo) — user-web `next build` 성공(생성 훅 import 해소 확인).
  - [x] `pnpm --filter @gosoom/api-client test`(Vitest) 통과.

## Dev Notes

### 🎯 스코프 경계 (범위 침범 금지)

- ✅ **이 스토리:** Orval 파이프라인(openapi 덤프→생성), `apiClient` 단일 인터셉터(Bearer+401 refresh), TanStack Provider+토큰 스토어, `(auth)/signup`·`(auth)/login` 화면, 인증 후 최소 홈(`/users/me` displayName), 클라이언트 가드, layout 정비. **첫 프론트 슬라이스 = 위 4프리미티브 확립.**
- ❌ **도메인 화면 금지(Epic 2/3/4):** 요청 생성·목록·견적·채팅 화면/훅 소비 금지. categories 훅은 **생성만**(openapi에 존재) 되지만 화면 소비는 이 스토리 밖(생성 검증용으로 `useReadMe`만 실소비).
- ❌ **모바일(Expo) 금지(Epic 5)** · **관리자(admin-web) 금지(Epic 6).** api-client는 3앱 공유지만 이 스토리는 user-web만 배선.
- ❌ **`@gosoom/ui` 확장 금지:** Select/Radio/Form 등 신규 프리미티브 추가 금지(역할 선택은 네이티브 라디오). ui 확장은 실제 필요(모바일 Epic 5) 시점에.
- ❌ **refresh 회전·블랙리스트·httpOnly 쿠키 금지(Post-MVP):** MVP는 access=메모리/refresh=localStorage, refresh로 access만 재발급(architecture line 187-194). XSS 강화는 Post-MVP.
- ❌ **백엔드 변경 금지:** auth/users/categories 계약은 1.3~1.6에서 동결. openapi는 현재 코드의 덤프만. 계약 부족분 발견 시 스토리 밖(별도 협의).
- ❌ **풀 자동화 E2E(Playwright)·프론트 CI 금지:** thin slice(mutator 단위 + 수동 체크리스트). CI는 Story 1.8.

### ⚖️ 결정 사항 (Dev가 그대로 채택)

- **🔑 #1 — openapi.json은 재생성 아티팩트(gitignore 유지, 커밋 안 함):** `app.openapi()`를 Python으로 레포 루트 `./openapi.json`에 기록(orval.config input 위치). **PowerShell `>` 리다이렉트 금지**(UTF-16+BOM → orval 파싱 실패) — `open(...,encoding='utf-8')`로 직접 기록. `ensure_ascii=False`로 한국어 보존. **레포에 커밋하지 않는다** — 루트 `.gitignore`가 이미 `openapi.json`을 무시(작성자 의도). `pnpm orval` **직전에 항상 덤프**(로컬·CI 동일). 추적/커밋 대상은 **생성물(`packages/api-client/src/generated/`)**이고, openapi.json은 중간 산출물(임시). 1.8 CI는 "덤프 → orval(또는 생성물 최신성 검증)" 단계를 갖는다.
- **🔑 #2 — `apiClient` mutator가 최고 위험 코드:** orval.config가 이미 mutator로 배선 → client.ts에 `apiClient` export 필수. 시그니처는 **설치된 orval 버전 문서로 확정**(메모리 금지). 3대 불변식: ① 토큰 스토어(access=메모리, refresh=localStorage) 단일 소스, ② 401→refresh **1회**→재요청, ③ **refresh 호출 비재귀**(refresh-401 → clearTokens + `/login` 리다이렉트, 무한 루프 금지). 동시 401은 단일 in-flight refresh 공유 권장.
- **🔑 #3 — TanStack Query 단일 소스(AR/architecture line 309·318):** 로딩=`isPending`/`isFetching`, 오류=`error`. 자체 boolean·수동 캐시 중복 금지. 에러 메시지=`error.message`(한국어 envelope `message`).
- **🔑 #4 — 토큰 저장 위치 고정(architecture line 187):** access=클라이언트 **메모리**(모듈 변수, 휘발), refresh=**localStorage**(`gosoom.refresh`). 웹/모바일 분기 없음(모바일은 Epic 5에서 SecureStore — api-client는 저장 추상화로 분기 없이). SSR 가드(`typeof window`) 필수.
- **🔑 #5 — 가드는 클라이언트, `proxy.ts` 아님:** **Next 16에서 `middleware.ts`→`proxy.ts`로 규약 변경**(확인됨). 그러나 access는 메모리·refresh는 localStorage → **서버 proxy는 토큰을 못 읽는다**. 따라서 가드는 **클라이언트 컴포넌트**(layout/AuthProvider에서 `useRouter().replace('/login')`). 최종 권한 시행은 서버 API(NFR4) — 가드는 UX 보조일 뿐. (architecture line 384가 `middleware.ts`를 적었으나 이는 v16 이전 명칭 + 토큰 모델상 클라이언트 가드로 귀결.)
- **🔑 #6 — 테스트: thin slice 결정:** 프론트 테스트 인프라가 0(JS 앱에 러너 없음). 풀 E2E(Playwright)는 첫 프론트 슬라이스엔 과대, RTL+RN-Web+Next16은 고통. → **mutator/refresh 단위 테스트(Vitest, 고위험·순수)** + **수동 E2E 체크리스트**. 풀 자동화는 1.8(CI) 또는 후속. *(KTH가 풀 Playwright E2E를 원하면 dev-story 전에 알려주세요 — 범위 확대.)*
- **#7 — 가입 후 자동 로그인 안 함:** 가입 성공 → `/login` 이동(성공 메시지). 가입/로그인 경계 명확·단순. (자동 로그인은 UX 개선 항목, 후속.)
- **#8 — `@tanstack/react-query` 단일 인스턴스:** QueryClient는 모듈 싱글턴 → api-client·user-web가 **동일 버전** 의존(pnpm overrides 핀 권장, react 단일 해석과 동일 사유). 중복 시 Provider-훅 컨텍스트 불일치로 런타임 오류.

### ⚠️ 알려진 함정 (런타임 디버깅 전 미리 적용 — 고가치)

1. **🔴 Next.js 16 = 다른 프레임워크(AGENTS.md):** 코드 작성 전 `apps/user-web/node_modules/next/dist/docs/01-app/` 읽기. 확인된 변경: `middleware.ts`→`proxy.ts`. 추가로 cookies/headers/params 등 async API 변경 가능 — route-groups·layout·use-client·environment-variables 문서 우선 확인.
2. **PowerShell `>` UTF-16 함정:** `... > openapi.json`은 BOM 포함 UTF-16 LE 생성 → orval이 JSON 파싱 실패. **Python `open(encoding='utf-8')`로 기록**(결정 #1).
3. **openapi.json 경로 불일치:** 명령은 `apps/api`에서 실행, 파일은 **레포 루트**(`../../openapi.json`)에 떨어져야 orval.config(`./openapi.json`)가 찾는다. 상대경로 주의.
4. **`apiClient` export 누락 시 orval 생성 실패/런타임 깨짐:** orval.config가 mutator name `apiClient`를 참조 → client.ts에 해당 export 없으면 생성물이 깨진 import 생성. **Task 2(export 추가)를 Task 3(생성)보다 먼저.**
5. **refresh 무한 루프:** refresh 요청 자체에 401-refresh 로직을 적용하면 무한 재귀. refresh 경로 분기 또는 retry 플래그로 **1회 보장**. refresh 실패 → `clearTokens`+리다이렉트로 종료.
6. **QueryClient 재생성:** `new QueryClient()`를 컴포넌트 본문에서 직접 호출하면 매 렌더 재생성 → 캐시 소실. `useState(() => new QueryClient())`(또는 모듈 상수)로 1회 생성.
7. **`"use client"` 누락:** TanStack 훅·RN-Web 컴포넌트·`useState`/`useRouter` 사용 화면/Provider는 모두 클라이언트 컴포넌트. page/provider 최상단 `"use client"` 필수(v16 use-client 문서 확인).
8. **CORS 401/차단:** 브라우저 user-web(`localhost:3000`)→API(`localhost:8000`), `allow_credentials=True` → `apps/api/.env`의 `CORS_ORIGINS`에 `http://localhost:3000` **포함 필수**(없으면 preflight 차단). KTH 체크포인트 참조. (deferred-work의 credentialed-wildcard 풋건과 동일 영역 — `*` 금지.)
9. **localStorage SSR 부재:** Next는 서버에서 모듈 평가 → `localStorage` 접근 시 `typeof window === 'undefined'` 가드 필수(아니면 빌드/SSR 크래시).
10. **생성물 lint/typecheck 오염:** `packages/api-client/src/generated`는 빌드 아티팩트 → eslint ignore에 추가. 타입 오류는 openapi/orval 설정에서 해결(생성물 직접 수정 금지, AR9).
11. **`@tanstack/react-query` 미설치 → 생성물 import 해소 실패:** 생성 전 api-client 의존성에 추가(Task 1). user-web Provider도 동일 패키지 필요.

### 현재 코드 상태 (UPDATE/NEW 대상 — 보존할 것)

Story 1.1이 모노레포+4앱 골격을, 1.2~1.6이 백엔드 auth/users/categories를 완성. 프론트엔드는 **user-web가 기본 Next 16 스캐폴드 상태**(가입/로그인·Provider·api-client 소비 전무). 아래는 실제 현재 상태 — **덮어쓰지 말고 확장/배선**:

- **`orval.config.ts`** (그대로 — 활성화만): input `./openapi.json`, output tags-split/react-query, mutator `apiClient`(client.ts). **이미 1.7용으로 구성됨** — openapi.json만 만들면 동작. 변경 불요(경로/이름 정합 확인만).
- **`packages/api-client/src/client.ts`** (UPDATE, append): 현재 `resolveBaseUrl()`만 export(주석에 "1.7에서 Bearer 인터셉터 구현" 명시). → **`apiClient` mutator 추가**(resolveBaseUrl 보존·재사용).
- **`packages/api-client/src/index.ts`** (UPDATE): 현재 `resolveBaseUrl`만 re-export. → generated barrel re-export 추가(`export * from './generated'`), resolveBaseUrl 보존.
- **`packages/api-client/package.json`** (UPDATE): 현재 deps 없음(typecheck만). → `@tanstack/react-query` dependency + `react` peerDependency + Vitest devDep + test 스크립트 추가.
- **루트 `package.json`** (UPDATE): `orval` 스크립트 존재하나 **패키지 미설치** → devDep `orval` 추가.
- **`apps/user-web/src/app/layout.tsx`** (UPDATE): `lang="en"`·"Create Next App" metadata·Geist 폰트. → `lang="ko"`+실제 metadata+Providers 래핑(폰트·구조 보존).
- **`apps/user-web/src/app/page.tsx`** (REPLACE): Story 1.1 검증 슬라이스(@gosoom/ui Button alert). → 인증 후 홈(또는 가드로 보호)으로 교체. `"use client"`+@gosoom/ui 재사용 패턴은 계승.
- **`apps/user-web/src/app/globals.css`** (그대로 — Tailwind v4 `@import "tailwindcss"`). 추가 스타일 최소.
- **`apps/user-web/package.json`** (UPDATE): 현재 `@gosoom/ui`·next 16.2.7·react 19.2.4. → `@gosoom/api-client`·`@tanstack/react-query` 추가. (lint/typecheck/build 스크립트 보존.)
- **`packages/ui/src/{Button,Input,Card}.tsx`** (그대로 — 소비만): RN 기반. Button(label/onPress/disabled), Input(value/onChangeText/placeholder/secureTextEntry/keyboardType/editable). 가입·로그인 폼이 재사용. **수정 금지**(확장도 금지).
- **`pnpm-workspace.yaml`** (UPDATE 검토): react/react-dom overrides 존재. → `@tanstack/react-query` 단일 핀 추가 검토(결정 #8).
- **`apps/api/app/`** (그대로 — 계약 소스): `routers/auth.py`(signup/login/refresh), `routers/users.py`(read_me), `routers/categories.py`(list_categories), `schemas/auth.py`(SignupRequest{email,password,displayName,role}, LoginRequest, TokenResponse{accessToken,refreshToken,tokenType}, RefreshRequest{refreshToken}, RefreshResponse{accessToken}, UserRead{id,email,displayName,userRole,isActive,...}). **openapi 덤프 소스 — 변경 없음.**
- **`apps/api/.env`** (KTH 확인 — CORS): `CORS_ORIGINS`에 `http://localhost:3000` 포함 필요(체크포인트).

### 아키텍처 준수 (반드시 따를 규약)

- **클라이언트 생성=Orval:** `openapi.json`→`packages/api-client` TS 타입+TanStack Query 훅. FastAPI Pydantic이 단일 소스. 생성물 수동 수정 금지(빌드 아티팩트).
  [Source: architecture.md#API & Communication Patterns (line 200-202), Anti-Patterns (line 326·343), AR9]
- **단일 인증 인터셉터:** api-client가 `Authorization: Bearer` 부착, 401 시 refresh 1회→재요청, 실패 시 토큰 폐기+로그인 유도. 웹·모바일 공유 단일 구현.
  [Source: architecture.md#Authentication & Security (line 186-194), Process Patterns (line 314-316), AR10]
- **토큰 저장:** access=클라이언트 메모리(휘발), refresh=웹 localStorage(모바일 SecureStore는 Epic 5). Bearer 무상태.
  [Source: architecture.md#Authentication & Security (line 187), 1-4 story AC4]
- **서버 상태=TanStack Query v5 단일 소스:** 로딩 `isPending`/`isFetching`, 오류 `error`, 불변 업데이트, 수동 캐시 중복 금지.
  [Source: architecture.md#Frontend Architecture (line 212), Process Patterns (line 309·318)]
- **라우팅/가드:** App Router route group `(auth)`. 역할/인증 가드는 레이아웃에서(미인증 리다이렉트). **권한 최종 시행은 서버(NFR4)** — 가드는 UX 보조. (v16: `middleware.ts`→`proxy.ts`이나 토큰 모델상 클라이언트 가드.)
  [Source: architecture.md#Frontend Architecture (line 214), Directory (line 375-376·384), AR17]
- **에러 envelope:** `{code, message, detail?}` — 클라이언트는 `message`(한국어)로 사용자에 노출. api-client에서 일관 처리.
  [Source: architecture.md#API Patterns (line 203), Process Patterns (line 317)]
- **환경:** `NEXT_PUBLIC_API_URL`로 API 베이스 주입. 클라이언트엔 `*_PUBLIC_*`만(시크릿 금지).
  [Source: architecture.md#Frontend Architecture (line 216), Infrastructure (line 223), AR18]
- **명명:** JSON 경계 camelCase(displayName, accessToken, nextCursor) — Orval이 백엔드 to_camel과 정합. TS는 camelCase 변수·PascalCase 타입.
  [Source: architecture.md#Naming Patterns (line 268·276-280), Coherence (line 496)]
- **스타일:** Tailwind(웹) + 공유 `@gosoom/ui`(RN-Web 프리미티브). 앱 고유 화면=`apps/user-web/features` 또는 `app/`.
  [Source: architecture.md#Frontend Architecture (line 215), Structure (line 292), Directory (line 382-383)]

### 라이브러리/버전 (검증·핀)

- **Next.js 16.2.7**(App Router·Turbopack 기본·React Compiler) · **React 19.2.4**(workspace override 19.2.0) — 이미 설치(user-web). ⚠️ **v16 파괴 변경 다수 — AGENTS.md 명령대로 번들 문서 선독**.
- **@tanstack/react-query 5.x**(신규) — api-client dependency + user-web. Orval react-query 생성물이 import. **단일 버전 핀**(결정 #8).
- **orval 7.x**(신규, 루트 devDep) — 생성기. mutator 시그니처는 **설치 버전 문서로 확정**(메모리 금지).
- **Vitest**(신규, api-client devDep) — mutator/토큰 스토어 단위 테스트(thin slice).
- **react-native-web ~0.21.0**(설치됨) — `@gosoom/ui` RN 컴포넌트를 웹에서 렌더(Story 1.1 검증). next.config의 RN-Web 별칭 이미 동작.
- 패키지 매니저 **pnpm 11.5.2**, **turbo 2.9.16**, Node ≥20. 설치=`pnpm install`(워크스페이스), 생성=`pnpm orval`, 개발=`pnpm --filter user-web dev`.
  [Source: package.json, apps/user-web/package.json, packages/api-client/package.json, architecture.md#Tech Stack (line 101·493), 1-1 scaffold]

### 파일 구조 (생성/수정 위치)

```
gosoom/
  package.json                       (UPDATE) devDep: orval
  orval.config.ts                    (그대로 — 이미 1.7 구성)
  openapi.json                       (재생성 아티팩트, gitignore 유지 — 커밋 안 함) orval 직전 덤프
  .gitignore                         (그대로 — openapi.json 무시 줄 유지)
  pnpm-workspace.yaml                (UPDATE 검토) @tanstack/react-query 핀
  packages/api-client/
    package.json                     (UPDATE) deps: @tanstack/react-query, peer: react, devDep: vitest
    src/
      client.ts                      (UPDATE, append) apiClient mutator(Bearer+401 refresh)
      token-store.ts                 (NEW) access=메모리 / refresh=localStorage 스토어
      index.ts                       (UPDATE) generated barrel re-export(resolveBaseUrl 보존)
      generated/                     (NEW, 자동생성 — 수정 금지) tags-split 훅 + model/
    tests/ (또는 src/*.test.ts)       (NEW) mutator/refresh/토큰 스토어 단위(Vitest)
  apps/user-web/
    package.json                     (UPDATE) deps: @gosoom/api-client, @tanstack/react-query
    .env.local.example               (NEW) NEXT_PUBLIC_API_URL
    src/
      app/
        layout.tsx                   (UPDATE) lang=ko, metadata, Providers 래핑(폰트 보존)
        page.tsx                     (REPLACE) 인증 후 홈(가드 보호) — useReadMe displayName
        (auth)/login/page.tsx        (NEW) 로그인 폼(useLogin→토큰 저장→홈)
        (auth)/signup/page.tsx       (NEW) 가입 폼(displayName+역할 라디오, useSignup→/login)
      providers/                     (NEW) QueryClientProvider + AuthProvider(클라이언트 가드)
  # proxy.ts(서버 가드) 만들지 않음 — 클라이언트 가드(결정 #5)
  # apps/api: 변경 없음(openapi 덤프 소스). apps/admin-web·mobile: 범위 밖.
```
[Source: architecture.md#Complete Project Directory Structure (line 351-435), orval.config.ts, 현재 user-web/api-client 상태]

### 테스트 표준

- **프론트 인프라는 이 스토리에서 처음 도입(thin slice).** 백엔드 pytest(실 DB)와 달리 JS 앱엔 러너가 없었다 → **Vitest를 api-client에 도입**해 인터셉터 핵심 로직(고위험·순수)만 단위 검증. `fetch` mock으로 401→refresh→재요청, refresh 실패→clear+리다이렉트, 비재귀, 토큰 스토어 메모리/localStorage 분리를 증명.
- **화면(page) 렌더 테스트는 이 스토리 범위 밖**(RTL+RN-Web+Next16 비용 과대) — **수동 E2E 체크리스트**(Task 9)로 가입→로그인→홈→가드를 사람 검증. 풀 자동화 E2E·프론트 CI는 Story 1.8.
- 백엔드 회귀 0(계약 동결 — pytest 변경 없음). `pnpm typecheck`/`lint`/`build` 그린이 통합 게이트.
  [Source: architecture.md#Process Patterns(테스트), 1.8 CI 범위, 결정 #6]

### Project Structure Notes

- 정합: `packages/api-client/src/{client,generated,index}` 배치, `apps/user-web/src/app/(auth)/{login,signup}`, `providers/`는 architecture 디렉터리 구조(line 372-384·429-432) 그대로. orval.config·client.ts 스텁이 이미 1.7을 예고(주석 명시).
- 변이: ① architecture line 384는 `middleware.ts`(가드)를 적었으나 **v16 규약 변경(`proxy.ts`) + 메모리/localStorage 토큰 모델**상 **클라이언트 가드**로 귀결(서버 가드 불가) — 새 아키텍처 결정이 아니라 토큰 전략(line 187)의 필연적 귀결. ② 프론트 테스트 전략(thin slice)은 architecture가 미명시한 신규 결정 — 1.8 CI 소유·greenfield 근거로 채택(결정 #6).
- 신규 패턴(Orval 소비, TanStack Provider, 인터셉터, 클라이언트 가드)은 Epic 2~6 웹 화면이 상속할 **선례**. 도메인 화면은 이 4프리미티브 위에 훅 소비만 추가한다.

### 이전 스토리 학습 / 정합

- **1.3~1.6 계약 동결 소비:** signup(displayName+role)/login(accessToken+refreshToken)/refresh(accessToken만)/read_me(UserRead)/list_categories(Page) — operationId(함수명)가 1.3~1.6에서 안정화됨(각 라우터 주석 "소비는 1.7"). Orval 함수명이 이에 직결 → 백엔드 함수명 변경 시 프론트 깨짐(동결 유지).
- **1.4 토큰 계약:** `TokenResponse{accessToken,refreshToken}`·`RefreshResponse{accessToken}`(회전 없음) — refresh는 access만 재발급. 인터셉터가 이 계약대로(refresh 응답에 refreshToken 없음 주의).
- **1.5 인증 모델:** `get_current_user`가 매 요청 재조회로 비활성/삭제 즉시 차단·401. `/users/me`(read_me)는 인증만 — 홈이 소비. 서버가 최종 권한, 클라이언트 가드는 UX 보조.
- **1.6 camelCase 경계:** `{items, nextCursor}`·`isActive` 등 camel — Orval이 백엔드 to_camel과 자동 정합(수기 매핑 금지, architecture line 343).
- **manual-setup-checkpoints 메모 계승:** 외부 설정(CORS env)을 dev-story 전 KTH에 선안내(아래 체크포인트).
  [Source: 1-3~1-6 story 라우터/스키마 주석, architecture.md#Coherence(line 496-497), manual-setup-checkpoints 메모]

### References

- [Source: epics.md#Story 1.7 (line 315-337)] — 4개 AC 원본(BDD): Orval+인터셉터, 가입→로그인 E2E·토큰 저장, 로딩/오류 일관, 미인증 가드
- [Source: epics.md#Story 1.8 (line 339-358)] — CI(pytest+JS lint/typecheck/build)·Railway 배포 = 후속(프론트 자동 E2E·CI 소유)
- [Source: architecture.md#Authentication & Security (line 184-195)] — Bearer 통일, access 메모리/refresh 저장, refresh 전략, CORS 명시 오리진
- [Source: architecture.md#API & Communication Patterns (line 197-207)] — Orval 생성, operationId, 에러 envelope, REST `/api/v1`
- [Source: architecture.md#Frontend Architecture (line 209-217)] — App Router, TanStack Query v5, 가드, 스타일, NEXT_PUBLIC env
- [Source: architecture.md#Process Patterns (line 308-318)] — 폴링/인증 인터셉터, 불변 업데이트, error/isPending 일관
- [Source: architecture.md#Anti-Patterns (line 326·343)] — Orval 생성물 수정 금지, snake 수기 매핑 금지
- [Source: architecture.md#Complete Project Directory Structure (line 351-435)] — user-web/api-client 구조, providers, (auth) route group
- [Source: orval.config.ts] — 이미 구성된 input/output/mutator(apiClient) — openapi.json만 필요
- [Source: packages/api-client/src/{client,index}.ts] — resolveBaseUrl 스텁 + "1.7에서 인터셉터 구현" 명시
- [Source: apps/user-web/AGENTS.md] — 🔴 Next 16 파괴 변경, 번들 docs 선독 명령(node_modules/next/dist/docs)
- [Source: apps/api/app/routers/{auth,users,categories}.py, schemas/auth.py] — 소비 대상 엔드포인트·DTO 계약(동결)
- [Source: 1-4-login-logout-jwt.md, 1-5-rbac.md, 1-6-categories-api-seed.md] — 토큰/인증/camelCase 선례
- [Source: deferred-work.md (CORS credentialed-wildcard)] — CORS 설정 영역 주의(`*` 금지)
- [Source: backend-env-setup 메모, manual-setup-checkpoints 메모] — uv 실행(openapi 덤프), 외부 설정 선안내 원칙

## ⚡ 수동 설정 체크포인트 (AR23 — dev-story 진입 전 KTH 확인)

이 스토리는 **브라우저↔API 실통신**이 처음이라 두 가지 로컬 설정이 필요합니다(외부 서비스 가입은 불요 — 모두 로컬):

1. **API CORS 허용(필수):** `apps/api/.env`의 `CORS_ORIGINS`에 **`http://localhost:3000`**(user-web 기본 포트)이 포함돼야 브라우저 가입/로그인이 동작합니다. `allow_credentials=True`라 와일드카드 `*`는 금지 — 명시 오리진으로. 현재 `.env`에 없으면 추가해 주세요.
   - 확인 방법: `apps/api/.env` 열어 `CORS_ORIGINS=http://localhost:3000`(또는 콤마로 다중) 확인/추가.
2. **user-web 환경변수(필수):** dev가 `apps/user-web/.env.local.example`을 커밋합니다. 로컬 실행 전 **`apps/user-web/.env.local`**(gitignore)을 만들어 `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`을 넣어주세요(API 포트가 다르면 맞춰서).
3. **검증용(선택):** API 기동(`apps/api`에서 `uv run uvicorn app.main:app --reload`) + `pnpm --filter user-web dev` 후 `/signup`→`/login`→홈(displayName) 수동 플로우(Task 9 체크리스트)로 E2E 확인.

**확정된 결정 (2026-06-08 KTH 확인 — dev는 아래대로 진행):**
- **로컬 설정 주체:** 위 1·2(CORS_ORIGINS·.env.local)는 **KTH가 직접 처리**한다. dev는 `apps/api/.env`를 편집하지 않고(비밀 보유 파일), `apps/user-web/.env.local.example`만 커밋. KTH가 두 설정을 마치면 dev-story 진입.
- **테스트 범위(결정 #6):** **thin slice 확정** — mutator/refresh 단위 테스트(Vitest) + 수동 E2E 체크리스트로 완료. 풀 Playwright E2E는 후속/1.8 CI(이 스토리 범위 아님).
- **openapi.json(결정 #1):** **커밋 안 함 확정** — 재생성 아티팩트로 취급, 루트 `.gitignore`의 `openapi.json` 무시 유지. `pnpm orval` 직전 항상 덤프(로컬·CI). 커밋 대상은 생성물 `generated/`뿐. (1.8 CI에 "덤프→orval" 단계.)
- **가입 후 흐름(결정 #7):** **`/login` 이동 확정** — 가입 성공 시 자동 로그인하지 않고 로그인 화면으로(성공 메시지 표시).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (1M context) — bmad-dev-story 워크플로우

### Debug Log References

- `pnpm orval` 생성 시 tags-split 모드는 루트 barrel(`generated/index.ts`)을 만들지 않음(`indexFiles: true`도 무효) → `packages/api-client/src/index.ts`에서 태그별 파일을 명시 re-export로 해결.
- 단위 테스트 초기 2건 실패 → 원인은 **테스트 mock 버그**(refresh 경로가 `response.json()` 사용인데 fake Response가 `text()`만 구현). fake Response에 `json()` 추가로 해결(구현 코드는 무변경).
- ESLint(React Compiler `react-hooks/set-state-in-effect`)가 AuthGuard의 effect 내 동기 setState를 차단 → `useSyncExternalStore`(서버 스냅샷=false)로 재작성, 하이드레이션 불일치도 동시 해소.

### Completion Notes List

**확립된 4프리미티브(Epic 2~6 웹 화면이 상속할 선례):**
1. **Orval 파이프라인** — `app.openapi()`를 레포 루트 `openapi.json`(BOM 없는 UTF-8, gitignore 유지)으로 덤프 → `pnpm orval` → `packages/api-client/src/generated`(TS 타입 + TanStack Query 훅). 훅: `useSignup`/`useLogin`/`useRefresh`/`useReadMe`/`useListCategories`.
2. **단일 `apiClient` mutator**(`client.ts`) — Bearer 부착 + 401→refresh 1회→원요청 1회 재시도. **refresh는 인터셉터 우회 직접 fetch**(비재귀, 함정 #5), **단일 in-flight refresh**(동시 401 공유), refresh 실패 시 `clearTokens`+로그인 유도, 에러 정규화(envelope `message`→`error.message` 한국어).
3. **TanStack Query Provider + 토큰 스토어** — `Providers.tsx`(QueryClient 1회 생성), `token-store.ts`(access=메모리/refresh=localStorage, SSR `window` 가드).
4. **클라이언트 가드** — `AuthGuard.tsx`(`useSyncExternalStore`로 `isAuthenticated`=access OR refresh 판단, 미인증 시 `/login` 리다이렉트). 서버 `proxy.ts` 미사용(토큰 모델상 불가, 결정 #5).

**⚠️ 필요한 편차 1건(스토리 가정 보정):** 스토리는 orval.config "변경 불요"라 했으나, 이는 작성자가 FastAPI가 클린 operationId를 낸다고 가정한 데서 비롯. 실제 기본 operationId는 verbose(`signup_api_v1_auth_signup_post`)라 그대로면 훅명이 `useSignupApiV1AuthSignupPost`가 됨. **백엔드는 무변경(계약 동결 준수)**, orval.config에 `operationName` 오버라이드(`_api_v1_...` 접미 제거)만 추가해 codegen 계층에서 클린 훅명을 확보(프론트 한정 해결). 또한 **baseURL 경로 중복**(NEXT_PUBLIC_API_URL=`/api/v1` + openapi 경로도 `/api/v1` 접두) — mutator의 `buildUrl`이 base의 `/api/v1` 접미를 제거해 합성(중복 방지, 단위 테스트로 검증).

**테스트(thin slice, 결정 #6):** `@gosoom/api-client`에 Vitest(jsdom) 도입, 15 테스트 통과 — 인터셉터(401→refresh→재시도/비재귀/동시성 단일 refresh/에러 정규화/네트워크·비-JSON 폴백) + 토큰 스토어(메모리/localStorage 분리, SSR 가드).

**품질 게이트:** `pnpm typecheck`(6/6)·`pnpm lint`·`pnpm build`(user-web `/`·`/login`·`/signup` 정적 프리렌더)·`pnpm --filter @gosoom/api-client test`(15/15) 전부 통과. 백엔드 무변경 → pytest 회귀 0.

**KTH 수동 E2E 체크리스트(API+user-web 기동 후 — Task 9):**
1. `/signup`에서 customer·표시명·이메일·비밀번호 가입 → 성공 → `/login`(성공 메시지).
2. 같은 이메일 재가입 → 409 한국어 메시지.
3. `/login` 로그인 → 인증 후 홈, **displayName 표시**.
4. 잘못된 비밀번호 → 401 한국어 메시지.
5. 로그아웃 → `/login`, 보호 홈 재진입 시 가드가 `/login`으로.
6. (선택) access 폐기 후 요청 → 401→refresh→재요청 성공.

**KTH 선행 로컬 설정(체크포인트):** `apps/api/.env`의 `CORS_ORIGINS`에 `http://localhost:3000` 포함, `apps/user-web/.env.local`에 `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` 생성(dev는 `.env.local.example`만 커밋).

**검토자 참고(비차단 — 이 스토리 범위 밖, 후속 개선 후보):**
- **로그아웃 시 QueryClient 캐시 미정리:** `handleLogout`은 `clearTokens`+리다이렉트만 하고 `/users/me` 캐시는 남김 — 같은 탭에서 다른 계정으로 재로그인 시 이전 displayName이 잠깐 보일 수 있음(refetch 전). 후속에 `queryClient.clear()` 추가 검토(무상태 로그아웃 범위 밖).
- **`retry: 1`와 인증 실패 핸들러 중복 발화:** `/users/me` 401의 refresh 실패로 핸들러가 리다이렉트한 뒤, React Query가 1회 재시도하며 핸들러가 한 번 더 발화 가능(목적지 동일 — 무해). 인지만.
- **생성물 재현성 확인 완료:** 최종 orval.config(`indexFiles` 없음)로 재덤프·재생성 후 `generated/` 트리 동일 → 커밋 산출물 재현 가능(1.8 CI의 덤프→orval 단계 선검증).

### File List

**신규(NEW):**
- `packages/api-client/src/token-store.ts` — 토큰 스토어(access=메모리/refresh=localStorage)
- `packages/api-client/src/token-store.test.ts` — 토큰 스토어 단위(jsdom)
- `packages/api-client/src/token-store.ssr.test.ts` — SSR 가드 단위(node)
- `packages/api-client/src/client.test.ts` — apiClient mutator 단위(인터셉터/refresh/에러)
- `packages/api-client/vitest.config.ts` — Vitest 설정(jsdom)
- `packages/api-client/src/generated/**` — Orval 생성물(auth/users/categories/default 훅 + model 타입; 수정 금지, AR9)
- `apps/user-web/src/providers/Providers.tsx` — QueryClientProvider + 인증 실패 라우팅
- `apps/user-web/src/providers/AuthGuard.tsx` — 클라이언트 라우트 가드
- `apps/user-web/src/app/(auth)/signup/page.tsx` — 회원가입 화면
- `apps/user-web/src/app/(auth)/login/page.tsx` — 로그인 화면
- `apps/user-web/.env.local.example` — NEXT_PUBLIC_API_URL 예시

**수정(UPDATE):**
- `package.json` — devDep `orval@^7.21.0`
- `pnpm-workspace.yaml` — `@tanstack/react-query` 단일 핀(5.101.0) + esbuild 빌드 승인
- `orval.config.ts` — `operationName` 오버라이드(클린 훅명)
- `packages/api-client/package.json` — deps(react-query)·peer(react)·devDep(vitest/jsdom)·test 스크립트
- `packages/api-client/src/client.ts` — `apiClient` mutator(`resolveBaseUrl` 보존)
- `packages/api-client/src/index.ts` — generated barrel + token-store re-export
- `apps/user-web/package.json` — deps `@gosoom/api-client`·`@tanstack/react-query`
- `apps/user-web/next.config.ts` — transpilePackages에 `@gosoom/api-client`
- `apps/user-web/src/app/layout.tsx` — `lang="ko"`·metadata·Providers 래핑(폰트 보존)
- `apps/user-web/src/app/page.tsx` — 인증 후 홈(AuthGuard + useReadMe displayName + 로그아웃)
- `pnpm-lock.yaml` — 의존성 해소
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 1-7 상태 갱신

**비추적(gitignore — 커밋 안 함):** `openapi.json`(재생성 아티팩트, 결정 #1), `apps/user-web/.env.local`(KTH 생성)

### Change Log

| 날짜 | 변경 | 작성자 |
|------|------|--------|
| 2026-06-08 | Story 1.7 초안 생성 — 인증 UI(가입·로그인) + 4프리미티브 확립(Orval 파이프라인·apiClient 인터셉터·TanStack Provider/토큰 스토어·클라이언트 가드). Next16 proxy 변경·CORS 체크포인트·thin-slice 테스트 결정 반영. Status → ready-for-dev | create-story (Opus 4.8) |
| 2026-06-08 | KTH 결정 4건 확정(thin slice·로컬설정 KTH직접·가입후 /login) 반영. **결정 #1 변경: openapi.json 커밋→커밋 안 함**(재생성 아티팩트, 루트 .gitignore의 openapi.json 무시 유지 — 레포 작성자 의도와 정합, orval 직전 덤프, 1.8 CI에 덤프→orval 단계) | create-story (Opus 4.8) |
| 2026-06-08 | 구현 완료(Task 1~10) — Orval 파이프라인·apiClient mutator(401 refresh, 비재귀, 단일 in-flight)·TanStack Provider·토큰 스토어·클라이언트 가드(`useSyncExternalStore`)·가입/로그인/홈 화면. Vitest 15 통과, typecheck/lint/build 그린. 편차: orval `operationName` 오버라이드(클린 훅명, 백엔드 무변경)·mutator baseURL 중복 제거. Status → review | dev-story (Opus 4.8) |
| 2026-06-08 | 코드 리뷰(bmad-code-review, 3레이어 적대적 병렬) — patch 3·defer 2·dismiss 6. 헤드라인: 로그인 401 메시지 가림(AC3 위반, 3레이어 수렴). **patch 3건 모두 수정 적용**(client.ts: 공개엔드포인트 401 통과·재시도 재-401 대칭·options 스레딩) + 회귀 테스트 2건. typecheck/lint/build/test 17 그린. Status → done | code-review (Opus 4.8) |

## Review Findings

> 출처: bmad-code-review (2026-06-08) — Blind Hunter + Edge Case Hunter + Acceptance Auditor 3레이어 병렬. NO_VCS라 untracked intent-to-add diff(19파일·+1196) 기준, `generated/**`·lock·tracking 제외.

### Patch (3건 — 모두 수정 적용 ✅ 2026-06-08, typecheck/lint/build/test 17 통과)

- [x] [Review][Patch] **로그인/공개 엔드포인트 401을 세션만료로 오처리 → 백엔드 메시지 가림 + spurious 리다이렉트 (HIGH, AC3 위반, blind+auditor 수렴)** [packages/api-client/src/client.ts:216-231] — `apiClient`가 `/auth/refresh`만 제외하고 모든 401을 refresh 분기로 처리. 미로그인 상태 로그인 실패(401)는 refresh 토큰이 없어 `refreshAccessToken()`→null→`clearTokens()`+`authFailureHandler()`(불필요한 `/login` 리다이렉트)+하드코딩 `"세션이 만료되었습니다."` throw로 종료되어, `parseResponse`/`extractErrorMessage`(envelope `message` 우선, client.ts:155-169)에 도달하지 못함 → 백엔드의 "이메일 또는 비밀번호가 올바르지 않습니다." 소실. **수정 방향:** refresh 토큰이 없거나(또는 `/auth/login`·`/auth/signup` 공개 엔드포인트면) 세션만료 분기를 타지 않고 `parseResponse`로 통과시키면 envelope 메시지가 그대로 노출됨(3증상 동시 해소). 단위 테스트는 보호 엔드포인트(`/users/me`) 401만 검증해 이 케이스를 놓침 → 회귀 테스트(login 401) 추가 권장.

- [x] [Review][Patch] **refresh 성공 후 재시도가 다시 401이면 토큰 폐기·리다이렉트 누락 (비대칭) (MEDIUM, blind+edge+auditor 수렴)** [packages/api-client/src/client.ts:218-222] — refresh 성공 후 원요청 재시도 결과를 `parseResponse`로 바로 throw만 하고 `clearTokens()`/`authFailureHandler()`를 호출하지 않음. refresh-실패 경로(223-230)와 비대칭. 무한 루프는 없으나(retry-once 유지) 무효 세션이 정리되지 않아 매 요청 refresh→retry→401 반복. **수정 방향:** 재시도 응답이 401이면 refresh-실패 경로와 동일하게 `clearTokens()`+`authFailureHandler()` 후 throw.

- [x] [Review][Patch] **Orval `SecondParameter`(per-call request 옵션) 무시 → 호출부 헤더/RequestInit 미적용 (LOW, latent, blind)** [packages/api-client/src/client.ts:207-211] — 생성 훅이 `request?: SecondParameter<typeof apiClient>`를 `apiClient`의 2번째 인자(`_options`)로 전달(generated/auth/auth.ts:48·113·178 확인)하나 mutator가 이를 버림. 현재 호출부가 미사용이라 잠복이나, Epic 2~6 웹 화면이 상속할 공유 프리미티브의 정확성 결함. **수정 방향:** `_options`의 `headers`를 병합하고 나머지 RequestInit 필드를 `fetch`에 반영(mutator가 만드는 method/body/signal과 충돌 규칙 정의).

**수정 적용 내역 (client.ts):**
- Patch 1: `isRefreshCall`→`isAuthEndpoint`(refresh+**login+signup** 제외). 공개 인증 401은 세션만료 분기를 타지 않고 `parseResponse`로 통과 → envelope 메시지 노출. 보호 엔드포인트 동작은 보존(기존 테스트 "refresh 토큰 없음→리다이렉트" 유지). 회귀 테스트 추가(로그인 401 메시지·리다이렉트 없음).
- Patch 2: `failSession()` 헬퍼 추출 후 재시도 재-401에서도 호출 → refresh-실패 경로와 대칭(폐기+핸들러). 회귀 테스트 추가.
- Patch 3: `apiClient`가 `options`(SecondParameter)를 `sendRequest`로 스레딩, `headersToRecord`로 호출부 헤더 병합 + RequestInit 스프레드(method/headers/body/signal은 mutator 우선). 헤더는 plain Record 유지(테스트 계약 보존).

### Defer (연기 — deferred-work.md 기록)

- [x] [Review][Defer] **로그아웃 시 TanStack Query 캐시 미정리 → 이전 사용자 displayName(PII) 잠시 노출** [apps/user-web/src/app/page.tsx:handleLogout] — deferred (dev가 Completion Notes에서 이미 무상태 로그아웃 범위 밖으로 인지). 같은 탭 재로그인 시 refetch 전 이전 사용자 표시명 노출 가능. `queryClient.clear()` 추가는 후속.
- [x] [Review][Defer] **buildQuery 비-스칼라 파라미터 직렬화 깨짐 (현재 미도달, 공유 프리미티브)** [packages/api-client/src/client.ts:70-79] — deferred, latent. `String(value)`로 배열→`"a,b"`·객체→`"[object Object]"`. 현재 훅 파라미터는 스칼라(cursor/limit)뿐이라 도달 불가. Epic 2~6에서 배열/객체 쿼리 도입 시 반복 키 직렬화로 개선.

### Dismissed (노이즈/거짓양성 — 6건)

- refresh 응답 refreshToken 회전 미처리 → **기각**: 계약상 회전 없음(`RefreshResponse{accessToken만}`, Story 1.4 "회전 없음").
- refresh accessToken 공백 문자열(`" "`) 미검증 → **기각**: 계약 `access_token: str` 보장, 악성 프록시 한정 이론.
- 2xx 빈/비-JSON 본문 → undefined/raw 반환 → **기각**: 계약상 JSON 보장(UserRead 등), 프로젝트 "백엔드 신뢰" 방침.
- 로그인/가입 2xx 빈 본문 → 토큰 setter 무효값 → **기각**: 계약 `TokenResponse` 보장, 이론적.
- authFailureHandler 주입 전(useEffect 커밋 전) refresh 실패 시 full-page reload 폴백 → **기각**: 기본 폴백(`window.location`) 정상 동작, 경미 UX.
- Content-Type 헤더 존재 검사 대소문자 구분 → **기각**: 생성 훅이 소문자 헤더를 넘기지 않음(미도달).
