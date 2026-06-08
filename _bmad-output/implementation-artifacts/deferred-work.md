# Deferred Work

프로젝트 진행 중 의도적으로 연기된 작업 항목. 각 항목은 출처(어느 리뷰/스토리)와 연기 사유를 포함한다.

## Deferred from: code review of 1-3-signup-seed-admin (2026-06-08)

- **소프트삭제 이메일 재가입 불가 (HIGH)** — `get_by_email`은 `deleted_at IS NULL`로 거르지만 `ix_users_email` 유니크 인덱스는 삭제행을 포함한 전체 범위. 소프트삭제된 이메일은 선검사를 통과(None)한 뒤 insert가 유니크 제약을 위반→오해 소지 있는 409로 영영 재가입 불가. 위치: `apps/api/app/models/user.py:39`, `repositories/users.py:get_by_email`, `alembic/versions/04c24a1c717d_add_users_table.py`. **사유:** Story 1.3엔 삭제 경로가 없어 현재 도달 불가능. 삭제 플로우(Epic 6 계정관리)가 들어올 때 partial 유니크 인덱스(`WHERE deleted_at IS NULL`) 채택 여부와 함께 결정. (연관: 시드 IntegrityError 가드 patch가 이 경로의 방어선)
- **과도한 IntegrityError→DuplicateEmailError 매핑 (Low)** — `services/auth.py:234`가 모든 IntegrityError를 409 중복 이메일로 변환. 현재 users의 유일 제약이 email 유니크라 정상 동작. **사유:** 두 번째 유니크/CHECK/FK 제약이 추가될 때 제약명 검사로 분기하도록 개선(현재는 잠복).
- **CORS credentialed-wildcard 풋건 (Low)** — `apps/api/app/main.py`의 `allow_credentials=True` + `allow_methods/headers=["*"]`. `CORS_ORIGINS`에 `*`가 설정되면 자격증명+와일드카드 오설정. **사유:** CORS는 Story 1.2에서 확립된 코드(본 스토리 미도입). 자격증명 활성 시 `*` 거부 validator는 후속 보안 정비 항목.
- **Alembic downgrade enum drop `checkfirst=False` (Low)** — `alembic/versions/04c24a1c717d:393`. 타입이 이미 없는 부분 다운그레이드 상태에서 다운그레이드가 실패. **사유:** up→down→up 멱등 체인은 검증 통과(정상 경로 안전), 손상 상태 전용 엣지케이스. 낮은 우선순위.

## Deferred from: code review of 1-5-rbac (2026-06-08)

- **health 엔드포인트 좁은 예외 포착 (Low)** — `apps/api/app/main.py:109`의 `except SQLAlchemyError`만 503으로 변환. 드라이버 소켓 OSError/ConnectionError·asyncio.TimeoutError·미래핑 DBAPI 오류는 전역 Exception 핸들러로 새어 500(문서·헬스 계약상 503·`{"db":"fail"}` 기대와 불일치). **사유:** Story 1.1 health 코드(1.5 미도입). 헬스/리브니스 계약 정비 시 `except Exception`으로 광역화 검토.
- **verify_password 광역 예외 흡수 (Low)** — `apps/api/app/core/security.py:53` `except Exception: return False`. 손상/비-Argon2 해시(UnknownHashError) 방어 목적이나 None·비-str 인자·OOM 등 프로그래밍 버그도 "인증 거부"로 은폐(fail-closed라 우회 위험은 없음). **사유:** Story 1.3/1.4 의도적 설계. 해시 컬럼 타입 버그 등을 일반 로그인 실패 뒤에 숨길 수 있어, 진단성 개선이 필요하면 예외 종류 분기 검토.
- **ensure_owner_or_admin str-vs-UUID 호출 계약 위험 (Low/잠복)** — `apps/api/app/core/authz.py:28` `current_user.id != resource_owner_id`. 현재 in-slice는 UUID-vs-UUID로 건전(현재 호출자 없음). 향후 Epic 2/3/4 service가 `resource_owner_id`를 문자열로 넘기면 `UUID != str`가 항상 True → 정당 소유자가 403(admin은 통과해 admin 테스트에선 은폐). **사유:** 1.5는 헬퍼·패턴만 확립(첫 실사용 Epic 2 이후). 배선 시점에 타입 강제/런타임 코어션 enforce.

## Deferred from: code review of 1-6-categories-api-seed (2026-06-08)

