// Orval 설정 — FastAPI openapi.json → packages/api-client 자동 생성 (AR9).
// Story 1.7에서 활성화: apps/api 기동 후 openapi.json을 내려받아 input으로 지정하고
// `pnpm orval`로 TS 타입 + TanStack Query 훅을 packages/api-client/src/generated 에 생성한다.
// 생성물은 빌드 아티팩트 — 수동 수정 금지.
import { defineConfig } from 'orval';

export default defineConfig({
  gosoom: {
    input: {
      // Story 1.7: FastAPI에서 생성한 OpenAPI 스펙 경로/URL로 교체
      target: './openapi.json',
    },
    output: {
      mode: 'tags-split',
      client: 'react-query',
      target: './packages/api-client/src/generated',
      schemas: './packages/api-client/src/generated/model',
      // 단일 인터셉터(Bearer, 401→refresh) 경유 (AR10)
      override: {
        mutator: {
          path: './packages/api-client/src/client.ts',
          name: 'apiClient',
        },
        // FastAPI 기본 operationId는 verbose(예: `signup_api_v1_auth_signup_post`)라
        // 그대로 두면 훅명이 `useSignupApiV1AuthSignupPost`가 된다. 라우트 함수명만 남기도록
        // `_api_v1_...` 접미를 제거 → `signup`/`login`/`read_me`/`list_categories`(orval이 camelCase)
        // → useSignup/useLogin/useReadMe/useListCategories. (Story가 기대한 클린 훅명; 백엔드 무변경,
        // 프론트 config 한정 해결 — 작성자가 가정한 "clean operationId"를 codegen 계층에서 보정)
        operationName: (operation) => {
          const id = operation.operationId ?? '';
          const cleaned = id.replace(/_api_v1_.*$/, '');
          return cleaned || id;
        },
      },
    },
  },
});
