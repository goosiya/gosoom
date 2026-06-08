// API 클라이언트 베이스 + 단일 인증 인터셉터 (AR10/AR18).
// Orval 생성 훅이 이 모듈의 `apiClient`(mutator, orval.config 배선)를 통해 모든 요청을 보낸다.
// 3대 불변식(결정 #2):
//   ① 토큰 스토어 단일 소스(access=메모리, refresh=localStorage) — token-store.ts
//   ② 401 → refresh 1회 → 원요청 1회 재시도
//   ③ refresh 호출은 인터셉터를 재귀하지 않는다(직접 fetch) — 무한 루프 금지(함정 #5)
// fetch 기반(axios 강제 아님). 반환 타입만 맞추면 구현 자유.

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
} from './token-store';

/** 환경에서 API 베이스 URL을 해석한다. 웹/모바일 모두 *_PUBLIC_API_URL 규약. */
export function resolveBaseUrl(): string {
  const fromEnv =
    process.env.NEXT_PUBLIC_API_URL ?? process.env.EXPO_PUBLIC_API_URL ?? '';
  return fromEnv || 'http://localhost:8000/api/v1';
}

/** Orval 생성 훅이 mutator를 호출할 때 넘기는 요청 설정. */
export interface ApiRequestConfig {
  url: string;
  method: string;
  params?: Record<string, unknown>;
  data?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  responseType?: string;
}

/** mutator가 throw하는 정규화된 에러 — TanStack Query `error.message`로 한국어 노출(AC3). */
export interface ApiError extends Error {
  status?: number;
  code?: string;
}

/** refresh 엔드포인트 절대 경로(openapi 경로 규약과 동일 — buildUrl이 origin과 합성). */
const REFRESH_PATH = '/api/v1/auth/refresh';

/**
 * 인증 실패(refresh 불가) 시 호출되는 핸들러. 기본은 로그인 리다이렉트.
 * 테스트/커스텀 라우팅을 위해 주입 가능(예: providers에서 router.replace 연결).
 */
let authFailureHandler: () => void = () => {
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
};

/** 인증 실패 핸들러 교체(기본: window.location → '/login'). */
export function setAuthFailureHandler(handler: () => void): void {
  authFailureHandler = handler;
}

/**
 * baseURL과 openapi 경로를 합성한다.
 * openapi 경로는 이미 `/api/v1` 접두를 포함(`/api/v1/auth/signup` 등)하므로,
 * baseURL이 `/api/v1`로 끝나면 중복을 제거한 origin에 합성한다(경로 중복 방지).
 */
function buildUrl(path: string): string {
  const base = resolveBaseUrl().replace(/\/+$/, '');
  const origin = base.replace(/\/api\/v1$/, '');
  return origin + path;
}

/** params 객체를 쿼리스트링으로(빈/undefined 값 제외). */
function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return '';
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    search.append(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : '';
}

/** RequestInit.headers(Headers/배열/Record)를 plain Record로 정규화. */
function headersToRecord(headers: HeadersInit | undefined): Record<string, string> {
  if (!headers) return {};
  if (headers instanceof Headers) {
    const record: Record<string, string> = {};
    headers.forEach((value, key) => {
      record[key] = value;
    });
    return record;
  }
  if (Array.isArray(headers)) {
    return Object.fromEntries(headers);
  }
  return { ...headers };
}

/**
 * 단일 요청 수행 — 현재 access 토큰을 Bearer로 부착. (refresh 분기 없음 — 순수 전송)
 * `options`는 Orval `SecondParameter`(호출부별 RequestInit) — 헤더/credentials 등을 병합한다.
 */
async function sendRequest(
  config: ApiRequestConfig,
  options?: RequestInit,
): Promise<Response> {
  const url = buildUrl(config.url) + buildQuery(config.params);
  // 호출부 옵션 헤더 → config 헤더 순 병합(인증/Content-Type는 이후 적용해 우선).
  const headers: Record<string, string> = {
    ...headersToRecord(options?.headers),
    ...(config.headers ?? {}),
  };

  const access = getAccessToken();
  if (access) {
    headers['Authorization'] = `Bearer ${access}`;
  }

  const hasBody = config.data !== undefined && config.data !== null;
  if (hasBody && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    return await fetch(url, {
      // 호출부 RequestInit(credentials/mode/cache 등) — 아래 필드가 우선 적용된다.
      ...options,
      method: config.method.toUpperCase(),
      headers,
      body: hasBody ? JSON.stringify(config.data) : undefined,
      signal: config.signal ?? options?.signal,
    });
  } catch (error) {
    // 요청 취소(AbortError)는 그대로 전파(TanStack Query 취소 처리).
    if (error instanceof Error && error.name === 'AbortError') {
      throw error;
    }
    // 네트워크 실패 등 → 한국어 폴백 메시지(AC3).
    const networkError = new Error(
      '서버에 연결할 수 없습니다. 네트워크 상태를 확인해 주세요.',
    ) as ApiError;
    throw networkError;
  }
}

