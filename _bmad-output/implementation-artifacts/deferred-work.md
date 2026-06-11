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

## Deferred from: code review of 2-2-my-requests-list-detail (2026-06-09)

- **ServiceRequestRead.status: str — OpenAPI enum 범위 미노출 (Low)** — `apps/api/app/schemas/service_request.py`의 status 필드가 `str`로 선언되어 OpenAPI 문서에 허용값(open/matched/completed/cancelled) enum이 누락됨. 기능 정상. API 문서화 개선 시 `ServiceRequestStatus` 타입으로 변경 검토.
- **desired_schedule·region 최대 길이 제한 없음 (Low)** — `apps/api/app/schemas/service_request.py`. DB `sa.String()` + Pydantic 스키마 모두 max_length 미설정. 현재 스펙 범위 외. 향후 데이터 품질 정책 수립 시 처리.
- **cursor base64 인코딩만, HMAC 서명 없음 (Low)** — `apps/api/app/core/pagination.py`. 커서 위변조 방지 없으나 `customer_id` 필터로 데이터 노출 차단. CategoryService와 동일 패턴 — 전체 cursor 보안 정책 검토 시 일괄 처리.
- **status 컬럼 DB 레벨 server_default 없음 (Low)** — `apps/api/alembic/versions/e447c8a3f9b7_add_service_requests_table.py`. ORM default만 설정(Python-side), DB 레벨 DEFAULT 없음. Raw SQL insert 시 NOT NULL 위반 가능. 현재 ORM 경유 전용이라 안전. 향후 직접 DB 접근 추가 시 서버 기본값 마이그레이션 검토.
- **상세 화면에서 categoryId UUID 원시값 표시 (Low)** — `apps/user-web/src/app/(customer)/requests/[id]/page.tsx`. 카테고리 이름 조회 API 미연동으로 UUID가 그대로 표시됨. Epic 3 카테고리-견적 기능 도입 시 카테고리명 표시로 개선.
- **updatedAt UI 미표시 (Low)** — `apps/user-web/src/app/(customer)/requests/[id]/page.tsx`. 상세 화면에 `createdAt`은 표시되나 `updatedAt` 누락. 스펙 AC4의 "등" 표현이 열려 있어 필수 아님. 향후 UI 정보 밀도 개선 시 추가.
- **keyset pagination 중 신규 요청 삽입 시 2페이지 누락 (Low)** — `apps/api/app/repositories/service_requests.py`. cursor 취득 후 신규 요청 생성 시 2페이지에서 해당 항목 skip됨. keyset pagination의 알려진 trade-off. 실시간 피드가 필요한 기능 추가 시 refresh 전략 검토.
- **UUID7 동일 밀리초 페이지네이션 불안정성 (Low)** — `apps/api/app/repositories/service_requests.py`. 동일 밀리초 내 복수 생성 시 랜덤 비트 기반 정렬. 테스트 환경에서 플래키니스 가능. created_at+id 복합 keyset으로 전환 검토(현재 CategoryService 패턴 일치).
- **cursor="" 빈 문자열 → 400 동작 미명세 (Low)** — `apps/api/app/services/service_request.py`. `?cursor=` 전송 시 UUID 파싱 실패로 400. 의도된 동작이나 OpenAPI 스펙에 명세 없음. API 문서화 개선 시 error response schema 추가.
- **타인 ID cursor 주입 → 데이터 누출 없으나 페이지 건너뜀 (Low)** — `apps/api/app/repositories/service_requests.py`. customer_id 필터로 데이터 보호 완료. 단, 악의적 cursor로 자신의 요청 목록에서 의도치 않은 항목 skip 가능. 실용적 위험 낮음. cursor 서명 도입 시 동시 해결.

## Deferred from: code review of 2-3-request-status-management (2026-06-09)

