// 토큰 스토어 — 인증 토큰의 단일 소스(결정 #4, AR10).
// - access: 메모리(모듈 변수, 휘발) — 새로고침 시 사라짐 → 인터셉터가 refresh로 재발급.
// - refresh: localStorage(영속) — 새로고침을 넘어 세션 유지. 키: `gosoom.refresh`.
// SSR 안전: Next는 서버에서 모듈을 평가하므로 `window` 부재 시 localStorage 접근을 가드한다(함정 #9).

/** localStorage refresh 토큰 키. */
const REFRESH_STORAGE_KEY = 'gosoom.refresh';

/** access 토큰 — 메모리에만 보관(휘발). 모듈 단일 변수. */
let accessToken: string | null = null;

/** 브라우저 환경(window 존재) 여부. SSR/Node에서는 false. */
function hasWindow(): boolean {
  return typeof window !== 'undefined';
}

/** 현재 access 토큰(없으면 null). */
export function getAccessToken(): string | null {
  return accessToken;
}

/** access 토큰 설정(null이면 비움). */
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/** 현재 refresh 토큰(localStorage, SSR/오류 시 null). */
export function getRefreshToken(): string | null {
  if (!hasWindow()) return null;
  try {
    return window.localStorage.getItem(REFRESH_STORAGE_KEY);
  } catch {
    // localStorage 접근 불가(프라이빗 모드 등)는 미인증으로 간주.
    return null;
  }
}

/** refresh 토큰 설정(null이면 제거). SSR/오류 시 no-op. */
export function setRefreshToken(token: string | null): void {
  if (!hasWindow()) return;
  try {
    if (token === null) {
      window.localStorage.removeItem(REFRESH_STORAGE_KEY);
    } else {
      window.localStorage.setItem(REFRESH_STORAGE_KEY, token);
    }
  } catch {
    // 저장 실패는 조용히 무시(인증 흐름을 막지 않음).
  }
}

/** access(메모리) + refresh(localStorage) 모두 비움 — 로그아웃/인증 실패 시. */
export function clearTokens(): void {
  accessToken = null;
  setRefreshToken(null);
}

/**
 * 인증 가능성 여부 — access(메모리) 또는 refresh(localStorage) 중 하나라도 있으면 true.
 * 새로고침 직후엔 메모리 access가 사라지고 refresh만 남으므로 OR 조건이 핵심(가드가
 * 홈을 마운트시켜 인터셉터가 첫 401에서 refresh하도록 함, AC4/Task 4).
 */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null || getRefreshToken() !== null;
}
