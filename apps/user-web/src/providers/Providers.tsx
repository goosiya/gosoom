"use client";

// 전역 Provider — TanStack Query 단일 소스(서버 상태)와 인증 실패 라우팅을 배선한다.
// layout.tsx가 모든 화면(공개 login/signup 포함)을 감싼다 → 모든 Orval 훅이 동작.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";

import { setAuthFailureHandler } from "@gosoom/api-client";

export function Providers({ children }: { children: ReactNode }) {
  const router = useRouter();

  // QueryClient는 1회만 생성(컴포넌트 본문에서 직접 new 하면 매 렌더 재생성 → 캐시 소실, 함정 #6).
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // 인증 401은 인터셉터가 refresh로 처리하므로 과도한 재시도는 불필요.
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  useEffect(() => {
    // 인터셉터가 refresh 실패로 세션을 종료하면 로그인으로 SPA 이동(전체 새로고침 회피).
    setAuthFailureHandler(() => {
      router.replace("/login");
    });
  }, [router]);

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