- **`ensure_owner_or_admin` ADMIN 우회가 서비스 계층에 잠재 (Low)** — `apps/api/app/core/authz.py:26`이 `UserRole.ADMIN`이면 소유권 검사 없이 통과. `change_status` 서비스 메서드에서 현재 `require_role(CUSTOMER)` 라우터 가드가 ADMIN을 403으로 막지만, 서비스 계층 자체는 ADMIN을 통과시키는 구조. 미래 ADMIN 전용 엔드포인트·내부 직접 호출 경로 추가 시 타인 요청 상태 변경 가능. 위치: `apps/api/app/core/authz.py:26`, `apps/api/app/services/service_request.py:99`. **사유:** Story 1.5에서 확립된 패턴(change_status 미도입). Epic 6 관리자 콘솔에서 상태 관리 정책이 결정될 때 서비스 계층 직접 소유권 검사로 전환 검토.
- **`ServiceRequestRepository.save()` `session.add()` 없는 암묵적 계약 (Low)** — `apps/api/app/repositories/service_requests.py:50-54`. `flush()`+`refresh(obj)` 전에 `session.add(obj)` 호출 없음. `change_status`에서 `get_by_id`로 로드된 이미 tracked 객체만 받으므로 현재 안전. 신규 생성 `ServiceRequest`를 `save()`에 직접 넘길 경우 INSERT 누락 또는 detached-instance error 위험. **사유:** 현재 호출 경로가 tracked 객체 전용이라 안전. 추가 호출자 도입 시 docstring 강화 또는 `session.add()` 포함으로 수정.
- **두 탭 동시 요청 race condition (Low)** — 두 브라우저 탭에서 같은 요청을 동시에 cancel 시도 시, 첫 번째 성공 후 두 번째가 409를 받아 사용자에게 "요청 처리 실패" 표시. 서버는 올바르게 처리하나 클라이언트 UX가 혼란스러움. `disabled={mutation.isPending}` 중복 클릭 방지는 같은 컴포넌트 인스턴스 내에서만 유효. **사유:** Epic 4(채팅/매칭) 이후 idempotency key 또는 낙관적 잠금 정책 수립 시 처리.
- **soft-deleted 요청 404 audit trail 없음 (Low)** — `get_by_id`가 `deleted_at IS NULL` 필터로 soft-deleted 레코드에 `None` 반환 → 404. 고객이 유효한 UUID를 가지고 있어도 "존재하지 않음"과 구별 불가. 관리자 진단·감사 로그 없음. **사유:** 현재 서비스 요청 소프트삭제 경로 없어 도달 불가능. Epic 6 관리자 콘솔 도입 시 audit log 정책과 함께 처리.

## Deferred from: code review of 3-1-pro-categories-setup (2026-06-09)

- **N+1 쿼리 — 카테고리 유효성 검증 단건 SELECT 반복 (Medium)** — `apps/api/app/services/pro_category.py:34-37`. `set_my_categories`가 `category_ids` 루프에서 `cat_repo.get_by_id`를 매번 호출. N개 ID = N번 SELECT. 기능 정확성에는 영향 없으나 카테고리 수 증가 시 레이턴시 선형 증가. `CategoryRepository.get_by_ids(list[UUID])` IN 쿼리 메서드 추가 후 일괄 검증으로 전환 필요. 성능 최적화 패스에서 처리.
- **동시 PUT 요청 last-writer-wins (Medium)** — `apps/api/app/repositories/pro_categories.py:26-38`. 동일 고수가 두 요청을 동시에 PUT 시 DELETE+INSERT 순서가 비결정론적으로 교차. 최종 상태 예측 불가. READ COMMITTED 기본 격리 수준. 현재 규모에서 발생 가능성 낮음. SELECT FOR UPDATE 또는 SERIALIZABLE 격리 도입 필요 시 처리.
- **AC4 fail-fast 검증 (Low)** — `apps/api/app/services/pro_category.py:33-37`. `[invalid1, invalid2]` 입력 시 첫 번째 invalid에서 즉시 raise, 나머지 미검증. 부분 삽입은 발생하지 않아 기능 무결성 유지. 모든 invalid ID를 한 번에 보고하는 UX 개선 시 전체 순회 후 일괄 raise 패턴으로 교체.
- **ProGuard 클라이언트사이드 역할 검사 (Low)** — `apps/user-web/src/app/(pro)/layout.tsx`. PRO 역할 검사가 클라이언트에서만 수행됨. 비PRO 사용자가 SSR로 URL에 직접 접근 가능(데이터는 API가 보호). (customer)/layout.tsx와 동일 패턴. Next.js middleware 기반 서버사이드 보호는 인증 아키텍처 정비 시 일괄 처리.

