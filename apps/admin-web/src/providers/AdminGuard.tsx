"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useSyncExternalStore } from "react";

import { isAuthenticated, useReadMe, type UserRead } from "@gosoom/api-client";

const subscribe = () => () => {};
const getServerSnapshot = () => false;

export function AdminGuard({ children }: { children: ReactNode }) {
  const router = useRouter();

  const authorized = useSyncExternalStore(subscribe, isAuthenticated, getServerSnapshot);

  useEffect(() => {
    if (!authorized) router.replace("/login");
  }, [authorized, router]);

  if (!authorized) return null;

  return <AdminRoleGuard>{children}</AdminRoleGuard>;
}

function AdminRoleGuard({ children }: { children: ReactNode }) {
  const router = useRouter();
  const me = useReadMe<UserRead, Error>();

  useEffect(() => {
    if (me.isError || (me.data && me.data.userRole !== "admin")) {
      router.replace("/login");
    }
  }, [me.isError, me.data, router]);

  if (me.isPending) return null;
  if (me.isError) return null;
  if (me.data && me.data.userRole !== "admin") return null;

  return <>{children}</>;
}
