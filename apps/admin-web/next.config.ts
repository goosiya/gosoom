import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // user-web과 동일한 RN-Web 배선 — Epic 6에서 @gosoom/ui 사용 시 retrofit 불필요(AR16).
  transpilePackages: ["@gosoom/ui"],
  turbopack: {
    resolveAlias: {
      "react-native": "react-native-web",
    },
  },
};

export default nextConfig;