## Deferred from: code review of 2-1-create-service-request (2026-06-09)

## Deferred from: code review of 3-2-matched-requests-feed (2026-06-09)

- **completed/cancelled 요청 PRO 직접 URL 접근 가능 (Low)** — `apps/api/app/services/service_request.py:128-139`. `get_feed_detail()`은 상태 필터 없이 카테고리 일치만 검사. 피드 목록에서 노출되지 않는 completed/cancelled 요청도 URL 직접 접근 시 조회 가능. 스펙 개발자 노트가 "북마크/직접 링크 허용 목적"으로 의도적 설계로 명시. 상태 제한 정책 재검토 시 처리.
- **목록 페이지 cursor 페이지네이션 UI 없음 (Low)** — `apps/user-web/src/app/(pro)/feed/page.tsx`. 기본 20개 이상 요청 시 다음 페이지 로드 UI 없음. API는 cursor 지원하나 프론트엔드에서 미활용. 후속 UX 개선 스토리에서 infinite scroll 또는 "더 보기" 버튼 추가.
- **프론트엔드 AC5 렌더링 조건 분기 테스트 없음 (Low)** — `apps/user-web/src/app/(pro)/feed/`. open/matched 상태 분기 UI, 빈 목록 메시지, 상세 필드 표시 등 AC5 항목이 pytest 외부(E2E/RTL)로만 검증 가능. 현 프로젝트에 E2E 테스트 인프라 미도입. Playwright/RTL 도입 시 커버.

- **updated_at onupdate 없음 (Low)** — `apps/api/app/models/service_request.py` TimestampMixin이 `onupdate` 트리거 없이 `server_default=now()`만 설정. 레코드 수정 시 `updated_at`이 갱신되지 않음. 모든 ORM 모델에 걸친 pre-existing 이슈 — TimestampMixin 전체 개선 시 일괄 처리.
- **category_id 인덱스 없음 (Low)** — `apps/api/alembic/versions/e447c8a3f9b7_add_service_requests_table.py`. `customer_id`는 인덱스 있으나 `category_id`는 없음. "카테고리별 요청 목록" 등 쿼리가 도입되는 Story 2.2+ 시점에 추가 마이그레이션으로 처리.
- **region 자유 텍스트 데이터 품질 (Low)** — `apps/api/app/schemas/service_request.py:17`. 임의 문자열 허용. MVP 결정 — Epic 3+ 지역 기반 매칭 기능 도입 시 enum 또는 코드 테이블로 전환 검토.
- **ServiceRequestRepository.create StaleDataError 미처리 (Low)** — `apps/api/app/repositories/service_requests.py:20-25`. flush 성공 후 refresh에서 StaleDataError 발생 시 500 반환. 동시 삭제가 없는 현재 패턴에서는 도달 불가능.
- **Alembic downgrade get_bind() deprecated + checkfirst=False (Low)** — `apps/api/alembic/versions/e447c8a3f9b7_add_service_requests_table.py:51`. 프로젝트 전체 마이그레이션(1.3, 1.5 등)이 동일 패턴 사용 — 일관성 유지 후 전체 일괄 교체(`op.execute("DROP TYPE IF EXISTS ...")` 방식으로). 정상 upgrade/downgrade 경로는 안전.
- **pnpm typecheck/lint/build CI 미확인 (Low)** — dev agent 완료 노트에 로컬 통과 기록 있음. Railway CI 실행 결과 확인 필요.

