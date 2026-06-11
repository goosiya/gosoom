"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  getListAdminCategoriesQueryKey,
  useCreateAdminCategory,
  useDeactivateAdminCategory,
  useListAdminCategories,
  useUpdateAdminCategory,
  type CategoryAdminRead,
} from "@gosoom/api-client";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function CategoriesPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">카테고리 관리</h1>
      <AddCategoryForm />
      <CategoryTable />
    </main>
  );
}

function AddCategoryForm() {
  const [name, setName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const createCategory = useCreateAdminCategory({
    mutation: {
      onSuccess: () => {
        setName("");
        setFormError(null);
        queryClient.invalidateQueries({ queryKey: getListAdminCategoriesQueryKey() });
      },
      onError: (error: unknown) => {
        setFormError(
          error instanceof Error ? error.message : "카테고리 추가 중 오류가 발생했습니다.",
        );
      },
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    createCategory.mutate({ data: { name } });
  };

  return (
    <Card className="mb-8">
      <CardHeader>
        <CardTitle>신규 카테고리 추가</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <div className="grid gap-1.5">
            <Label htmlFor="category-name">카테고리명</Label>
            <Input
              id="category-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="예: 청소, 이사, 과외"
              className="w-64"
            />
          </div>
          <Button type="submit" disabled={createCategory.isPending}>
            {createCategory.isPending ? "추가 중..." : "카테고리 추가"}
          </Button>
        </form>
        {formError && (
          <div className="mt-3 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {formError}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CategoryTable() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<CategoryAdminRead[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useListAdminCategories({
    limit: 20,
    cursor,
  });

  useEffect(() => {
    if (!data?.items) return;
    if (!cursor) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAllItems(data.items);
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAllItems((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        return [...prev, ...data.items.filter((i) => !existingIds.has(i.id))];
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const invalidateList = () => {
    setActionError(null);
    queryClient.invalidateQueries({ queryKey: getListAdminCategoriesQueryKey() });
    setCursor(undefined);
    setAllItems([]);
  };

  const deactivate = useDeactivateAdminCategory({
    mutation: {
      onSuccess: invalidateList,
      onError: (error: unknown) => {
        setActionError(error instanceof Error ? error.message : "오류가 발생했습니다.");
      },
    },
  });

  const formatDate = (iso: string) => new Date(iso).toLocaleDateString("ko-KR");

  if (isLoading && allItems.length === 0) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="animate-pulse bg-muted rounded h-12" />
        ))}
      </div>
    );
  }

  return (
    <div>
      {actionError && (
        <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError}
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>카테고리명</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>사용여부</TableHead>
            <TableHead>생성일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                카테고리가 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((cat) => (
              <TableRow key={cat.id}>
                <TableCell className="font-medium">{cat.name}</TableCell>
                <TableCell>
                  <Badge variant={cat.isActive ? "default" : "secondary"}>
                    {cat.isActive ? "활성" : "비활성"}
                  </Badge>
                </TableCell>
                <TableCell>
                  {cat.inUse ? (
                    <Badge variant="outline" className="text-xs">
                      사용 중
                    </Badge>
                  ) : (
                    <span className="text-sm text-muted-foreground">미사용</span>
                  )}
                </TableCell>
                <TableCell>{formatDate(cat.createdAt)}</TableCell>
                <TableCell>
                  <CategoryActions
                    category={cat}
                    onDeactivate={(id) => deactivate.mutate({ categoryId: id })}
                    onRenameSuccess={invalidateList}
                    isDeactivating={deactivate.isPending}
                  />
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {data?.nextCursor && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => setCursor(data.nextCursor ?? undefined)}
            disabled={isFetching}
          >
            {isFetching ? "불러오는 중..." : "더 보기"}
          </Button>
        </div>
      )}
    </div>
  );
}

interface CategoryActionsProps {
  category: CategoryAdminRead;
  onDeactivate: (id: string) => void;
  onRenameSuccess: () => void;
  isDeactivating: boolean;
}

function CategoryActions({
  category,
  onDeactivate,
  onRenameSuccess,
  isDeactivating,
}: CategoryActionsProps) {
  const [renameOpen, setRenameOpen] = useState(false);
  const [newName, setNewName] = useState(category.name);
  const [renameError, setRenameError] = useState<string | null>(null);

  const updateCategory = useUpdateAdminCategory({
    mutation: {
      onSuccess: () => {
        setRenameOpen(false);
        setRenameError(null);
        onRenameSuccess();
      },
      onError: (error: unknown) => {
        setRenameError(
          error instanceof Error ? error.message : "이름 변경 중 오류가 발생했습니다.",
        );
      },
    },
  });

  if (!category.isActive) {
    return <span className="text-sm text-muted-foreground">비활성</span>;
  }

  return (
    <div className="flex gap-2">
      {!category.inUse && (
        <AlertDialog
          open={renameOpen}
          onOpenChange={(open) => {
            setRenameOpen(open);
            if (open) {
              setNewName(category.name);
              setRenameError(null);
            }
          }}
        >
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm">
              이름 변경
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>카테고리 이름 변경</AlertDialogTitle>
              <AlertDialogDescription>새 이름을 입력하세요.</AlertDialogDescription>
            </AlertDialogHeader>
            <div className="py-2">
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="카테고리명"
              />
              {renameError && <p className="mt-2 text-sm text-destructive">{renameError}</p>}
            </div>
            <AlertDialogFooter>
              <AlertDialogCancel>취소</AlertDialogCancel>
              <AlertDialogAction
                onClick={() =>
                  updateCategory.mutate({
                    categoryId: category.id,
                    data: { name: newName },
                  })
                }
                disabled={updateCategory.isPending || !newName.trim()}
              >
                {updateCategory.isPending ? "변경 중..." : "변경"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="outline" size="sm" disabled={isDeactivating}>
            비활성화
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>카테고리를 비활성화하시겠습니까?</AlertDialogTitle>
            <AlertDialogDescription>
              &quot;{category.name}&quot;을(를) 비활성화하면 고객 요청 생성 및 고수 카테고리
              설정 목록에서 제외됩니다.
              {category.inUse && " 현재 사용 중인 카테고리입니다."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>취소</AlertDialogCancel>
            <AlertDialogAction onClick={() => onDeactivate(category.id)}>
              비활성화
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
