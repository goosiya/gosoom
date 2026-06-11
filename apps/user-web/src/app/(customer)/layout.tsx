"use client";

// (customer) 그룹 레이아웃 — AuthGuard + CUSTOMER 역할 검사.
// 인증 실패(isError) 시 /login으로, 비CUSTOMER(PRO/ADMIN) 시 /로 리다이렉트.
// 최종 권한 시행은 서버 API — 이 가드는 UX 보조 역할.
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { useReadMe, type UserRead } from "@gosoom/api-client";

import { AuthGuard } from "@/providers/AuthGuard";

function CustomerGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const me = useReadMe<UserRead, Error>();

  useEffect(() => {
    if (me.isError) {
      router.replace("/login");
    } else if (me.data && me.data.userRole !== "customer") {
      router.replace("/");
    }
  }, [me.isError, me.data, router]);

  if (me.isPending) return null;
  if (me.isError) return null;
  if (me.data && me.data.userRole !== "customer") return null;

  return <>{children}</>;
}

export default function CustomerLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <CustomerGuard>{children}</CustomerGuard>
    </AuthGuard>
  );
}