## Deferred from: code review of 4-1-compare-quotes (2026-06-10)

- **SR 소프트 삭제 레이스 컨디션 (Low)** — `apps/api/app/services/quote.py:134`. `get_by_id` 소유권 검사 통과 후 다른 트랜잭션이 ServiceRequest를 소프트삭제하면 삭제된 SR의 견적 목록이 반환됨. 프로젝트 전체 read 엔드포인트의 공통 패턴 — 트랜잭션 격리 레벨(Repeatable Read) 정책 수립 시 일괄 처리.
- **matched 상태 전환 후 pending 견적 수락/거절 버튼 안내 없음 (Low)** — `apps/user-web/src/app/(customer)/requests/[id]/page.tsx:191`. `data.status === "open"` 조건으로 matched 이후 버튼 미노출은 AC6 스펙 범위 내. UX 개선(상태 안내 메시지)은 Story 4.2/4.3 배선 시 정리.
- **AC4 세 번째 이후 빈 페이지 cursor 동작 테스트 미비 (Low)** — `apps/api/tests/test_quotes_list_for_request.py`. 코드 로직은 정확하나 빈 페이지 cursor 직접 접근 시나리오 테스트 케이스 없음. 테스트 커버리지 보강 시 추가.
- **pro_ids set 순서 비결정성 (Low)** — `apps/api/app/services/quote.py:157`. `list({q.pro_id for q in page_rows})` set→list 변환으로 IN 쿼리 파라미터 순서 비결정. 기능 영향 없음. `list(dict.fromkeys(q.pro_id for q in page_rows))` 패턴으로 순서 보존 가능.

## Deferred from: code review of 4-2-accept-quote-create-chatroom (2026-06-10)

- **TOCTOU — quote 행 잠금 없음 (Low)** — `apps/api/app/services/quote.py:212-231`. quote는 FOR UPDATE 없이 조회되나, SR FOR UPDATE가 동일 SR에 대한 모든 동시 수락을 직렬화하므로 실질적 레이스 방지. partial index `uq_quotes_accepted_per_request`가 최종 방어. **사유:** SR FOR UPDATE로 충분히 직렬화됨; quote 행 추가 잠금은 오버헤드만 추가.
- **CANCELLED/COMPLETED 요청에 `service_request_already_matched` 반환 (Low)** — `apps/api/app/services/quote.py:226-227`. `status != OPEN` 일괄 조건으로 MATCHED뿐 아니라 CANCELLED/COMPLETED도 같은 오류 코드. **사유:** AC3 스펙이 matched 상태만 명시. 비-OPEN 포괄 처리로 기술적 수용 가능. 별도 오류 코드 필요 시 Epic 4 완결 후 정책 수립.
- **동시 수락 race condition 동시성 테스트 없음 (Low)** — `apps/api/tests/test_quotes_accept.py`. AC2 race 시나리오 테스트 미존재. **사유:** asyncio concurrent 테스트는 복잡하며 현 스토리 DoD 기준 외. 향후 동시성 테스트 프레임워크 도입 시 처리.
- **소프트삭제된 pro 사용자와의 채팅방 생성 가능 (Low)** — `apps/api/app/services/quote.py:237-242`. pro 사용자가 소프트삭제된 경우에도 채팅방이 생성됨. **사유:** 사용자 탈퇴 플로우가 Epic 6 범위. 탈퇴 구현 시 quote/chat_room 처리 정책과 함께 결정.
- **non-IntegrityError 발생 시 명시적 rollback 없음 (Low)** — `apps/api/app/services/quote.py:253-257`. try/except가 IntegrityError만 catch하며, OperationalError 등은 명시적 rollback 없이 상위로 전파. **사유:** FastAPI get_db 세션 dependency의 컨텍스트 매니저가 예외 시 rollback 처리. 일관성 개선 필요 시 전체 서비스 계층 예외 처리 정책 수립 시 일괄 처리.
- **AC5 `/chat/{chatRoomId}` 라우트 미구현 (Low)** — `apps/user-web/src/app/(customer)/requests/[id]/page.tsx:71`. 수락 성공 후 404 페이지 이동. **사유:** 스토리 개발자 노트에서 명시적 허용("404여도 라우팅 자체는 동작"). Story 4.4 채팅 화면 구현 시 해결.
- **AC5 채팅방 TanStack Query 캐시 무효화 누락 (Low)** — `apps/user-web/src/app/(customer)/requests/[id]/page.tsx:67-73`. onSuccess에서 채팅방 관련 쿼리 키 무효화 없음. **사유:** 채팅방 목록 API와 쿼리 훅이 Story 4.4에서 생성됨. 해당 스토리에서 캐시 무효화 추가.

