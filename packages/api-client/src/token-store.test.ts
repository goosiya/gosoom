import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isAuthenticated,
  setAccessToken,
  setRefreshToken,
} from './token-store';

describe('token-store (jsdom)', () => {
  beforeEach(() => {
    clearTokens();
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
