import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 공유 RN-Web 패키지 + api-client(TS 소스 워크스페이스 패키지)를 트랜스파일 (AR16)
  transpilePackages: ["@gosoom/ui", "@gosoom/api-client"],
  turbopack: {
    // react-native 임포트를 웹에서 react-native-web으로 별칭 (Next 16 = Turbopack 기본).
    // 이로써 @gosoom/ui의 react-native 프리미티브가 웹 번들에서 동작한다.
    resolveAlias: {
      "react-native": "react-native-web",
    },
  },
};

export default nextConfig;