## Deferred from: code review of 4-3-reject-quote (2026-06-11)

- **거절 실패 에러 코드별 메시지 미분기 (Low)** — `apps/user-web/src/app/(customer)/requests/[id]/page.tsx`. `rejectMutation.isError` 시 `"거절 처리에 실패했습니다."` 고정 문자열만 표시. 서버의 409(`quote_not_pending`)·403(`forbidden`)·404(`quote_not_found`) 구분 없음. API 에러 처리 아키텍처 정비(story 3-3 defer와 동일 패턴) 시 일괄 처리.
- **`ServiceRequestNotFoundError` 경로 미테스트 — orphan quote 시나리오 (Low)** — `apps/api/tests/test_quotes_reject.py`. `reject()` 2단계 `sr_repo.get_by_id() is None` 분기에 대한 테스트 케이스 없음. FK 제약 하에서 현재 도달 불가능. 소프트삭제 SR 정책 도입 시 테스트 추가.
- **소프트삭제 SR의 견적 거절 시 404 반환 정책 미문서화 (Low)** — SR이 소프트삭제된 경우 `sr_repo.get_by_id()`가 None 반환 → `ServiceRequestNotFoundError(404)`. 고객은 UI에서 "거절하기" 버튼이 보이지만 404를 받을 수 있음. SR 소프트삭제 경로 Epic 6 범위 — 탈퇴 처리 정책 수립 시 함께 결정.

## Deferred from: code review of 4-5-chatroom-list (2026-06-11)

- **React StrictMode 이중 실행 시 `processedCursors` 첫 페이지 유실 (Low)** — `apps/user-web/src/app/chat/page.tsx`. React StrictMode에서 Effect가 두 번 실행될 때 `processedCursors` ref에 cursor가 첫 실행에서 추가되어 두 번째 실행에서 데이터 처리가 건너뛰어짐. 개발 환경에서 첫 페이지가 비어 보일 수 있음. `(pro)/quotes/page.tsx` 와 동일 pre-existing 패턴 — quotes 페이지 개선 시 일괄 처리.
- **백그라운드 refetch 시 `processedCursors`가 최신 데이터 갱신 차단 (Low)** — `apps/user-web/src/app/chat/page.tsx`. TanStack Query 기본 staleTime=0 으로 포커스 복귀 시 refetch가 발생하나 동일 cursor가 Set에 있어 최신 데이터가 `allRooms`에 반영되지 않음. 스토리 노트에 "실시간 갱신 불필요" 명시된 의도적 트레이드오프. 채팅방 목록 실시간 갱신 요구사항 추가 시 재검토.
- **컴포넌트 unmount/remount 중 inflight fetch 경쟁 조건 (Low)** — `apps/user-web/src/app/chat/page.tsx`. 사용자가 페이지 이동 후 복귀 시 `processedCursors` ref가 초기화되어 이전 inflight 응답이 리마운트 후 도착하면 중복 처리 가능. 목록 페이지 특성상 실질적 사용자 영향 낮음. 상태관리 아키텍처 정비 시 처리.

