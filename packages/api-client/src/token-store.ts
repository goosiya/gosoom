// 토큰 스토어 — 인증 토큰의 단일 소스(결정 #4, AR10).
// - access: 메모리(모듈 변수, 휘발) — 새로고침 시 사라짐 → 인터셉터가 refresh로 재발급.
// - refresh: storageBackend(영속) — 웹=localStorage, 모바일=SecureStore 어댑터. 키: `gosoom.refresh`.
// SSR 안전: Next는 서버에서 모듈을 평가하므로 `window` 부재 시 localStorage 접근을 가드한다(함정 #9).
// 모바일 호환: React Native에서 window.localStorage는 undefined → setStorageBackend()로 교체(Story 5-1).

/** localStorage / SecureStore 어댑터가 구현해야 하는 동기 인터페이스. */
export interface SyncStorageBackend {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** refresh 토큰 키. 웹(localStorage)과 모바일(SecureStore) 모두 동일 키 사용. */
const REFRESH_STORAGE_KEY = 'gosoom.refresh';

/** access 토큰 — 메모리에만 보관(휘발). 모듈 단일 변수. */
let accessToken: string | null = null;

/** 주입된 스토리지 백엔드. 기본값 null → getStorage()가 window.localStorage로 폴백. */
let storageBackend: SyncStorageBackend | null = null;

/** 스토리지 백엔드 교체 — 모바일 앱 부트 시 SecureStore 어댑터를 주입한다. null이면 window.localStorage 폴백으로 복원. */
export function setStorageBackend(backend: SyncStorageBackend | null): void {
  storageBackend = backend;
}

/** 브라우저 환경(window 존재) 여부. SSR/Node에서는 false. */
function hasWindow(): boolean {
  return typeof window !== 'undefined';
}

/** 현재 유효한 스토리지 백엔드. 주입 백엔드 → window.localStorage → null 순. */
function getStorage(): SyncStorageBackend | null {
  if (storageBackend) return storageBackend;
  if (!hasWindow()) return null;
  try {
    if (typeof window.localStorage === 'undefined') return null;
    return window.localStorage;
  } catch {
    return null;
  }
}

/** 현재 access 토큰(없으면 null). */
export function getAccessToken(): string | null {
  return accessToken;
}

/** access 토큰 설정(null이면 비움). */
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/** 현재 refresh 토큰(스토리지 백엔드, SSR/오류 시 null). */
export function getRefreshToken(): string | null {
  const storage = getStorage();
  if (!storage) return null;
  try {
    return storage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    // 접근 불가(프라이빗 모드 등)는 미인증으로 간주.
    return null;
  }
}

/** refresh 토큰 설정(null이면 제거). 스토리지 없으면 no-op. */
export function setRefreshToken(token: string | null): void {
  const storage = getStorage();
  if (!storage) return;
  try {
    if (token === null) {
      storage.removeItem(REFRESH_STORAGE_KEY);
    } else {
      storage.setItem(REFRESH_STORAGE_KEY, token);
    }
  } catch {
    // 저장 실패는 조용히 무시(인증 흐름을 막지 않음).
  }
}

/** access(메모리) + refresh(스토리지) 모두 비움 — 로그아웃/인증 실패 시. */
export function clearTokens(): void {
  accessToken = null;
  setRefreshToken(null);
}

/**
 * 인증 가능성 여부 — access(메모리) 또는 refresh(스토리지) 중 하나라도 있으면 true.
 * 새로고침 직후엔 메모리 access가 사라지고 refresh만 남으므로 OR 조건이 핵심(가드가
 * 홈을 마운트시켜 인터셉터가 첫 401에서 refresh하도록 함, AC4/Task 4).
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null || getRefreshToken() !== null;
}
