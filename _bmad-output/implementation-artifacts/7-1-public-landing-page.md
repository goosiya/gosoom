---
baseline_commit: "3e722a7"
---

# Story 7.1: 공개 메인 랜딩 화면

Status: done

> ⚠️ **Provenance:** 이 스토리는 정식 bmad 절차(create-story→dev-story→code-review)가 아니라
> KTH의 직접 요청으로 ad-hoc 구현된 뒤 사후 기록되었다. PRD FR1~24 범위 밖의 Post-MVP UX 개선(Epic 7).

## Story

As a 미인증 방문자,
I want user-web·mobile 진입 시 로그인 화면이 아니라 서비스를 소개하는 공개 랜딩을 보기를,
So that 서비스를 이해하고 로그인/회원가입을 선택할 수 있다.

## Acceptance Criteria

1. **AC1 — 공개 랜딩 노출:** 토큰이 없는 방문자가 user-web `/` 또는 mobile 루트(`/`)에 진입하면 로그인으로 리다이렉트되지 않고 공개 랜딩(히어로·기능 소개·역할 소개·CTA)이 표시된다. 로그인/회원가입 링크가 기존 인증 화면에 연결된다.

2. **AC2 — 인증 사용자 우회:** 이미 인증된 사용자가 랜딩(`/`)에 진입하면 역할별 홈으로 리다이렉트된다 — user-web은 `/dashboard`, mobile은 역할 그룹(`(customer)`/`(pro)`).

3. **AC3 — 반응형:** PC·모바일 각 화면 폭에서 적절한 레이아웃이 적용된다 — 데스크톱 2단 히어로, 모바일 단일 컬럼.

4. **AC4 — 브랜드 톤 비주얼:** 외부 이미지 에셋 없이 브랜드 컬러(`#1360F5`) 기반 장식(웹: SVG 점 격자+그라데이션 블롭, 모바일: 틴트 패널+장식 도형)과 앱 미리보기 목업으로 시각적 완성도를 갖춘다.

## Dev Notes

### 변경/추가 파일

**user-web**
- `src/app/page.tsx` — 기존 대시보드를 제거하고 공개 랜딩으로 교체. 인증 시 `/dashboard`로 리다이렉트(`useSyncExternalStore(isAuthenticated)`).
- `src/app/dashboard/page.tsx` — 기존 대시보드(역할별 퀵액션, AuthGuard)를 이곳으로 이동.
- `src/app/(auth)/login/page.tsx` · `(customer)/layout.tsx` · `(pro)/layout.tsx` — 리다이렉트 타깃 `/` → `/dashboard`.
- `src/components/AppHeader.tsx` — 로고 링크 `/dashboard`, `/`에서 헤더 숨김, **`useReadMe`를 `enabled: isAuthenticated()`로 게이트**.

**mobile**
- `src/app/index.tsx` — Expo 데모 화면을 공개 랜딩으로 교체.
- `src/app/_layout.tsx` — `AuthGate`가 미인증 사용자에게 랜딩(`pathname === '/'`)을 허용하고, 인증 사용자는 역할 그룹으로 리다이렉트하도록 수정.

### 핵심 버그 수정 (랜딩 진입 즉시 로그인 이동)

`AppHeader`의 `useReadMe`가 훅 규칙상 공개 페이지에서도 실행 → `/me` 401 → `failSession()` → 전역 `authFailureHandler`가 `/login`으로 강제 이동하던 문제를, 토큰이 있을 때만 쿼리하도록 `enabled: isAuthenticated()` + `queryKey: getReadMeQueryKey()`로 게이트하여 차단. (mobile `AuthContext`는 원래 `enabled: shouldFetchMe`로 이미 게이트되어 동일 문제 없음.)

### 제약 준수
- 공개 페이지에서 인증 API를 호출하지 않음(401 부작용 방지).
- 새 네이티브 의존성 추가 없음(mobile은 `@gosoom/ui` 토큰 + RN View 도형, `react-native-svg` 미사용).

## Completion Notes

- user-web / admin-web 영향 없는 라우팅 재배치 + mobile AuthGate 분기 수정으로 구현.
- 타입체크(tsc)·ESLint 통과.
- 정식 code-review 미수행(ad-hoc). 후속 회귀가 우려되면 `/bmad-code-review`로 별도 점검 권장.
