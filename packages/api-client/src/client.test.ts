import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient, setAuthFailureHandler } from './client';
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from './token-store';

const PROTECTED_URL = '/api/v1/users/me';
const SIGNUP_URL = '/api/v1/auth/signup';
const LOGIN_URL = '/api/v1/auth/login';
const REFRESH_SUFFIX = '/api/v1/auth/refresh';

interface RecordedCall {
  url: string;
  authorization: string | null;
}

/** Response를 모방하는 경량 객체(전역 Response 의존 회피). text()/json() 모두 제공. */
function fakeResponse(status: number, body?: unknown): Response {
  const serialized = body === undefined ? '' : JSON.stringify(body);
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => serialized,
    json: async () => (body === undefined ? undefined : JSON.parse(serialized)),
  } as unknown as Response;
}

function fakeTextResponse(status: number, text: string): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => text,
  } as unknown as Response;
}

/**
 * 현실적 fetch mock: 보호 엔드포인트는 `Bearer new-access`면 200, 아니면 401을 돌려준다.
 * refresh 엔드포인트는 옵션에 따라 성공(새 access)/실패(401)를 돌려준다.
 * → "오래된 access로 401 → refresh로 새 access → 재시도 200" 실제 흐름을 재현한다.
 */
function installRealisticFetch(options: { refreshSucceeds: boolean }) {
  const calls: RecordedCall[] = [];
  const fetchMock = vi.fn(
    async (input: unknown, init?: { headers?: Record<string, string> }) => {
      const url = String(input);
      const authorization = init?.headers?.['Authorization'] ?? null;
      calls.push({ url, authorization });

      if (url.endsWith(REFRESH_SUFFIX)) {
        return options.refreshSucceeds
          ? fakeResponse(200, { accessToken: 'new-access', tokenType: 'bearer' })
          : fakeResponse(401, { code: 'invalid_token', message: '만료된 토큰' });
      }

      if (authorization === 'Bearer new-access') {
        return fakeResponse(200, { id: 'u1', displayName: '홍길동' });
      }
      return fakeResponse(401, { code: 'unauthorized', message: '인증이 필요합니다.' });
    },
  );
  vi.stubGlobal('fetch', fetchMock);
  return { calls, fetchMock };
}

function refreshCalls(calls: RecordedCall[]): RecordedCall[] {
  return calls.filter((c) => c.url.endsWith(REFRESH_SUFFIX));
}

function protectedCalls(calls: RecordedCall[]): RecordedCall[] {
  return calls.filter((c) => c.url.endsWith('/users/me'));
}

