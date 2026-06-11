"use client";

import Link from "next/link";

import {
  useListServiceRequestFeed,
  type PageServiceRequestRead,
} from "@gosoom/api-client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function FeedPage() {
  const feed = useListServiceRequestFeed<PageServiceRequestRead, Error>();

  return (
    <main className="max-w-screen-lg mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">요청 피드</h1>

      {feed.isPending && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      )}

      {feed.isError && (
        <Card>
          <CardContent className="p-6 text-center text-destructive">
            피드를 불러오는 중 오류가 발생했습니다.
          </CardContent>
        </Card>
      )}

      {feed.data && (feed.data.items ?? []).length === 0 && (
        <Card>
          <CardContent className="p-10 text-center space-y-3">
            <p className="text-muted-foreground">표시할 요청이 없습니다.</p>
            <p className="text-sm text-muted-foreground">카테고리를 먼저 설정해 주세요.</p>
            <Button asChild size="sm" variant="outline">
              <Link href="/categories">카테고리 설정하기</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {feed.data && (feed.data.items ?? []).length > 0 && (
        <div className="space-y-3">
          {(feed.data.items ?? []).map((req) => (
            <Card key={req.id} className={req.status === "matched" ? "opacity-60" : ""}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm">{req.region}</p>
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {req.description ?? ""}
                    </p>
                  </div>
                  <Badge variant={req.status === "open" ? "default" : "secondary"}>
                    {req.status === "open" ? "견적 가능" : "매칭됨"}
                  </Badge>
                </div>
                {req.status === "open" && (
                  <div className="mt-3">
                    <Button asChild size="sm">
                      <Link href={`/feed/${req.id}`}>견적 제안하기</Link>
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
