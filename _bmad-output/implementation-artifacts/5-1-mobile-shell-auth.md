---
baseline_commit: 4b8d9887f1c51ec31f667d85d06502c51f283d35
---

# Story 5.1: 모바일 셸 & 인증

Status: done

## Story

As a 고객·고수,
I want 모바일 앱에서 가입·로그인하고 세션이 안전하게 유지되기를,
so that 휴대폰에서 gosoom에 진입할 수 있다.

## Acceptance Criteria

1. **AC1 — 환경 설정 & 공유 패키지 로드:** `EXPO_PUBLIC_API_URL`(LAN IP 또는 배포 URL) 주입 후 앱 기동 시 공유 `@gosoom/api-client`와 `@gosoom/ui` 프리미티브가 모바일에서 정상 로드되고 API와 통신한다.

2. **AC2 — 가입 (FR1 재사용):** 가입 화면에서 역할(고객/고수) + 표시명 + 이메일 + 비밀번호를 입력하고 가입 시, `POST /api/v1/auth/signup`이 호출되어 완결되고 로그인 화면으로 이동한다.

3. **AC3 — 로그인 & 토큰 저장 (FR2 재사용):** 로그인 성공 시 `POST /api/v1/auth/login` 응답의 refresh 토큰은 **Expo SecureStore**에, access 토큰은 **메모리**에 보관된다. 앱 재시작 후에도 refresh 토큰이 SecureStore에서 복원되어 세션이 유지된다.

4. **AC4 — 토큰 갱신 (FR3 재사용):** access 토큰 만료(401) 시 api-client 인터셉터가 SecureStore의 refresh 토큰으로 `POST /api/v1/auth/refresh`를 1회 시도하고, 성공 시 원 요청을 재전송, 실패 시 로그아웃 처리된다.

5. **AC5 — 라우트 가드 (FR4 재사용):** 미인증 상태에서 보호 화면(고객/고수 영역) 접근 시 expo-router 가드가 로그인 화면으로 이동시킨다. 최종 권한은 서버가 검사한다.

6. **AC6 — 역할별 리다이렉트:** 로그인 후 역할에 따라 고객은 `/(customer)/requests`, 고수는 `/(pro)/feed`로 자동 이동한다.

7. **AC7 — 로그아웃:** 로그아웃 시 `clearTokens()` 호출 + SecureStore refresh 삭제 + 로그인 화면으로 이동한다.

## Tasks / Subtasks

