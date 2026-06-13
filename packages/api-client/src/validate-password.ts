// 비밀번호 규칙 검증 — 백엔드(apps/api/app/schemas/auth.py)의 SignupRequest 검증과 동일.
// 회원가입 폼(user-web, mobile)이 제출 전 클라이언트 측에서 동일 규칙을 적용해,
// 서버의 일반 422 메시지("요청 값이 올바르지 않습니다.") 대신 어떤 규칙이 어긋났는지 안내한다.
// ⚠️ 백엔드 규칙이 바뀌면 이 파일도 함께 갱신해야 한다(동일 규칙 유지).

/** 비밀번호 길이 하한(백엔드 min_length=8). */
export const PASSWORD_MIN_LENGTH = 8;
/** 비밀번호 길이 상한(백엔드 max_length=128). */
export const PASSWORD_MAX_LENGTH = 128;

/** 폼에서 보조 안내로 노출할 규칙 요약 문구. */
export const PASSWORD_RULE_HINT =
  '8자 이상, 대문자·소문자·숫자·특수문자를 각각 1자 이상 포함';

// 백엔드와 동일한 특수문자 집합.
const SPECIAL_CHAR_RE = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?`~]/;

/**
 * 비밀번호가 규칙을 위반하면 한국어 안내 메시지를, 통과하면 `null`을 반환한다.
 * 메시지 순서/문구는 백엔드 검증과 일치시켜 일관된 경험을 제공한다.
 */
export function validatePassword(password: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `비밀번호는 ${PASSWORD_MIN_LENGTH}자 이상이어야 합니다.`;
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    return `비밀번호는 ${PASSWORD_MAX_LENGTH}자 이하여야 합니다.`;
  }
  if (!/[A-Z]/.test(password)) {
    return '비밀번호에 대문자가 1자 이상 포함되어야 합니다.';
  }
  if (!/[a-z]/.test(password)) {
    return '비밀번호에 소문자가 1자 이상 포함되어야 합니다.';
  }
  if (!/\d/.test(password)) {
    return '비밀번호에 숫자가 1자 이상 포함되어야 합니다.';
  }
  if (!SPECIAL_CHAR_RE.test(password)) {
    return '비밀번호에 특수문자가 1자 이상 포함되어야 합니다.';
  }
  return null;
}
