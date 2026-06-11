import * as SecureStore from 'expo-secure-store';

import type { SyncStorageBackend } from '@gosoom/api-client';

// 동기 메모리 캐시 + 비동기 SecureStore 후기록 패턴.
// token-store.ts는 동기 인터페이스만 지원하므로 getItem은 메모리 캐시에서 즉시 반환하고,
// setItem/removeItem은 캐시를 즉시 갱신한 뒤 SecureStore에 비동기로 반영한다.
export const REFRESH_SECURE_KEY = 'gosoom.refresh';

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

/** 앱 시작 시 1회 호출 — SecureStore의 refresh 토큰을 메모리 캐시로 복원한다. */
export async function hydrateMobileStorage(): Promise<void> {
  const refresh = await SecureStore.getItemAsync(REFRESH_SECURE_KEY);
  if (refresh) cache[REFRESH_SECURE_KEY] = refresh;
}
