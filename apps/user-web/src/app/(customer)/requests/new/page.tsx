"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  useCreateServiceRequest,
  useListCategories,
  type PageCategoryRead,
} from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

export default function NewRequestPage() {
  const router = useRouter();

  const [categoryId, setCategoryId] = useState("");
  const [region, setRegion] = useState("");
  const [description, setDescription] = useState("");
  const [desiredSchedule, setDesiredSchedule] = useState("");
  const [budget, setBudget] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const categories = useListCategories<PageCategoryRead, Error>({ limit: 100 });

  const createRequest = useCreateServiceRequest<Error>({
    mutation: {
      onSuccess: () => {
        router.push("/requests");
      },
      onError: (err) => {
        setErrorMsg(err instanceof Error ? err.message : "요청에 실패했습니다.");
      },
    },
  });

  const canSubmit =
    categoryId !== "" &&
    region.trim() !== "" &&
    description.trim() !== "" &&
    !createRequest.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setErrorMsg(null);
    const parsedBudget = budget !== "" ? parseInt(budget, 10) : undefined;
    if (parsedBudget !== undefined && (Number.isNaN(parsedBudget) || parsedBudget < 0)) {
      setErrorMsg("예산은 0 이상의 숫자를 입력해 주세요.");
      return;
    }
    createRequest.mutate({
      data: {
        categoryId,
        region: region.trim(),
        description: description.trim(),
        desiredSchedule: desiredSchedule.trim() || undefined,
        budget: parsedBudget,
      },
    });
  };

  return (
    <main className="max-w-screen-sm mx-auto p-6">
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle>서비스 요청 만들기</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="category">카테고리 *</Label>
              <Select
                value={categoryId}
                onValueChange={setCategoryId}
                disabled={categories.isPending || categories.isError || createRequest.isPending}
              >
                <SelectTrigger id="category">
                  <SelectValue
                    placeholder={
                      categories.isPending
                        ? "로딩 중…"
                        : categories.isError
                          ? "카테고리 로드 실패"
                          : "카테고리 선택"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {categories.data?.items.map((cat) => (
                    <SelectItem key={cat.id} value={cat.id}>
                      {cat.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="region">지역 *</Label>
              <Input
                id="region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                placeholder="예: 서울 강남구"
                disabled={createRequest.isPending}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">설명 *</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="요청 내용을 자세히 입력해 주세요"
                rows={4}
                disabled={createRequest.isPending}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="schedule">희망 일정 (선택)</Label>
              <Input
                id="schedule"
                value={desiredSchedule}
                onChange={(e) => setDesiredSchedule(e.target.value)}
                placeholder="예: 이번 주 중, 6/20 오전"
                disabled={createRequest.isPending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="budget">예산 (선택, 원₩)</Label>
              <Input
                id="budget"
                type="number"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="예: 50000"
                min={0}
                disabled={createRequest.isPending}
              />
            </div>

            {errorMsg && (
              <p className="text-sm text-destructive" role="alert">
                {errorMsg}
              </p>
            )}

            <Button type="submit" className="w-full" disabled={!canSubmit}>
              {createRequest.isPending ? "제출 중…" : "요청 제출"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
