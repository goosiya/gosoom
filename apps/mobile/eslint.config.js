// https://docs.expo.dev/guides/using-eslint/ (flat config)
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*', '.expo/*', 'expo-export/*'],
  },
  {
    // Expo SDK 55 기본 템플릿의 웹 하이드레이션 헬퍼는 마운트 시 setState가 의도된 패턴이다.
    // eslint-config-expo@56의 신규 규칙과의 마찰만 좁게 예외 처리(우리 실제 코드는 규칙 유지).
    files: ['src/hooks/use-color-scheme.web.ts'],
    rules: {
      'react-hooks/set-state-in-effect': 'off',
    },
  },
]);
