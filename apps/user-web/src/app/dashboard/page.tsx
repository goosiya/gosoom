"use client";

import Link from "next/link";

import { useReadMe, type UserRead } from "@gosoom/api-client";

import { AuthGuard } from "@/providers/AuthGuard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const CUSTOMER_QUICK_ACTIONS = [
  {
    title: "새 요청 만들기",
    description: "원하는 서비스를 고수에게 요청하세요.",
    href: "/requests/new",
    cta: "요청 작성",
  },
  {
    title: "내 요청 목록",
    description: "진행 중인 요청과 견적을 확인하세요.",
    href: "/requests",
    cta: "목록 보기",
  },
  {
    title: "채팅",
    description: "수락된 견적의 고수와 대화하세요.",
    href: "/chat",
    cta: "채팅 열기",
  },
];

const PRO_QUICK_ACTIONS = [
  {
    title: "요청 피드",
    description: "내 카테고리에 맞는 요청을 확인하고 견적을 제안하세요.",
    href: "/feed",
    cta: "피드 보기",
  },
  {
    title: "내 견적",
    description: "제출한 견적의 현황을 확인하세요.",
    href: "/quotes",
    cta: "견적 확인",
  },
  {
    title: "카테고리 설정",
    description: "활동할 서비스 카테고리를 선택하세요.",
    href: "/categories",
    cta: "설정하기",
  },
  {
    title: "채팅",
    description: "수락된 견적의 고객과 대화하세요.",
    href: "/chat",
    cta: "채팅 열기",
  },
];

function DashboardContent() {
  const me = useReadMe<UserRead, Error>();

  if (me.isPending) {
    return (
      <main className="max-w-screen-lg mx-auto p-6">
        <div className="h-8 w-48 bg-muted animate-pulse rounded mb-6" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </main>
    );
  }

  if (!me.data) return null;

  const isCustomer = me.data.userRole === "customer";
  const actions = isCustomer ? CUSTOMER_QUICK_ACTIONS : PRO_QUICK_ACTIONS;

  return (
    <main className="max-w-screen-lg mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">
          안녕하세요, {me.data.displayName}님 👋
        </h1>
        <p className="text-muted-foreground mt-1 text-sm">
          {isCustomer ? "원하는 서비스를 찾아보세요." : "오늘도 좋은 서비스를 제공해 주세요."}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {actions.map((action) => (
          <Card key={action.href} className="hover:border-primary transition-colors">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">{action.title}</CardTitle>
              <CardDescription className="text-sm">{action.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild size="sm" className="w-full">
                <Link href={action.href}>{action.cta}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}