// ── refresh: 단일 in-flight 공유(동시 401 다발 시 1회만 수행, 결정 #2) ──
let inflightRefresh: Promise<string | null> | null = null;

/**
 * refresh 토큰으로 새 access를 1회 발급한다(비재귀 — fetch 직접 호출, 인터셉터 우회).
 * 성공 시 새 access를 스토어에 저장하고 반환, 실패 시 null.
 * 동시 호출은 단일 in-flight promise를 공유해 중복 refresh를 막는다.
 */
function refreshAccessToken(): Promise<string | null> {
  if (inflightRefresh) return inflightRefresh;

  inflightRefresh = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      // ⚠️ 인터셉터(apiClient)를 거치지 않는 직접 fetch — refresh-401이 다시 refresh를
      //    유발하는 무한 재귀를 원천 차단(함정 #5). Bearer도 부착하지 않는다.
      const response = await fetch(buildUrl(REFRESH_PATH), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });
      if (!response.ok) return null;
      const body = (await response.json()) as { accessToken?: string };
      if (!body.accessToken) return null;
      setAccessToken(body.accessToken);
      return body.accessToken;
    } catch {
      return null;
    }
  })();

  // in-flight를 settle 후 해제 — 다음 만료 주기엔 새 refresh를 시작.
  return inflightRefresh.finally(() => {
    inflightRefresh = null;
  });
}

/** 비-2xx 응답에서 표준 envelope `message`를 추출하거나 상태 기반 한국어 폴백. */
function extractErrorMessage(body: unknown, status: number): string {
  if (
    body !== null &&
    typeof body === 'object' &&
    'message' in body &&
    typeof (body as { message: unknown }).message === 'string'
  ) {
    return (body as { message: string }).message;
  }
  if (status === 401) return '인증에 실패했습니다. 다시 로그인해 주세요.';
  if (status === 403) return '접근 권한이 없습니다.';
  if (status === 404) return '요청한 항목을 찾을 수 없습니다.';
  if (status >= 500) return '서버 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.';
  return '요청을 처리할 수 없습니다.';
}

/** Response를 파싱해 데이터를 반환하거나, 비-2xx면 정규화된 ApiError를 throw. */
async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let body: unknown = undefined;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!response.ok) {
    const error = new Error(
      extractErrorMessage(body, response.status),
    ) as ApiError;
    error.status = response.status;
    if (body !== null && typeof body === 'object' && 'code' in body) {
      const code = (body as { code: unknown }).code;
      if (typeof code === 'string') error.code = code;
    }
    throw error;
  }

  return body as T;
}

/** 세션 종료 — 토큰 폐기 + 로그인 유도 후 정규화된 401 에러를 throw(절대 정상 반환 안 함). */
function failSession(): never {
  clearTokens();
  authFailureHandler();
  const error = new Error(
    '세션이 만료되었습니다. 다시 로그인해 주세요.',
  ) as ApiError;
  error.status = 401;
  throw error;
}

/**
 * Orval mutator — 모든 요청의 단일 진입점(AR10).
 * 흐름: access 부착 전송 → 401(공개 인증 엔드포인트 제외)이면 refresh 1회 → 성공 시 원요청
 *       1회 재시도, 실패(또는 재시도 재-401) 시 토큰 폐기 + 로그인 유도 후 에러 throw.
 */
export const apiClient = async <T>(
  config: ApiRequestConfig,
  // Orval `SecondParameter<typeof apiClient>` — 호출부별 RequestInit(헤더/credentials 등).
  options?: RequestInit,
): Promise<T> => {
  // 공개/자격증명 엔드포인트(가입·로그인·refresh)의 401은 "세션 만료"가 아니라 정상적인
  // 인증 실패(잘못된 자격증명 등) → 인터셉터가 가로채지 않고 parseResponse로 통과시켜
  // 백엔드 envelope 메시지를 그대로 노출한다(AC3). refresh 시도·spurious 리다이렉트 없음.
  const isAuthEndpoint =
    config.url.includes('/auth/refresh') ||
    config.url.includes('/auth/login') ||
    config.url.includes('/auth/signup');

  const response = await sendRequest(config, options);

  if (response.status === 401 && !isAuthEndpoint) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      // 새 access로 원요청 1회 재시도(sendRequest가 스토어의 최신 access를 읽음).
      const retried = await sendRequest(config, options);
      // 재시도가 다시 401이면 refresh-실패와 동일하게 세션 종료(비대칭 방지).
      if (retried.status === 401) {
        failSession();
      }
      return parseResponse<T>(retried);
    }
    // refresh 불가 → 세션 종료: 토큰 폐기 + 로그인 유도.
    failSession();
  }

  return parseResponse<T>(response);
};
