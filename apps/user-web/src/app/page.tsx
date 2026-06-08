"use client";

// 인증 후 홈(AC2/AC4) — 클라이언트 가드로 보호. useReadMe(GET /users/me)로 현재 사용자
// displayName 표시(가입→로그인 E2E 완결의 가시적 증거). 로그아웃은 무상태(토큰 폐기만, 1.4 AC4 계승).
import { useRouter } from "next/navigation";

import { clearTokens, useReadMe, type UserRead } from "@gosoom/api-client";
import { Button } from "@gosoom/ui";

import { AuthGuard } from "@/providers/AuthGuard";

function HomeContent() {
  const router = useRouter();
  // 로딩/오류는 TanStack Query 상태로 일관 처리(AC3 — 자체 boolean 금지).
  const me = useReadMe<UserRead, Error>();

  const handleLogout = () => {
    // 서버 토큰 무효화 없음(무상태) — 클라이언트 토큰만 폐기 후 로그인으로.
    clearTokens();
    router.replace("/login");
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-50 p-8 dark:bg-black">
      <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
        gosoom
      </h1>

      {me.isPending && (
        <p className="text-zinc-600 dark:text-zinc-400">불러오는 중…</p>
      )}

      {me.error && (
        <p className="text-sm text-red-600" role="alert">
          {me.error.message}
        </p>
      )}

      {me.data && (
        <p className="text-lg text-zinc-800 dark:text-zinc-200">
          {me.data.displayName}님, 환영합니다.
        </p>
      )}

      <Button label="로그아웃" onPress={handleLogout} />
    </main>
  );
}

export default function Home() {
  return (
    <AuthGuard>
      <HomeContent />
    </AuthGuard>
  );
}
