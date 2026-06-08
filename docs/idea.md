아래 기능을 포함한 크로스 플랫폼 서비스의 핵심 기능 구축을 하려고 해.
최소 기능만 구현하려고 해.
한국의 "숨고"라는 서비스의 핵심 기능과 유사해.

- 기능 범위
  - 고객: 가입 > 로그인 > 서비스 요청 > 견적 확인 > 채팅
  - 고수: 가입 > 로그인 > 카테고리 설정 > 요청 확인 > 견적 제안 > 채팅
  - 관리자: 가입 > 로그인 > 고객 관리 / 고수 관리 / 관리자 관리 > 요청 관리 > 채팅 관리(내역 확인)
- 시연에 사용하는 기술 스택
  - 1. 사용자(고객/고수)용 반응형 웹(Next.js)
  - 2. 관리자용 반응형 웹(Next.js)
  - 3. 사용자(고객/고수)용 모바일 앱(React Native)
  - 4. 통합 API(FastAPI)
  - 5. DB (Supabase, PostgreSQL)
  - 6. 배포(Railway : 프론트엔드, 백엔드, PostgreSQL), 테스트(expo go)

- 참고 사항
Supabase로 database 개발을 먼저 하고, PostgreSQL(Railway)로 마이그레이션하여 마무리.
[1단게: Supabase 기반의 개발] -> [2단계: FastAPI 인프라를 Railway PostgreSQL로 완전히 독립시키는 이관] 흐름
Phase 1 (BaaS 기반): FastAPI와 Supabase(DB)를 연동해 빠른 기능 구현.
Phase 2 (인프라 독립): Supabase 의존성을 제거하고, Railway의 PostgreSQL로 DB 마이그레이션 및 인프라 최적화)