// @vitest-environment node
// SSR(서버 평가) 시나리오: window/localStorage 부재 가드 검증(함정 #9).
import { beforeEach, describe, expect, it } from 'vitest';

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isAuthenticated,
  setAccessToken,
  setRefreshToken,
} from './token-store';

describe('token-store (SSR / window 부재)', () => {
  beforeEach(() => {
    clearTokens();
  });

  it('window가 없으면 refresh 접근은 null/no-op이며 throw하지 않는다', () => {
    expect(typeof window).toBe('undefined');
    expect(getRefreshToken()).toBeNull();
    expect(() => setRefreshToken('refresh-1')).not.toThrow();
    // 저장소가 없으므로 값은 유지되지 않는다.
    expect(getRefreshToken()).toBeNull();
  });

  it('access(메모리)는 window 없이도 동작한다', () => {
    setAccessToken('access-1');
    expect(getAccessToken()).toBe('access-1');
    expect(isAuthenticated()).toBe(true);
  });
});
