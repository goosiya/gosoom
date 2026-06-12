"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { clearTokens, useReadMe, type UserRead } from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

const NAV_LINKS = [
  { href: "/users", label: "계정관리" },
  { href: "/admins", label: "관리자관리" },
  { href: "/requests", label: "요청관리" },
  { href: "/chats", label: "채팅내역" },
  { href: "/categories", label: "카테고리관리" },
];

export function AdminHeader() {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const me = useReadMe<UserRead, Error>();

  const handleLogout = () => {
    queryClient.clear();
    clearTokens();
    router.replace("/login");
  };

  if (me.isPending) {
    return <header className="h-14 border-b border-border bg-background" />;
  }

  if (me.isError || !me.data) {
    return (
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95">
        <div className="flex h-14 max-w-screen-xl mx-auto items-center px-4">
          <span className="font-bold text-xl text-primary tracking-tight">meetgo 관리자</span>
          <div className="flex-1" />
          <Button variant="ghost" size="sm" onClick={handleLogout}>로그아웃</Button>
        </div>
      </header>
    );
  }

  const navLinkClass = (prefix: string) =>
    `transition-colors hover:text-foreground text-sm ${
      pathname.startsWith(prefix)
        ? "text-foreground font-medium"
        : "text-muted-foreground"
    }`;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 max-w-screen-xl mx-auto items-center px-4 gap-6">
        <Link href="/dashboard" className="font-bold text-xl text-primary tracking-tight whitespace-nowrap">
          meetgo 관리자
        </Link>

        <Separator orientation="vertical" className="h-5" />

        <nav className="flex items-center gap-5 flex-1">
          {NAV_LINKS.map(({ href, label }) => (
            <Link key={href} href={href} className={navLinkClass(href)}>
              {label}
            </Link>
          ))}
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
