"use client";

// 클라이언트 라우트 가드(AC4, 결정 #5) — 보호 화면을 감싼다.
// access는 메모리·refresh는 localStorage라 서버(proxy.ts)는 토큰을 읽을 수 없으므로
// 가드는 반드시 클라이언트 컴포넌트. 최종 권한 시행은 서버 API(NFR4) — 이건 UX 보조.
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useSyncExternalStore } from "react";

import { isAuthenticated } from "@gosoom/api-client";

// 토큰 스토어는 변경 이벤트를 발행하지 않으므로 구독은 no-op(가드는 마운트 시점 1회 판단).
const subscribe = () => () => {};
// 서버 스냅샷은 항상 미인증(SSR엔 window/메모리 토큰 없음) → 서버는 null 렌더.
const getServerSnapshot = () => false;

export function AuthGuard({ children }: { children: ReactNode }) {
  const router = useRouter();

  // 외부 저장소(메모리 access / localStorage refresh) 상태를 effect 없이 읽는다(React 권장).
  // isAuthenticated = access 또는 refresh 존재. 새로고침 직후엔 메모리 access가 사라지고
  // refresh만 남으므로 OR 조건이 통과 → 홈이 마운트되고 첫 401에서 인터셉터가 refresh.
  const authorized = useSyncExternalStore(
    subscribe,
    isAuthenticated,
    getServerSnapshot,
  );

  useEffect(() => {
    if (!authorized) {
      router.replace("/login");
    }
  }, [authorized, router]);

  // 미인증이면 보호 콘텐츠를 렌더하지 않음(리다이렉트 진행) — 깜빡임 방지.
  if (!authorized) return null;
  return <>{children}</>;
}
