// 비-API 공유 타입·상수 — 백엔드 도메인 enum의 프론트 미러.
// 라우트 가드(AR17)·UI 한국어 라벨·폼 검증에서 단일 출처로 사용한다.
// 권한 최종 시행은 서버이며, 여기 값은 UX 보조용 미러다.

/** 사용자 역할 (FR1/FR4) — admin은 자가 가입 불가 */
export const USER_ROLES = ['customer', 'pro', 'admin'] as const;
export type UserRole = (typeof USER_ROLES)[number];

/** 회원가입 가능한 역할 (admin 제외) */
export const SIGNUP_ROLES = ['customer', 'pro'] as const;
export type SignupRole = (typeof SIGNUP_ROLES)[number];

/** 서비스 요청 상태 기계 (FR7) */
export const REQUEST_STATUSES = ['open', 'matched', 'completed', 'cancelled'] as const;
export type RequestStatus = (typeof REQUEST_STATUSES)[number];

/** 견적 상태 기계 (FR12) */
export const QUOTE_STATUSES = ['pending', 'accepted', 'rejected', 'closed'] as const;
export type QuoteStatus = (typeof QUOTE_STATUSES)[number];

/** 상태 → 한국어 라벨 (NFR2) */
export const REQUEST_STATUS_LABELS: Record<RequestStatus, string> = {
  open: '대기중',
  matched: '매칭됨',
  completed: '완료',
  cancelled: '취소됨',
};

export const QUOTE_STATUS_LABELS: Record<QuoteStatus, string> = {
  pending: '검토중',
  accepted: '수락됨',
  rejected: '거절됨',
  closed: '마감됨',
};
