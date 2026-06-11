import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isAuthenticated,
  setAccessToken,
  setRefreshToken,
  setStorageBackend,
  type SyncStorageBackend,
} from './token-store';

describe('token-store (jsdom)', () => {
  beforeEach(() => {
    clearTokens();
    // storageBackend를 null로 리셋 — window.localStorage 폴백 경로를 테스트한다.
    setStorageBackend(null);
  });

  it('access 토큰은 메모리에 저장/조회/해제된다', () => {
    expect(getAccessToken()).toBeNull();
    setAccessToken('access-1');
    expect(getAccessToken()).toBe('access-1');
    setAccessToken(null);
    expect(getAccessToken()).toBeNull();
  });

  it('refresh 토큰은 localStorage에 영속된다', () => {
    setRefreshToken('refresh-1');
    expect(window.localStorage.getItem('gosoom.refresh')).toBe('refresh-1');
    expect(getRefreshToken()).toBe('refresh-1');
    setRefreshToken(null);
    expect(window.localStorage.getItem('gosoom.refresh')).toBeNull();
  });

  it('access(메모리)와 refresh(localStorage)는 분리 저장된다', () => {
    setAccessToken('access-1');
    setRefreshToken('refresh-1');
    // access는 localStorage에 절대 들어가지 않는다.
    expect(window.localStorage.getItem('gosoom.refresh')).toBe('refresh-1');
    expect(window.localStorage.getItem('access')).toBeNull();
  });

  it('clearTokens는 access와 refresh를 모두 비운다', () => {
    setAccessToken('access-1');
    setRefreshToken('refresh-1');
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it('isAuthenticated: access 또는 refresh 중 하나라도 있으면 true', () => {
    expect(isAuthenticated()).toBe(false);

    setAccessToken('access-1');
    expect(isAuthenticated()).toBe(true);

    // 새로고침 시나리오: 메모리 access는 사라지고 refresh만 남아도 인증으로 간주(가드 통과).
    setAccessToken(null);
    setRefreshToken('refresh-1');
    expect(isAuthenticated()).toBe(true);
  });
});

describe('token-store — setStorageBackend (모바일 어댑터 주입)', () => {
  beforeEach(() => {
    clearTokens();
    // storageBackend를 null로 리셋 — 각 테스트가 독립적으로 모의 백엔드를 주입한다.
    setStorageBackend(null);
  });

  it('주입된 백엔드에 refresh 토큰이 읽고 쓰여진다', () => {
    const store: Record<string, string> = {};
    const mockBackend: SyncStorageBackend = {
      getItem: (key) => store[key] ?? null,
      setItem: (key, value) => { store[key] = value; },
      removeItem: (key) => { delete store[key]; },
    };
    setStorageBackend(mockBackend);

    setRefreshToken('mobile-refresh');
    expect(store['gosoom.refresh']).toBe('mobile-refresh');
    expect(getRefreshToken()).toBe('mobile-refresh');
    // localStorage에는 저장되지 않는다
    expect(window.localStorage.getItem('gosoom.refresh')).toBeNull();
  });

  it('주입된 백엔드에서 clearTokens가 refresh를 제거한다', () => {
    const store: Record<string, string> = {};
    const mockBackend: SyncStorageBackend = {
      getItem: (key) => store[key] ?? null,
      setItem: (key, value) => { store[key] = value; },
      removeItem: (key) => { delete store[key]; },
    };
    setStorageBackend(mockBackend);

    setRefreshToken('mobile-refresh');
    setAccessToken('mobile-access');
    clearTokens();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(store['gosoom.refresh']).toBeUndefined();
  });
});
