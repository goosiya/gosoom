"use client";

import { use, useState } from "react";

import {
  useGetServiceRequestFeedDetail,
  useCreateServiceRequestQuote,
  type ServiceRequestRead,
} from "@gosoom/api-client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";

export default function FeedDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const storageKey = `gosoom_quote_submitted_${id}`;

  const detail = useGetServiceRequestFeedDetail<ServiceRequestRead, Error>(id);
  const submitQuote = useCreateServiceRequestQuote();

  const [price, setPrice] = useState("");
  const [message, setMessage] = useState("");
  const [submitted, setSubmitted] = useState(
    () => typeof window !== "undefined" && localStorage.getItem(storageKey) === "true"
  );
  const [submittedThisSession, setSubmittedThisSession] = useState(false);

  if (detail.isPending) {
    return (
      <main className="max-w-screen-md mx-auto p-6 space-y-4">
        <div className="h-8 w-32 bg-muted animate-pulse rounded" />
        <div className="h-48 bg-muted animate-pulse rounded-lg" />
      </main>
    );
  }

  if (detail.isError) {
    return (
      <main className="max-w-screen-md mx-auto p-6">
        <Card>
          <CardContent className="p-6 text-center text-destructive">
            요청을 불러오는 중 오류가 발생했습니다.
          </CardContent>
        </Card>
      </main>
    );
  }

  const req = detail.data;
  if (!req) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (submitted) return;
    const priceNum = parseInt(price, 10);
    if (isNaN(priceNum) || priceNum < 0 || !message.trim()) return;

    submitQuote.mutate(
      { requestId: id, data: { price: priceNum, message: message.trim() } },
      {
        onSuccess: () => {
          localStorage.setItem(storageKey, "true");
          setSubmitted(true);
          setSubmittedThisSession(true);
        },
      },
    );
  };

  return (
    <main className="max-w-screen-md mx-auto p-6 space-y-6">
      {/* 요청 정보 카드 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">요청 정보</CardTitle>
            <Badge variant={req.status === "open" ? "default" : "secondary"}>
              {req.status === "open" ? "견적 가능" : "매칭됨"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <dt className="text-xs font-medium text-muted-foreground">지역</dt>
              <dd className="mt-1 text-sm">{req.region}</dd>
            </div>
            {req.desiredSchedule && (
              <div>
                <dt className="text-xs font-medium text-muted-foreground">희망 일정</dt>
                <dd className="mt-1 text-sm">{req.desiredSchedule}</dd>
              </div>
            )}
            {req.budget != null && (
              <div>
                <dt className="text-xs font-medium text-muted-foreground">예산</dt>
                <dd className="mt-1 text-sm font-medium">{req.budget.toLocaleString()}원</dd>
              </div>
            )}
            <div className="sm:col-span-2">
              <dt className="text-xs font-medium text-muted-foreground">요청 내용</dt>
              <dd className="mt-1 text-sm">{req.description}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* 견적 제안 카드 */}
      {req.status === "open" && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">견적 제안</CardTitle>
          </CardHeader>
          <CardContent>
            {submitted ? (
              <p className="text-sm text-green-600 text-center py-4">
                {submittedThisSession ? "견적이 제출되었습니다. ✓" : "이미 견적을 제출했습니다."}
              </p>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="price">금액 (원)</Label>
                  <Input
                    id="price"
                    type="number"
                    min={0}
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    placeholder="예: 50000"
                    required
                    disabled={submitQuote.isPending}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="quoteMessage">제안 메시지</Label>
                  <Textarea
                    id="quoteMessage"
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="고객에게 전달할 메시지를 작성하세요"
                    rows={4}
                    required
                    disabled={submitQuote.isPending}
                  />
                </div>
                {submitQuote.isError && (
                  <p className="text-sm text-destructive" role="alert">
                    {(submitQuote.error as Error)?.message ?? "견적 제출 중 오류가 발생했습니다."}
                  </p>
                )}
                <Button type="submit" className="w-full" disabled={submitQuote.isPending}>
                  {submitQuote.isPending ? "제출 중…" : "견적 제안하기"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      )}

      {req.status === "matched" && (
        <Card>
          <CardContent className="p-6 text-center text-muted-foreground">
            이 요청은 이미 다른 고수와 매칭되었습니다.
          </CardContent>
        </Card>
      )}
    </main>
  );
}
