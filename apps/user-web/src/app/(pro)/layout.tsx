"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { useReadMe, type UserRead } from "@gosoom/api-client";

import { AuthGuard } from "@/providers/AuthGuard";

function ProGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const me = useReadMe<UserRead, Error>();

  useEffect(() => {
    if (me.isError) {
      router.replace("/login");
    } else if (me.data && me.data.userRole !== "pro") {
      router.replace("/dashboard");
    }
  }, [me.isError, me.data, router]);

  if (me.isPending) return null;
  if (me.isError) return null;
  if (me.data && me.data.userRole !== "pro") return null;

  return <>{children}</>;
}

export default function ProLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <ProGuard>{children}</ProGuard>
    </AuthGuard>
  );
}