## Deferred from: code review of 5-1-mobile-shell-auth (2026-06-11)

- **SecureStore 쓰기 실패 시 앱 재시작 후 세션 유실 (Low)** — `apps/mobile/src/features/auth/mobile-storage-backend.ts:14-16`. `setItem`/`removeItem`의 SecureStore 비동기 후기록이 `.catch(() => {})` 로 조용히 실패. 디바이스 잠금·하드웨어 오류 시 메모리 캐시에만 저장되고 영구 저장 실패. 앱 재시작 시 SecureStore에 값이 없어 세션 유실. MVP 범위에서 허용; 디바이스 수준 오류 재시도 또는 사용자 알림 정책 수립 시 처리.
- **`cache` 모듈 전역 변수 테스트 오염 가능 (Low)** — `apps/mobile/src/features/auth/mobile-storage-backend.ts:10`. `cache`가 모듈 싱글턴이라 단위 테스트에서 `mobileStorageBackend`를 직접 테스트할 경우 테스트 간 상태 누출. 현재 모바일 단위 테스트 미작성 — 테스트 추가 시 `cache` 초기화 수단(내보내기 또는 jest mock) 도입 검토.

## Deferred from: code review of 3-3-submit-quote (2026-06-09)

- **서비스 레이어 역할 미재검증 (Low)** — `apps/api/app/services/quote.py`. QuoteService.submit()이 라우터 계층의 `require_role(PRO)` 의존성에만 의존하고 서비스 내부에서 `current_user.user_role`을 재확인하지 않는다. 이는 프로젝트 전체 아키텍처 패턴(모든 서비스가 동일). 서비스 레이어를 직접 호출하는 경로가 추가될 경우 역할 검사 우회 가능. 전체 서비스 계층 역할 재검증 정책 수립 시 일괄 처리.
- **프론트 에러 메시지 원시 노출 (Low)** — `apps/user-web/src/app/(pro)/feed/[id]/page.tsx:104`. `(submitQuote.error as Error)?.message`를 직접 렌더링. api-client 인터셉터가 서버 응답 envelope의 message를 Error.message에 매핑하는 경우 안전하나, 미매핑 시 raw HTTP 에러 문자열이 노출될 수 있음. api-client 에러 처리 아키텍처 정비 시 처리.
- **status cancelled/closed 등 상태 UI 안내 없음 (Low)** — `apps/user-web/src/app/(pro)/feed/[id]/page.tsx`. open/matched 외 상태(cancelled, completed 등)일 때 아무 메시지도 표시되지 않음. 현재 피드 API가 이 상태들을 필터링하므로 실제 노출 불가. 피드 필터 정책 변경 또는 UX 개선 시 처리.
- **프론트 더블 제출 (Low)** — `apps/user-web/src/app/(pro)/feed/[id]/page.tsx`. isPending 전환 전 두 번째 클릭이 발생하면 두 번째 요청은 409 DuplicateQuoteError를 받아 에러 표시. 서버는 올바르게 처리하나 UX 혼란. 서버 보호로 데이터 무결성은 유지됨. 폼 제출 비활성화 UX 개선 시 처리.
- **downgrade checkfirst=False 멱등성 미보장 (Low)** — `apps/api/alembic/versions/d7bffeb07473_add_quotes_table.py:48`. `sa.Enum(name='quote_status').drop(..., checkfirst=False)` — enum 타입이 없는 상태에서 downgrade 재실행 시 ProgrammingError 발생. 프로젝트 전체 마이그레이션이 동일 패턴 사용 — 전체 일괄 교체(`op.execute("DROP TYPE IF EXISTS quote_status")` 방식) 시 처리. 정상 up→down 경로는 안전.
