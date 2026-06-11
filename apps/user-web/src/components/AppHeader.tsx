"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearTokens, useReadMe, type UserRead } from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function AppHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const me = useReadMe<UserRead, Error>();

  // 인증 페이지는 자체 레이아웃 사용 — 헤더 숨김
  if (pathname.startsWith("/login") || pathname.startsWith("/signup")) {
    return null;
  }

  // 인증 상태 로딩 중 — 빈 헤더로 레이아웃 자리 확보
  if (me.isPending) {
    return <header className="h-14 border-b border-border bg-background" />;
  }

  // 미인증(오류 포함) — 헤더 미표시
  if (!me.data) return null;

  const handleLogout = () => {
    clearTokens();
    router.replace("/login");
  };

  const role = me.data.userRole;
  const isCustomer = role === "customer";
  const isPro = role === "pro";

  const navLinkClass = (prefix: string) =>
    `transition-colors hover:text-foreground ${
      pathname.startsWith(prefix)
        ? "text-foreground font-medium"
        : "text-muted-foreground"
    }`;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 max-w-screen-lg mx-auto items-center px-4 gap-6">
        <Link href="/" className="font-bold text-xl text-primary tracking-tight">
          gosoom
        </Link>

        <Separator orientation="vertical" className="h-5" />

        <nav className="flex items-center gap-5 text-sm flex-1">
          {isCustomer && (
            <>
              <Link href="/requests" className={navLinkClass("/requests")}>
                내 요청
              </Link>
              <Link href="/chat" className={navLinkClass("/chat")}>
                채팅
              </Link>
            </>
          )}

          {isPro && (
            <>
              <Link href="/feed" className={navLinkClass("/feed")}>
                요청 피드
              </Link>
              <Link href="/quotes" className={navLinkClass("/quotes")}>
                내 견적
              </Link>
              <Link href="/categories" className={navLinkClass("/categories")}>
                카테고리
              </Link>
              <Link href="/chat" className={navLinkClass("/chat")}>
                채팅
              </Link>
            </>
          )}
        </nav>

        <div className="flex items-center gap-3">
          <span className="hidden sm:inline text-sm text-muted-foreground">
            {me.data.displayName}
          </span>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            로그아웃
          </Button>
        </div>
      </div>
    </header>
  );
}
