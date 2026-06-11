"use client";

import { type ReactNode } from "react";

import { AdminGuard } from "@/providers/AdminGuard";
import { AdminHeader } from "@/components/AdminHeader";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminGuard>
      <AdminHeader />
      <div className="flex-1">{children}</div>
    </AdminGuard>
  );
}
