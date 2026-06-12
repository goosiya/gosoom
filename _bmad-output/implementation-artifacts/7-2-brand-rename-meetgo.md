---
baseline_commit: "3e722a7"
---

# Story 7.2: 브랜드 표기 변경 (gosoom → meetgo)

Status: done

> ⚠️ **Provenance:** 정식 bmad 절차가 아니라 KTH 직접 요청으로 ad-hoc 구현 후 사후 기록. Post-MVP(Epic 7).

## Story

As a 운영자(KTH),
I want 화면에 노출되는 제품명을 `gosoom`에서 `meetgo`로 바꾸기를,
So that 변경된 브랜드 아이덴티티를 사용자에게 일관되게 전달한다.

## 배경

- 기존 `gosoom`은 "숨고"를 뒤집은 네이밍 → 영문 `meetgo`, 한글 "믿고"('믿는 고수' 의미)로 변경 결정.
- **화면 표기만 변경**하고 세팅·프로그램 요소의 `gosoom`은 그대로 둔다.

## Acceptance Criteria

1. **AC1 — 화면 표기 변경:** user-web·admin-web·mobile에서 브랜드명이 노출되는 모든 위치(로고·페이지 타이틀·히어로·푸터·CTA·메타데이터)가 `gosoom` → `meetgo`로 표시된다.

2. **AC2 — 코드/설정 식별자 보존:** 다음은 `gosoom`으로 유지된다 — `@gosoom/*` 패키지명·import, env 키(`SEED_ADMIN_*` 등), localStorage 키 `gosoom_quote_submitted_*`, SecureStore 키 `gosoom.refresh`, CSS 주석, `app.json`.

3. **AC3 — 빌드 안정성:** 표기 변경 후에도 세 앱이 타입체크를 통과하고, JS 변경만이라 네이티브 리빌드가 불필요하다(웹 재배포·모바일 OTA로 반영 가능).

## Dev Notes

### 변경된 화면 표기 (총 19곳)

- **user-web (7):** 랜딩 헤더 로고·히어로·CTA·푸터(로고+저작권), 로그인/회원가입 카드 브랜드, AppHeader 로고, `metadata.title`.
- **admin-web (6):** 로그인 카드, 대시보드 안내문, AdminHeader 로고 2곳, `metadata` title·description.
- **mobile (4):** 랜딩 로고·히어로, 로그인/회원가입 브랜드.

### 미변경(의도적 유지)
- localStorage `gosoom_quote_submitted_${id}` (`apps/user-web/.../feed/[id]/page.tsx`)
- SecureStore `gosoom.refresh` (`apps/mobile/.../mobile-storage-backend.ts`)
- CSS 브랜드 주석, `@gosoom/*` 워크스페이스·import, env, `app.json`.

### 한글 브랜드 "믿고"
- 코드에 한글 표기("고숨")가 존재하지 않아 치환 대상 없음 → 현재 "믿고"는 어느 화면에도 미노출.
- 필요 시 후속으로 로고 병기·메타 설명 등에 추가(별도 작업).

### 앱 이름/아이콘
- `app.json`의 `expo.name`(현재 `"mobile"`)·icon·splash는 미변경. 변경 시 네이티브 리빌드 필요하므로 KTH 결정 시 별도 처리.

## Completion Notes

- 세 앱 타입체크 통과. 화면 텍스트·메타데이터만 변경(JS), 리빌드 불필요.
- 브라우저 "유출된 비밀번호" 경고는 별개 이슈(약한 시드 비밀번호 `1234qwer`)로, 본 스토리와 무관.
