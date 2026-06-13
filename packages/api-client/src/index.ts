// @gosoom/api-client — 3개 클라이언트(user-web, admin-web, mobile) 공유 API 계층.
// Orval이 FastAPI openapi.json → src/generated/ 에 TS 타입 + TanStack Query 훅 생성(수정 금지, AR9).

// baseURL 해석 + 단일 인증 인터셉터 제어(로그인 시 핸들러 주입 등).
export { resolveBaseUrl, setAuthFailureHandler } from './client';
export type { ApiError, ApiRequestConfig } from './client';

// 토큰 스토어 — 로그인(토큰 저장)/로그아웃(clearTokens)/가드(isAuthenticated) 소비.
// setStorageBackend: 모바일 앱 부트 시 SecureStore 어댑터 주입(Story 5-1, AC3).
export {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isAuthenticated,
  setAccessToken,
  setRefreshToken,
  setStorageBackend,
} from './token-store';
export type { SyncStorageBackend } from './token-store';

// 비밀번호 규칙 검증(회원가입 폼 공유) — 백엔드 검증(schemas/auth.py)과 동일 규칙.
export {
  validatePassword,
  PASSWORD_MIN_LENGTH,
  PASSWORD_MAX_LENGTH,
  PASSWORD_RULE_HINT,
} from './validate-password';

// 생성된 TanStack Query 훅 + 모델 타입(useSignup/useLogin/useRefresh/useReadMe/useListCategories 등).
// orval tags-split는 루트 barrel을 만들지 않으므로 태그별 파일을 명시적으로 re-export(동결 API).
export * from './generated/auth/auth';
export * from './generated/users/users';
export * from './generated/categories/categories';
export * from './generated/service-requests/service-requests';
export * from './generated/pros/pros';
export * from './generated/quotes/quotes';
export * from './generated/chat-rooms/chat-rooms';
export * from './generated/default/default';
export * from './generated/admin/admin';
export * from './generated/model';