describe('apiClient mutator', () => {
  beforeEach(() => {
    clearTokens();
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/api/v1';
    // 테스트가 실제 페이지 이동을 일으키지 않도록 인증 실패 핸들러를 기본 no-op로.
    setAuthFailureHandler(() => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('성공 요청: 현재 access를 Authorization: Bearer로 부착하고 데이터를 반환한다', async () => {
    setAccessToken('new-access');
    const { fetchMock } = installRealisticFetch({ refreshSucceeds: true });

    const result = await apiClient<{ id: string; displayName: string }>({
      url: PROTECTED_URL,
      method: 'GET',
    });

    expect(result).toEqual({ id: 'u1', displayName: '홍길동' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const init = fetchMock.mock.calls[0]?.[1] as { headers: Record<string, string> };
    expect(init.headers['Authorization']).toBe('Bearer new-access');
    // baseURL(/api/v1)과 경로(/api/v1/...)가 중복되지 않는다.
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe(
      'http://localhost:8000/api/v1/users/me',
    );
  });

  it('401 → refresh 1회 → 원요청 재시도 성공', async () => {
    setAccessToken('old-access');
    setRefreshToken('refresh-token');
    const { calls } = installRealisticFetch({ refreshSucceeds: true });

    const result = await apiClient<{ id: string }>({
      url: PROTECTED_URL,
      method: 'GET',
    });

    expect(result).toEqual({ id: 'u1', displayName: '홍길동' });
    // refresh는 정확히 1회.
    expect(refreshCalls(calls)).toHaveLength(1);
    // 원요청은 2회(최초 401 + 재시도).
    expect(protectedCalls(calls)).toHaveLength(2);
    // 새 access가 스토어에 저장됨.
    expect(getAccessToken()).toBe('new-access');
  });

  it('refresh 실패(401) → 토큰 폐기 + 로그인 핸들러 호출 + 비재귀(refresh 1회로 종료)', async () => {
    setAccessToken('old-access');
    setRefreshToken('refresh-token');
    const authFailure = vi.fn();
    setAuthFailureHandler(authFailure);
    const { calls } = installRealisticFetch({ refreshSucceeds: false });

    await expect(
      apiClient({ url: PROTECTED_URL, method: 'GET' }),
    ).rejects.toThrowError(/세션이 만료/);

    // 핵심: refresh가 다시 refresh를 부르는 무한 루프가 없다 — 정확히 1회.
    expect(refreshCalls(calls)).toHaveLength(1);
    expect(authFailure).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it('동시 401 다발: refresh를 1회만 수행하고 모든 요청이 재시도 성공', async () => {
    setAccessToken('old-access');
    setRefreshToken('refresh-token');
    const { calls } = installRealisticFetch({ refreshSucceeds: true });

    const [r1, r2, r3] = await Promise.all([
      apiClient<{ id: string }>({ url: PROTECTED_URL, method: 'GET' }),
      apiClient<{ id: string }>({ url: PROTECTED_URL, method: 'GET' }),
      apiClient<{ id: string }>({ url: PROTECTED_URL, method: 'GET' }),
    ]);

    expect(r1).toEqual({ id: 'u1', displayName: '홍길동' });
    expect(r2).toEqual({ id: 'u1', displayName: '홍길동' });
    expect(r3).toEqual({ id: 'u1', displayName: '홍길동' });
    // 동시 401 3건이어도 refresh는 단일 in-flight로 1회만.
    expect(refreshCalls(calls)).toHaveLength(1);
  });

  it('에러 정규화: 비-2xx envelope의 message(한국어)를 error.message로 throw', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        fakeResponse(409, {
          code: 'duplicate_email',
          message: '이미 가입된 이메일입니다.',
        }),
      ),
    );

    const error = await apiClient({
      url: SIGNUP_URL,
      method: 'POST',
      data: { email: 'a@b.com' },
    }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(Error);
    expect((error as Error).message).toBe('이미 가입된 이메일입니다.');
    expect((error as { status?: number }).status).toBe(409);
    expect((error as { code?: string }).code).toBe('duplicate_email');
  });

  it('네트워크 오류: fetch 거부 시 한국어 폴백 메시지로 throw', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      }),
    );

    await expect(
      apiClient({ url: PROTECTED_URL, method: 'GET' }),
    ).rejects.toThrowError(/서버에 연결할 수 없습니다/);
  });

  it('비-JSON 오류 본문(500): 상태 기반 한국어 폴백 메시지', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => fakeTextResponse(500, 'Internal Server Error')),
    );

    await expect(
      apiClient({ url: PROTECTED_URL, method: 'GET' }),
    ).rejects.toThrowError(/서버 오류/);
  });

  it('refresh 토큰이 없으면 401에서 곧바로 인증 실패(refresh 시도 안 함)', async () => {
    setAccessToken('old-access');
    // refresh 토큰 없음
    const authFailure = vi.fn();
    setAuthFailureHandler(authFailure);
    const { calls } = installRealisticFetch({ refreshSucceeds: true });

    await expect(
      apiClient({ url: PROTECTED_URL, method: 'GET' }),
    ).rejects.toThrowError(/세션이 만료/);

    // refresh 토큰이 없으므로 refresh fetch 자체가 일어나지 않는다.
    expect(refreshCalls(calls)).toHaveLength(0);
    expect(authFailure).toHaveBeenCalledTimes(1);
  });

  it('로그인 401(잘못된 자격증명): 세션만료로 가로채지 않고 백엔드 메시지 노출(리다이렉트 없음)', async () => {
    // 미로그인 상태 — access/refresh 모두 없음.
    const authFailure = vi.fn();
    setAuthFailureHandler(authFailure);
    const calls: { url: string }[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: unknown) => {
        const url = String(input);
        calls.push({ url });
        return fakeResponse(401, {
          code: 'invalid_credentials',
          message: '이메일 또는 비밀번호가 올바르지 않습니다.',
        });
      }),
    );

    const error = await apiClient({
      url: LOGIN_URL,
      method: 'POST',
      data: { email: 'a@b.com', password: 'wrong' },
    }).catch((e: unknown) => e);

    // 공개 엔드포인트의 401은 envelope message를 그대로 노출(AC3).
    expect((error as Error).message).toBe(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    );
    expect((error as { status?: number }).status).toBe(401);
    // 공개 엔드포인트라 refresh 시도/리다이렉트가 없어야 한다.
    expect(authFailure).not.toHaveBeenCalled();
    expect(calls.filter((c) => c.url.endsWith(REFRESH_SUFFIX))).toHaveLength(0);
  });

  it('refresh 성공 후 재시도가 다시 401: 세션 종료(폐기+핸들러) — 비대칭 방지·무한루프 없음', async () => {
    setAccessToken('old-access');
    setRefreshToken('refresh-token');
    const authFailure = vi.fn();
    setAuthFailureHandler(authFailure);
    const calls: RecordedCall[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async (input: unknown, init?: { headers?: Record<string, string> }) => {
          const url = String(input);
          const authorization = init?.headers?.['Authorization'] ?? null;
          calls.push({ url, authorization });
          if (url.endsWith(REFRESH_SUFFIX)) {
            return fakeResponse(200, {
              accessToken: 'new-access',
              tokenType: 'bearer',
            });
          }
          // 보호 엔드포인트는 새 access로도 계속 401(권한 박탈/즉시 만료 시나리오).
          return fakeResponse(401, {
            code: 'unauthorized',
            message: '인증이 필요합니다.',
          });
        },
      ),
    );

    await expect(
      apiClient({ url: PROTECTED_URL, method: 'GET' }),
    ).rejects.toThrowError(/세션이 만료/);

    // refresh 1회, 원요청 2회(최초+재시도)로 종료 — 무한 루프 없음.
    expect(refreshCalls(calls)).toHaveLength(1);
    expect(protectedCalls(calls)).toHaveLength(2);
    // 재시도 재-401도 refresh-실패와 동일하게 세션 종료.
    expect(authFailure).toHaveBeenCalledTimes(1);
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });
});