- **시드 충돌 안전성: 비-partial unique index (Critical/High — Blind Hunter·Edge Case Hunter 둘 다 평가, 의도적 보류)** — `apps/api/alembic/versions/4b715631d65e_add_categories_table.py`의 `name` unique 인덱스가 전역(non-partial)인데 `apps/api/app/repositories/categories.py`의 `get_by_name`은 `deleted_at IS NULL`로 필터한다. 소프트삭제된 동명 카테고리 행이 잔존하면 `seed_categories`(`apps/api/app/seed.py:79-107`)의 선검사가 `None`을 반환 → insert → 전역 unique 위반 → IntegrityError→ValueError→`sys.exit(1)`로 **시드 영구 차단(AC2 멱등성 위배)**. 동시 실행 시에도 배치 단일 commit이 한 충돌에 정상 신규분까지 전부 롤백하고, 멱등 skip이 아니라 실패로 끝난다. **사유:** 스펙 Dev Notes(line 282)가 1.3 email-unique 선례와 동일하게 명시적으로 보류한 사항. `categories` 테이블은 이 마이그레이션에서 처음 생성되고 1.6 범위에 카테고리 소프트삭제 경로가 없어 **현재 도달 불가**(트리거 조건이 코드상 발생 불가). Epic 6(카테고리 삭제/비활성화 FR24) 도입 시 partial unique 인덱스(`postgresql_where=text("deleted_at IS NULL")`) 채택 + 동시성은 ON CONFLICT DO NOTHING 검토. ⚠️ NO_VCS(아직 커밋 없음)라 마이그레이션이 어디에도 적용되지 않은 상태 — 지금 partial로 바꾸면 거의 무비용이므로, 보류 유지 여부는 KTH 판단.

## Deferred from: code review of 1-7-auth-ui-api-client (2026-06-08)

- **로그아웃 시 TanStack Query 캐시 미정리 → 이전 사용자 PII 잠시 노출 (Medium — Blind Hunter)** — `apps/user-web/src/app/page.tsx`의 `handleLogout`이 `clearTokens()`+`router.replace('/login')`만 하고 `/users/me`(useReadMe) 캐시는 남김. 같은 탭에서 다른 계정 재로그인 시 새 fetch 전 이전 사용자 `displayName`이 잠깐 보일 수 있음(공유 단말 정보 누출). **사유:** dev가 Completion Notes에서 이미 "무상태 로그아웃 범위 밖"으로 명시 인지. `queryClient.clear()`/`removeQueries` 추가는 후속(인증 상태관리 정비 시).
- **buildQuery 비-스칼라 파라미터 직렬화 깨짐 (Low/잠복 — Blind Hunter)** — `packages/api-client/src/client.ts:70-79`의 `search.append(key, String(value))`는 배열을 `"a,b"`(반복 키 아님)·객체를 `"[object Object]"`로 직렬화. **사유:** 현재 Orval 훅 파라미터는 스칼라(cursor/limit)뿐이라 도달 불가능. Epic 2~6 도메인 화면이 배열/객체 쿼리(목록 필터 등)를 도입하는 시점에 반복 키(`?tags=a&tags=b`) 직렬화로 개선. 공유 프리미티브라 그때 모든 화면이 영향받음.

## Deferred from: code review of 1-8-ci-deploy-skeleton (2026-06-08)

- **CI `JWT_SECRET` 평문 하드코딩 (Low)** — `ci.yml:25`의 `JWT_SECRET: ci-test-secret-not-for-prod`가 레포에 평문 커밋됨. CI 전용 테스트 값이고 로컬 Postgres 컨테이너 대상이라 실제 서비스 영향은 없음. 공개 레포로 전환 시 GitHub Secrets(`${{ secrets.CI_JWT_SECRET }}`)로 분리 검토. 현재 private 레포 전제로 허용.
- **`turbo`에 `test` 태스크 없어 향후 패키지 테스트 자동화 누락 가능 (Low)** — `pnpm --filter @gosoom/api-client test`를 `--filter`로 직접 호출하는 방식은 의도적(turbo.json test 태스크 미정의). 향후 `packages/ui`·`packages/types` 등에 Vitest가 추가될 때 ci.yml 수동 추가 또는 turbo `test` 태스크 도입 검토.
- **Railway release command 실패 시 부분 마이그레이션 위험 (Medium)** — `alembic upgrade head`가 마이그레이션 중간에 실패하면 Railway가 롤백을 보장하지 않아 DB 상태와 코드 불일치 가능. MVP 단계에서 마이그레이션 수가 적어 발생 가능성 낮음. Alembic 트랜잭션 마이그레이션 패턴 준수로 완화. Phase 2 이후 마이그레이션 복잡도 증가 시 배포 전략 재검토.
- **GitHub Actions 액션 SHA 미고정 supply chain 표면 (Low)** — `actions/checkout@v4` 등 major tag 사용. MVP 범위 결정. 보안 요구사항 강화 시 SHA 고정 검토(`uses: actions/checkout@<sha>`).
- **`.dockerignore`에 `alembic/` 미제외 (Low)** — `tests/`는 제외됐으나 `alembic/versions/` 마이그레이션 파일이 이미지에 포함됨. 기능 영향 없음. 이미지 슬림화가 필요할 때 추가.
