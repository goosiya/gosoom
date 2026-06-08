import { defineConfig } from 'vitest/config';

// thin slice 테스트(결정 #6) — 인터셉터/토큰 스토어 핵심 로직만 단위 검증.
// jsdom: token-store의 localStorage·window 가드 검증에 필요(개별 파일은 node로 오버라이드 가능).
export default defineConfig({
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
  },
});
