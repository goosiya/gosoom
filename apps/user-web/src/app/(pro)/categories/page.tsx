"use client";

import { useState } from "react";

import { useQueryClient } from "@tanstack/react-query";

import {
  getGetProCategoriesQueryKey,
  useGetProCategories,
  useListCategories,
  useSetProCategories,
  type PageCategoryRead,
  type ProCategoriesRead,
} from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

interface CategoryFormProps {
  allIds: string[];
  allNames: Record<string, string>;
  initialIds: string[];
}

function CategoryForm({ allIds, allNames, initialIds }: CategoryFormProps) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set(initialIds));

  const mutation = useSetProCategories({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: getGetProCategoriesQueryKey() });
      },
    },
  });

  function toggleCategory(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function handleSave() {
    mutation.mutate({ data: { categoryIds: [...selected] } });
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {allIds.map((id) => (
          <label
            key={id}
            className={`flex items-center gap-2 rounded-md border p-3 cursor-pointer text-sm transition-colors ${
              selected.has(id)
                ? "border-primary bg-primary/5 text-primary font-medium"
                : "border-border hover:bg-muted text-foreground"
            }`}
          >
            <input
              type="checkbox"
              checked={selected.has(id)}
              onChange={() => toggleCategory(id)}
              className="sr-only"
            />
            <span
              className={`w-4 h-4 rounded border-2 flex items-center justify-center flex-shrink-0 ${
                selected.has(id) ? "border-primary bg-primary" : "border-border"
              }`}
            >
              {selected.has(id) && (
                <svg className="w-2.5 h-2.5 text-white" viewBox="0 0 10 10" fill="none">
                  <path d="M1.5 5L4 7.5L8.5 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </span>
            {allNames[id]}
          </label>
        ))}
      </div>

      {mutation.isError && (
        <p className="text-sm text-destructive" role="alert">저장 중 오류가 발생했습니다.</p>
      )}

      {mutation.isSuccess && (
        <p className="text-sm text-green-600" role="status">저장되었습니다. ✓</p>
      )}

      <Button onClick={handleSave} disabled={mutation.isPending}>
        {mutation.isPending ? "저장 중…" : "카테고리 저장"}
      </Button>
    </div>
  );
}

export default function CategoriesPage() {
  const allCategories = useListCategories<PageCategoryRead, Error>({ limit: 100 });
  const current = useGetProCategories<ProCategoriesRead, Error>();

  if (allCategories.isPending || current.isPending) {
    return (
      <main className="max-w-screen-md mx-auto p-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-14 bg-muted animate-pulse rounded-md" />
          ))}
        </div>
      </main>
    );
  }

  if (allCategories.isError || current.isError) {
    return (
      <main className="max-w-screen-md mx-auto p-6">
        <Card>
          <CardContent className="p-6 text-center text-destructive">
            데이터를 불러오는 중 오류가 발생했습니다.
          </CardContent>
        </Card>
      </main>
    );
  }

  const items = allCategories.data?.items ?? [];
  const allIds = items.map((c) => c.id);
  const allNames = Object.fromEntries(items.map((c) => [c.id, c.name]));
  const allIdsSet = new Set(allIds);
  const initialIds = (current.data?.categoryIds ?? []).filter((id) => allIdsSet.has(id));

  return (
    <main className="max-w-screen-md mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>활동 카테고리 설정</CardTitle>
          <CardDescription>
            활동할 서비스 카테고리를 선택하세요. 선택한 카테고리의 요청이 피드에 노출됩니다.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <CategoryForm
            key={[...initialIds].sort().join(",")}
            allIds={allIds}
            allNames={allNames}
            initialIds={initialIds}
          />
        </CardContent>
      </Card>
    </main>
  );
}
