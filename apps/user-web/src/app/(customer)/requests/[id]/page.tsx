"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import {
  useGetServiceRequest,
  useUpdateServiceRequestStatus,
  useListServiceRequestQuotes,
  useListCategories,
  useAcceptQuote,
  useRejectQuote,
  getGetServiceRequestQueryKey,
  getListMyServiceRequestsQueryKey,
  getListServiceRequestQuotesQueryKey,
  type ServiceRequestRead,
  type PageQuoteWithProInfo,
  type PageCategoryRead,
} from "@gosoom/api-client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

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

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("ko-KR", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RequestDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const router = useRouter();

  const { data, isPending, isError } = useGetServiceRequest<ServiceRequestRead, Error>(id);

  const { data: quotesData, isPending: quotesLoading, isError: quotesError } =
    useListServiceRequestQuotes<PageQuoteWithProInfo, Error>(id);

  const { data: categoriesData } = useListCategories<PageCategoryRead, Error>({ limit: 100 });
  const categoryMap = new Map(
    (categoriesData?.items ?? []).map((c) => [c.id, c.name])
  );

  const queryClient = useQueryClient();

  const acceptMutation = useAcceptQuote({
    mutation: {
      onSuccess: (chatRoom) => {
        queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
        queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
        queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
        router.push(`/chat/${chatRoom.id}`);
      },
    },
  });

  const rejectMutation = useRejectQuote({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getListServiceRequestQuotesQueryKey(id) });
      },
    },
  });

  const mutation = useUpdateServiceRequestStatus({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetServiceRequestQueryKey(id) });
        queryClient.invalidateQueries({ queryKey: getListMyServiceRequestsQueryKey() });
      },
    },
  });

  return (
    <main className="max-w-screen-md mx-auto p-6 space-y-6">
      <Link href="/requests" className="text-sm text-primary hover:underline inline-flex items-center gap-1">
        ← 목록으로
      </Link>

      {isPending && (
        <div className="space-y-4">
          <div className="h-8 w-32 bg-muted animate-pulse rounded" />
          <div className="h-48 bg-muted animate-pulse rounded-lg" />
        </div>
      )}

      {isError && (
        <Card>
          <CardContent className="p-6 text-center text-destructive">
            요청 정보를 불러오지 못했습니다.
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          {/* 요청 정보 카드 */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">요청 상세</CardTitle>
                <Badge variant={STATUS_VARIANTS[data.status] ?? "secondary"}>
                  {STATUS_LABELS[data.status] ?? data.status}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <dt className="text-xs font-medium text-muted-foreground">카테고리</dt>
                  <dd className="mt-1 text-sm">{categoryMap.get(data.categoryId) ?? data.categoryId}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium text-muted-foreground">지역</dt>
                  <dd className="mt-1 text-sm">{data.region}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-xs font-medium text-muted-foreground">설명</dt>
                  <dd className="mt-1 text-sm">{data.description}</dd>
                </div>
                {data.desiredSchedule && (
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">희망 일정</dt>
                    <dd className="mt-1 text-sm">{data.desiredSchedule}</dd>
                  </div>
                )}
                {data.budget !== null && data.budget !== undefined && (
                  <div>
                    <dt className="text-xs font-medium text-muted-foreground">예산</dt>
                    <dd className="mt-1 text-sm font-medium">{data.budget.toLocaleString("ko-KR")}원</dd>
                  </div>
                )}
                <div>
                  <dt className="text-xs font-medium text-muted-foreground">생성일</dt>
                  <dd className="mt-1 text-sm">{formatDate(data.createdAt)}</dd>
                </div>
              </dl>

              <Separator />

              <div className="flex gap-3">
                {data.status === "open" && (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => mutation.mutate({ requestId: id, data: { action: "cancel" } })}
                    disabled={mutation.isPending}
                  >
                    {mutation.isPending ? "처리 중…" : "취소하기"}
                  </Button>
                )}
                {data.status === "matched" && (
                  <Button
                    size="sm"
                    onClick={() => mutation.mutate({ requestId: id, data: { action: "complete" } })}
                    disabled={mutation.isPending}
                  >
                    {mutation.isPending ? "처리 중…" : "완료하기"}
                  </Button>
                )}
                {mutation.isError && (
                  <p className="text-destructive text-sm self-center" role="alert">
                    요청 처리에 실패했습니다.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* 견적 목록 */}
          <section className="space-y-4">
            <h2 className="text-lg font-semibold">받은 견적</h2>

            {quotesLoading && (
              <div className="space-y-3">
                {[1, 2].map((i) => (
                  <div key={i} className="h-32 bg-muted animate-pulse rounded-lg" />
                ))}
              </div>
            )}

            {quotesError && (
              <Card>
                <CardContent className="p-4 text-center text-destructive text-sm">
                  견적을 불러오지 못했습니다.
                </CardContent>
              </Card>
            )}

            {!quotesLoading && !quotesError && (!quotesData?.items || quotesData.items.length === 0) && (
              <Card>
                <CardContent className="p-6 text-center text-muted-foreground text-sm">
                  아직 받은 견적이 없습니다.
                </CardContent>
              </Card>
            )}

            {quotesData?.items && quotesData.items.length > 0 && (
              <div className="space-y-3">
                {quotesData.items.map((quote) => (
                  <Card key={quote.id}>
                    <CardContent className="p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-sm">{quote.pro.displayName}</span>
                        <Badge variant={QUOTE_STATUS_VARIANTS[quote.status] ?? "secondary"}>
                          {QUOTE_STATUS_LABELS[quote.status] ?? quote.status}
                        </Badge>
                      </div>
                      <p className="text-lg font-bold text-primary">
                        {quote.price.toLocaleString("ko-KR")}원
                      </p>
                      <p className="text-sm text-muted-foreground">{quote.message}</p>
                      {quote.pro.categoryIds.length > 0 && (
                        <p className="text-xs text-muted-foreground">
                          전문 분야: {quote.pro.categoryIds.map((cid) => categoryMap.get(cid) ?? cid).join(", ")}
                        </p>
                      )}

                      {data.status === "open" && quote.status === "pending" && (
                        <div className="flex gap-2 pt-1">
                          <Button
                            size="sm"
                            onClick={() => acceptMutation.mutate({ quoteId: quote.id })}
                            disabled={acceptMutation.isPending}
                          >
                            {acceptMutation.isPending ? "처리 중…" : "수락하기"}
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => rejectMutation.mutate({ quoteId: quote.id })}
                            disabled={rejectMutation.isPending}
                          >
                            {rejectMutation.isPending ? "처리 중…" : "거절하기"}
                          </Button>
                          {(acceptMutation.isError || rejectMutation.isError) && (
                            <p className="text-destructive text-xs self-center" role="alert">
                              처리에 실패했습니다.
                            </p>
                          )}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
