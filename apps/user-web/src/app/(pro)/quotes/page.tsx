"use client";

import { useEffect, useRef, useState } from "react";

import {
  useListMyQuotes,
  type PageQuoteListItem,
} from "@gosoom/api-client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

type QuoteListItem = PageQuoteListItem["items"][0];

const QUOTE_STATUS_LABELS: Record<string, string> = {
  pending: "검토 중",
  accepted: "수락됨",
  rejected: "거절됨",
  closed: "마감됨",
};

const QUOTE_STATUS_VARIANTS: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  pending: "secondary",
  accepted: "default",
  rejected: "destructive",
  closed: "outline",
};

const REQUEST_STATUS_LABELS: Record<string, string> = {
  open: "접수됨",
  matched: "매칭됨",
  completed: "완료됨",
  cancelled: "취소됨",
};

const REQUEST_STATUS_VARIANTS: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  open: "default",
  matched: "secondary",
  completed: "outline",
  cancelled: "destructive",
};

export default function MyQuotesPage() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<QuoteListItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
  const processedCursors = useRef(new Set<string | undefined>());

  const { data, isPending, isError, isFetching } =
    useListMyQuotes<PageQuoteListItem, Error>({ cursor });

  useEffect(() => {
    if (isFetching || !data?.items) return;
    if (processedCursors.current.has(cursor)) return;
    processedCursors.current.add(cursor);
    setAllItems((prev) => cursor === undefined ? data.items : [...prev, ...data.items]);
    setNextCursor(data.nextCursor);
  }, [data, cursor, isFetching]);

  const handleLoadMore = () => {
    if (nextCursor) setCursor(nextCursor);
  };

  return (
    <main className="max-w-screen-lg mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">내 견적 목록</h1>

      {isPending && cursor === undefined && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <Card>
          <CardContent className="p-6 text-center text-destructive">
            견적 목록을 불러오는 중 오류가 발생했습니다.
          </CardContent>
        </Card>
      )}

      {!isPending && !isError && allItems.length === 0 && (
        <Card>
          <CardContent className="p-10 text-center text-muted-foreground">
            제안한 견적이 없습니다.
          </CardContent>
        </Card>
      )}

      {allItems.length > 0 && (
        <div className="space-y-3">
          {allItems.map((quote) => (
            <Card key={quote.id}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xl font-bold text-primary">
                    {quote.price.toLocaleString()}원
                  </p>
                  <Badge variant={QUOTE_STATUS_VARIANTS[quote.status] ?? "secondary"}>
                    {QUOTE_STATUS_LABELS[quote.status] ?? quote.status}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">{quote.message}</p>

                {quote.serviceRequest && (
                  <>
                    <Separator />
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-muted-foreground">{quote.serviceRequest.region}</p>
                        <p className="text-sm mt-0.5 line-clamp-2">
                          {(quote.serviceRequest.description ?? "").slice(0, 80)}
                          {(quote.serviceRequest.description?.length ?? 0) > 80 ? "…" : ""}
                        </p>
                      </div>
                      <Badge
                        variant={REQUEST_STATUS_VARIANTS[quote.serviceRequest.status ?? ""] ?? "secondary"}
                        className="text-xs flex-shrink-0"
                      >
                        {REQUEST_STATUS_LABELS[quote.serviceRequest.status ?? ""] ?? quote.serviceRequest.status}
                      </Badge>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {nextCursor && (
        <Button
          variant="outline"
          className="w-full"
          onClick={handleLoadMore}
          disabled={isFetching}
        >
          {isFetching ? "로딩 중…" : "더 보기"}
        </Button>
      )}
    </main>
  );
}