> ⚡ **수동 설정 체크포인트 (AR23):** Task 1 착수 전 아래 항목을 먼저 사용자(KTH)가 직접 완료해야 한다.
> 1. [expo.dev](https://expo.dev) 계정 생성
> 2. 실기기에 **Expo Go** 앱 설치 (iOS App Store / Android Play Store)
> 3. PC의 **LAN IP** 확인: `ipconfig` (Windows) → IPv4 주소 (예: 192.168.1.10)
> 4. `.env` 파일에 `EXPO_PUBLIC_API_URL=http://<LAN_IP>:8000/api/v1` 설정
>    - 또는 배포된 Railway URL 사용 (`localhost` 불가 — Expo Go 실기기 제약)

- [x] Task 1 — packages/api-client 스토리지 어댑터 주입 지원 추가 (AC3, AC4)
  - [x] 1.1: `packages/api-client/src/token-store.ts`에 `SyncStorageBackend` 인터페이스 및 `setStorageBackend()` export 추가
  - [x] 1.2: 기존 localStorage 로직을 default backend로 유지 (웹 동작 회귀 없음)
  - [x] 1.3: `packages/api-client/src/index.ts`에 `setStorageBackend` export 추가
  - [x] 1.4: 기존 `packages/api-client` 테스트 전체 통과 확인 (`pnpm --filter @gosoom/api-client test`)

- [x] Task 2 — apps/mobile 의존성 추가 및 환경 설정 (AC1)
  - [x] 2.1: `apps/mobile/package.json`에 `expo-secure-store`, `@gosoom/api-client`, `@tanstack/react-query` 추가
  - [x] 2.2: `apps/mobile/app.json`의 `plugins` 배열에 `"expo-secure-store"` 추가
  - [x] 2.3: `apps/mobile/.env.example` 파일에 `EXPO_PUBLIC_API_URL=http://192.168.x.x:8000/api/v1` 예시 추가
  - [x] 2.4: `pnpm install` 실행 후 `pnpm --filter mobile typecheck` 통과 확인

- [x] Task 3 — 모바일 스토리지 어댑터 구현 (AC3, AC4)
  - [x] 3.1: `apps/mobile/src/features/auth/mobile-storage-backend.ts` 생성 — SecureStore 기반 동기 어댑터 + `hydrateMobileStorage()` 비동기 초기화 함수
  - [x] 3.2: 어댑터는 `SyncStorageBackend` 인터페이스 구현: `getItem` → 메모리 캐시 반환, `setItem/removeItem` → 메모리 캐시 즉시 + SecureStore 비동기 후기록

- [x] Task 4 — AuthContext 구현 (AC2~AC7)
  - [x] 4.1: `apps/mobile/src/features/auth/AuthContext.tsx` 생성 — `login`, `signup`, `logout`, `user`, `isLoading` 제공
  - [x] 4.2: `login` 성공 시: `setAccessToken(accessToken)` + `setRefreshToken(refreshToken)` 호출 (토큰 스토어 경유 → SecureStore에 자동 반영)
  - [x] 4.3: `logout` 시: `clearTokens()` + SecureStore `gosoom.refresh` 키 삭제 + expo-router `replace('/(auth)/login')`
  - [x] 4.4: `setAuthFailureHandler()` 등록 — 인터셉터 refresh 실패 시 expo-router `replace('/(auth)/login')` 호출
  - [x] 4.5: `apps/mobile/src/features/auth/index.ts` export 파일 생성

- [x] Task 5 — 루트 레이아웃 재구성 (AC1, AC5, AC6)
  - [x] 5.1: `apps/mobile/src/app/_layout.tsx` 업데이트 — `hydrateMobileStorage()` + `setStorageBackend()` 초기화를 앱 부트 시 수행
  - [x] 5.2: `QueryClientProvider` + `AuthProvider` 래핑 추가
  - [x] 5.3: 인증 상태에 따른 화면 분기: 미인증 → `(auth)` 그룹, 고객 → `(customer)` 그룹, 고수 → `(pro)` 그룹

- [x] Task 6 — 인증 화면 구현 (AC2, AC3)
  - [x] 6.1: `apps/mobile/src/app/(auth)/_layout.tsx` — 인증 그룹 레이아웃 (Stack 네비게이터)
  - [x] 6.2: `apps/mobile/src/app/(auth)/login.tsx` — 이메일·비밀번호 입력, `useLogin()` 훅 사용, 에러 메시지 표시
  - [x] 6.3: `apps/mobile/src/app/(auth)/signup.tsx` — 역할 선택(고객/고수) + 표시명 + 이메일 + 비밀번호, `useSignup()` 훅 사용
  - [x] 6.4: 로그인 화면에 "가입하기" 링크 (`/signup`), 가입 화면에 "로그인" 링크 (`/login`) 추가
  - [x] 6.5: 모든 에러 메시지 한국어 표시 (api-client `error.message` 활용)

- [x] Task 7 — 보호 레이아웃 구현 (AC5, AC6)
  - [x] 7.1: `apps/mobile/src/app/(customer)/_layout.tsx` — 고객 보호 레이아웃 (미인증 또는 역할 불일치 시 `/login` 리다이렉트)
  - [x] 7.2: `apps/mobile/src/app/(pro)/_layout.tsx` — 고수 보호 레이아웃 (동일 패턴)
  - [x] 7.3: 각 레이아웃에 플레이스홀더 화면(`/requests` index, `/feed` index) 추가 — Story 5.2/5.3에서 실제 구현

- [x] Task 8 — 타입체크 및 동작 확인
  - [x] 8.1: `pnpm --filter mobile typecheck` 통과
  - [x] 8.2: Expo Go로 실기기 실행 후 가입→로그인→보호 화면 이동→로그아웃 황금 경로 확인 (코드 구현 완료; 실기기 최종 확인은 KTH가 직접 수행)
  - [x] 8.3: 앱 강제 종료 후 재시작 시 SecureStore에서 세션 복원되는지 확인 — hydrateMobileStorage() 구현으로 처리 (KTH 직접 확인 필요)
  - [x] 8.4: 보호 화면 직접 진입 시 로그인 리다이렉트 확인 — AuthGate + Redirect 컴포넌트로 구현 (KTH 직접 확인 필요)

## Dev Notes

### 핵심 기술 도전: token-store.ts 모바일 호환성 문제 (반드시 읽을 것)

`packages/api-client/src/token-store.ts`는 `localStorage` 기반이다. React Native에서 `typeof window !== 'undefined'`는 `true`지만 `window.localStorage`는 `undefined`라서 try/catch가 모든 refresh 토큰 접근을 조용히 null 반환/무시한다. **수정 없이는 앱 재시작 시마다 세션이 사라진다.**

**필수 수정 — token-store.ts에 storage backend 주입 추가:**

```typescript
// packages/api-client/src/token-store.ts에 추가

export interface SyncStorageBackend {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** 기본값: localStorage (웹). 모바일은 앱 부트 시 setStorageBackend()로 교체한다. */
let storageBackend: SyncStorageBackend | null = null;

export function setStorageBackend(backend: SyncStorageBackend): void {
  storageBackend = backend;
}

/** localStorage 접근 시 storageBackend 우선, 없으면 window.localStorage 폴백 */
function getStorage(): SyncStorageBackend | null {
  if (storageBackend) return storageBackend;
  if (!hasWindow()) return null;
  try {
    // localStorage 접근 가능 여부 사전 확인
    if (typeof window.localStorage === 'undefined') return null;
    return window.localStorage;
  } catch {
    return null;
  }
}
// getRefreshToken, setRefreshToken, clearTokens의 localStorage 직접 접근을 getStorage() 경유로 교체
```

**모바일 어댑터 패턴 — 동기 메모리 캐시 + 비동기 SecureStore 후기록:**

```typescript
// apps/mobile/src/features/auth/mobile-storage-backend.ts
import * as SecureStore from 'expo-secure-store';
import type { SyncStorageBackend } from '@gosoom/api-client';

const cache: Record<string, string> = {};

export const mobileStorageBackend: SyncStorageBackend = {
  getItem: (key) => cache[key] ?? null,
  setItem: (key, value) => {
    cache[key] = value;
    SecureStore.setItemAsync(key, value).catch(() => {});
  },
  removeItem: (key) => {
    delete cache[key];
    SecureStore.deleteItemAsync(key).catch(() => {});
  },
};

/** 앱 시작 시 1회 호출 — SecureStore → 메모리 캐시 동기화 */
export async function hydrateMobileStorage(): Promise<void> {
  const refresh = await SecureStore.getItemAsync('gosoom.refresh');
  if (refresh) cache['gosoom.refresh'] = refresh;
}
```

**루트 레이아웃 초기화 순서 (엄격히 준수):**

```typescript
// apps/mobile/src/app/_layout.tsx
import { setStorageBackend } from '@gosoom/api-client';
import { hydrateMobileStorage, mobileStorageBackend } from '@/features/auth/mobile-storage-backend';

// 1. storage backend 등록 (동기 — 렌더 전에 반드시 먼저)
setStorageBackend(mobileStorageBackend);

// 2. SecureStore → 메모리 캐시 복원 (비동기 — SplashScreen 유지 중 수행)
// SplashScreen.preventAutoHideAsync()와 함께 사용
useEffect(() => {
  hydrateMobileStorage().then(() => {
    // 3. 복원 완료 후 AuthContext isLoading=false → 화면 분기
    SplashScreen.hideAsync();
  });
}, []);
```

**setAuthFailureHandler 등록 (refresh 실패 → expo-router 리다이렉트):**

```typescript
// apps/mobile/src/providers/Providers.tsx 또는 루트 레이아웃에서
import { setAuthFailureHandler } from '@gosoom/api-client';
import { router } from 'expo-router';

setAuthFailureHandler(() => {
  router.replace('/(auth)/login');
});
```

### 기존 코드 재사용 원칙 (절대 재발명 금지)

| 재사용 대상 | 위치 | Story 5-1에서의 역할 |
|-------------|------|---------------------|
| `useLogin` 훅 | `@gosoom/api-client` (Orval 자동생성) | 로그인 화면 |
| `useSignup` 훅 | `@gosoom/api-client` (Orval 자동생성) | 가입 화면 |
| `setAccessToken`, `setRefreshToken`, `clearTokens`, `isAuthenticated` | `@gosoom/api-client/src/token-store.ts` | AuthContext 토큰 관리 |
| `setAuthFailureHandler` | `@gosoom/api-client/src/client.ts` | refresh 실패 → 로그아웃 |
| `Button`, `Input`, `Card` | `@gosoom/ui` | 로그인·가입 폼 UI |
| `SignupRequest`, `LoginRequest`, `TokenResponse` | `@gosoom/api-client` (Orval 타입) | API 요청/응답 타입 |

**절대 직접 구현 금지:** `fetch('/api/v1/auth/login')` — 반드시 Orval 생성 `useLogin()` 훅 경유

### 웹(user-web)과의 인증 패턴 비교

```
웹 로그인 후:                        모바일 로그인 후:
setAccessToken(access)               setAccessToken(access)  // 동일
setRefreshToken(refresh)             setRefreshToken(refresh) // token-store → SecureStore 후기록
  → window.localStorage               → mobileStorageBackend.setItem()
  key: 'gosoom.refresh'               key: 'gosoom.refresh'  // 동일 키 사용
```

웹 `AuthGuard.tsx` 패턴 참고: `apps/user-web/src/providers/AuthGuard.tsx`
웹 `Providers.tsx` 패턴 참고: `apps/user-web/src/providers/Providers.tsx`

### expo-router 파일 구조

```
apps/mobile/src/app/
├── _layout.tsx              # ← 수정: QueryClientProvider + AuthProvider + hydration
├── (auth)/
│   ├── _layout.tsx          # ← 신규: Stack 레이아웃
│   ├── login.tsx            # ← 신규: 로그인 화면
│   └── signup.tsx           # ← 신규: 가입 화면
├── (customer)/
│   ├── _layout.tsx          # ← 신규: 고객 보호 레이아웃 + 탭 네비게이터
│   └── requests/
│       └── index.tsx        # ← 신규: 플레이스홀더 (Story 5.2에서 구현)
├── (pro)/
│   ├── _layout.tsx          # ← 신규: 고수 보호 레이아웃 + 탭 네비게이터
│   └── feed/
│       └── index.tsx        # ← 신규: 플레이스홀더 (Story 5.3에서 구현)
└── +not-found.tsx           # ← 유지
```

**기존 유지 파일:** `explore.tsx`, `index.tsx`, `src/components/`, `src/constants/`, `src/hooks/` — **건드리지 않는다.**

### package.json에 추가할 의존성

```json
{
  "dependencies": {
    "@gosoom/api-client": "workspace:*",
    "@tanstack/react-query": "^5.0.0",
    "expo-secure-store": "~14.0.1"
  }
}
```

> `expo-secure-store` 버전: Expo SDK 55와 호환되는 `~14.0.1` 사용. `expo install expo-secure-store` 명령이 자동으로 적합한 버전을 선택한다.

### app.json 플러그인 추가

```json
{
  "expo": {
    "plugins": [
      "expo-secure-store"
    ]
  }
}
```

### 스타일링 규칙 (NativeWind + tokens.ts)

- NativeWind `className` prop 사용 (`style` prop 대신)
- 브랜드 색상: `packages/ui/src/tokens.ts` 참조 (primary, border, muted, destructive 등)
- 한국어 텍스트: 에러 메시지는 api-client `error.message` 그대로 표시 (이미 한국어)
- 폼 레이아웃: `SafeAreaView` + `KeyboardAvoidingView` 필수 (iOS 키보드 가림 방지)

### AuthContext 인터페이스

```typescript
interface AuthContextValue {
  user: { id: string; role: 'customer' | 'pro'; displayName: string } | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName: string, role: 'customer' | 'pro') => Promise<void>;
  logout: () => Promise<void>;
}
```

`user` 정보는 `useReadMe()` 훅으로 로그인 후 조회한다 (`@gosoom/api-client`에서 export됨).

### 에러 처리 패턴 (웹과 동일)

```typescript
// useLogin 훅 사용 예시
const { mutate: loginMutate, isPending } = useLogin();
loginMutate(
  { data: { email, password } },
  {
    onSuccess: (data) => {
      setAccessToken(data.accessToken);
      setRefreshToken(data.refreshToken);
      // user 정보 조회 후 역할별 리다이렉트
    },
    onError: (error) => setErrorMessage(error.message), // 한국어 메시지
  }
);
```

웹 참고: `apps/user-web/src/app/(auth)/login/page.tsx`

### Project Structure Notes

- `apps/mobile/src/app/` — expo-router 파일 라우팅 루트 (아키텍처 `apps/mobile/app/` 표기와 동일, 현재 실제 경로는 `src/app/`)
- `apps/mobile/src/features/auth/` — 신규 생성 (웹의 `apps/user-web/src/features/auth/`와 동일 도메인 구조)
- `packages/api-client/src/token-store.ts` — **수정 필수** (Story 5-1의 유일한 공유 패키지 변경)
- `packages/api-client/src/index.ts` — `setStorageBackend` re-export 추가 필요

### References

- [Source: epics.md#Story 5.1] — 유저 스토리, AC 전문
- [Source: architecture.md#L186-189] — Bearer 통일, Expo SecureStore, api-client 웹/모바일 분기 없음
- [Source: architecture.md#L230-234] — 모바일 디자인 시스템, NativeWind 세팅, tokens.ts
- [Source: architecture.md#L216-217] — EXPO_PUBLIC_API_URL, localhost 불가 제약
- [Source: packages/api-client/src/token-store.ts] — 현재 localStorage 구현 전문
- [Source: packages/api-client/src/client.ts#L17-21] — resolveBaseUrl() EXPO_PUBLIC_API_URL 지원 확인
- [Source: packages/api-client/src/client.ts#L47-56] — setAuthFailureHandler() 기본값(window.location)
- [Source: apps/user-web/src/providers/Providers.tsx] — setAuthFailureHandler + QueryClient 세팅 참고
- [Source: apps/user-web/src/providers/AuthGuard.tsx] — 라우트 가드 패턴 참고
- [Source: apps/user-web/src/app/(auth)/login/page.tsx] — useLogin 훅 사용 패턴 참고
- [Source: apps/mobile/package.json] — 현재 의존성 전체 목록

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- `packages/api-client/src/token-store.ts`: React Native에서 `window.localStorage`는 undefined → `SyncStorageBackend` 인터페이스 + `setStorageBackend()` 주입 패턴으로 해결
- `apps/mobile/.expo/types/router.d.ts`: `typedRoutes: true` 환경에서 새 라우트(`(auth)`, `(customer)`, `(pro)`) 타입이 누락 → 수동 업데이트 (Expo dev server 실행 시 자동 재생성됨)
- `useReadMe` queryKey: TanStack Query v5 `UseQueryOptions`가 `queryKey`를 필수로 요구 → `getReadMeQueryKey()` 명시 전달로 해결
- `UserRead.userRole`: API 응답 필드명은 `userRole` (not `role`) — `AuthContext`에서 `meData.userRole`로 매핑

### Completion Notes List

- **Task 1**: `packages/api-client/src/token-store.ts`에 `SyncStorageBackend` 인터페이스와 `setStorageBackend()` 함수 추가. 기존 localStorage 폴백 로직 유지로 웹 회귀 없음. 새 테스트 2개 추가(총 19개 통과)
- **Task 2**: `apps/mobile/package.json`에 `@gosoom/api-client`, `expo-secure-store`, `@tanstack/react-query` 추가. `app.json` 플러그인, `.env.example` 생성
- **Task 3**: `apps/mobile/src/features/auth/mobile-storage-backend.ts` — 동기 메모리 캐시 + SecureStore 비동기 후기록 어댑터. `hydrateMobileStorage()`로 앱 시작 시 복원
- **Task 4**: `AuthContext.tsx` — `isHydrated` prop으로 수화 완료 시점 수신 후 세션 복원 시도. `setAuthFailureHandler`로 refresh 실패 시 자동 로그아웃
- **Task 5**: `_layout.tsx` 전면 재구성 — `setStorageBackend` 동기 등록, `hydrateMobileStorage` 비동기 수화, `QueryClientProvider` + `AuthProvider` 래핑, `AuthGate`로 역할별 라우팅
- **Task 6**: `(auth)/login.tsx`, `(auth)/signup.tsx` — `@gosoom/ui` 토큰 기반 스타일링, 한국어 에러 메시지, expo-router `Link` 연결
- **Task 7**: `(customer)/_layout.tsx`, `(pro)/_layout.tsx` — `Redirect` 컴포넌트 기반 보호 레이아웃. 플레이스홀더 화면 포함
- **Task 8**: 타입체크 통과. 실기기 검증(8.2-8.4)은 KTH가 Expo Go로 직접 수행 필요

### File List

packages/api-client/src/token-store.ts
packages/api-client/src/index.ts
packages/api-client/src/token-store.test.ts
apps/mobile/package.json
apps/mobile/app.json
apps/mobile/.env.example
apps/mobile/.expo/types/router.d.ts
apps/mobile/src/app/_layout.tsx
apps/mobile/src/app/(auth)/_layout.tsx
apps/mobile/src/app/(auth)/login.tsx
apps/mobile/src/app/(auth)/signup.tsx
apps/mobile/src/app/(customer)/_layout.tsx
apps/mobile/src/app/(customer)/requests/index.tsx
apps/mobile/src/app/(pro)/_layout.tsx
apps/mobile/src/app/(pro)/feed/index.tsx
apps/mobile/src/features/auth/AuthContext.tsx
apps/mobile/src/features/auth/mobile-storage-backend.ts
apps/mobile/src/features/auth/index.ts

### Review Findings

- [x] [Review][Patch] hydrateMobileStorage 오류 시 isHydrated 미설정 → 앱 무한 로딩 [apps/mobile/src/app/_layout.tsx]
- [x] [Review][Patch] 로그아웃 시 SecureStore 이중 삭제 race condition [apps/mobile/src/features/auth/AuthContext.tsx:119-125]
- [x] [Review][Patch] 재로그인 시 이전 /me 캐시 stale 트리거 [apps/mobile/src/features/auth/AuthContext.tsx:70-87]
- [x] [Review][Patch] meData.userRole 비표준 값 미검증 캐스팅 [apps/mobile/src/features/auth/AuthContext.tsx:74]
- [x] [Review][Patch] isLoading 중 null 반환 → 스플래시 해제 후 흰 화면 [apps/mobile/src/app/_layout.tsx:53]
- [x] [Review][Patch] setAuthFailureHandler 언마운트 cleanup 누락 [apps/mobile/src/features/auth/AuthContext.tsx:90-97]
- [x] [Review][Patch] beforeEach storageBackend 리셋 불완전 — null 대신 localStorage 주입 [packages/api-client/src/token-store.test.ts]
- [x] [Review][Defer] SecureStore 쓰기 실패 시 재시작 후 세션 유실 [apps/mobile/src/features/auth/mobile-storage-backend.ts:14-16] — deferred, pre-existing device-level limitation
- [x] [Review][Defer] cache 모듈 전역 변수 — 테스트 환경 오염 가능 [apps/mobile/src/features/auth/mobile-storage-backend.ts:10] — deferred, test infrastructure

## Change Log

- 2026-06-11: Story 5-1 구현 완료 — packages/api-client SyncStorageBackend 주입 지원, 모바일 SecureStore 어댑터, AuthContext(세션 복원/로그인/로그아웃), 루트 레이아웃 재구성(AuthGate), 인증 화면(로그인/가입), 보호 레이아웃(고객/고수) 구현
