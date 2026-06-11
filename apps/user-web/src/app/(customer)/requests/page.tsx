"use client";

import Link from "next/link";

import {
  useListMyServiceRequests,
  type PageServiceRequestRead,
} from "@gosoom/api-client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const STATUS_LABELS: Record<string, string> = {
  open: "접수됨",
  matched: "매칭됨",
  completed: "완료됨",
  cancelled: "취소됨",
};

const STATUS_VARIANTS: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  open: "default",
  matched: "secondary",
  completed: "outline",
  cancelled: "destructive",
};

export default function RequestsPage() {
  const { data, isPending, isError } = useListMyServiceRequests<
    PageServiceRequestRead,
    Error
  >();

  return (
    <main className="max-w-screen-lg mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">내 요청 목록</h1>
        <Button asChild size="sm">
          <Link href="/requests/new">새 요청 만들기</Link>
        </Button>
      </div>

      {isPending && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <Card>
          <CardContent className="p-6 text-center text-destructive">
            요청 목록을 불러오지 못했습니다.
          </CardContent>
        </Card>
      )}

      {data && data.items.length === 0 && (
        <Card>
          <CardContent className="p-10 text-center space-y-3">
            <p className="text-muted-foreground">아직 요청이 없습니다.</p>
            <Button asChild size="sm">
              <Link href="/requests/new">첫 요청 만들기</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((item) => (
            <Link key={item.id} href={`/requests/${item.id}`}>
              <Card className="hover:border-primary transition-colors cursor-pointer">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">{item.description}</p>
                      <p className="text-xs text-muted-foreground mt-1">{item.region}</p>
                    </div>
                    <Badge variant={STATUS_VARIANTS[item.status] ?? "secondary"}>
                      {STATUS_LABELS[item.status] ?? item.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
