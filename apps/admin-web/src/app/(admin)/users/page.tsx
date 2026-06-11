"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  getListAdminUsersQueryKey,
  useActivateAdminUser,
  useDeactivateAdminUser,
  useListAdminUsers,
  type UserRead,
} from "@gosoom/api-client";
import type { UserRole } from "@gosoom/api-client";

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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const ROLE_TABS = [
  { value: "customer" as const, label: "고객" },
  { value: "pro" as const, label: "고수" },
];

export default function UsersPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">계정 관리</h1>
      <Tabs defaultValue="customer">
        <TabsList>
          {ROLE_TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {ROLE_TABS.map((t) => (
          <TabsContent key={t.value} value={t.value}>
            <UserTable role={t.value} />
          </TabsContent>
        ))}
      </Tabs>
    </main>
  );
}

function UserTable({ role }: { role: "customer" | "pro" }) {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<UserRead[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useListAdminUsers({
    role: role as UserRole,
    limit: 20,
    cursor,
  });

  // role 변경 시 상태 초기화
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCursor(undefined);
    setAllItems([]);
  }, [role]);

  // 새 데이터 누적
  useEffect(() => {
    if (!data?.items) return;
    if (!cursor) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAllItems(data.items);
    } else {
      setAllItems((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        const newItems = data.items.filter((i) => !existingIds.has(i.id));
        return [...prev, ...newItems];
      });
    }
  // cursor 변경 시 data가 새로 도착했을 때만 실행
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  const invalidateList = () => {
    setActionError(null);
    queryClient.invalidateQueries({
      queryKey: getListAdminUsersQueryKey({ role: role as UserRole, limit: 20 }),
    });
    setCursor(undefined);
    setAllItems([]);
  };

  const handleError = (error: unknown) => {
    setActionError(error instanceof Error ? error.message : "오류가 발생했습니다.");
  };

  const deactivate = useDeactivateAdminUser({
    mutation: { onSuccess: invalidateList, onError: handleError },
  });

  const activate = useActivateAdminUser({
    mutation: { onSuccess: invalidateList, onError: handleError },
  });

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("ko-KR");

  if (isLoading && allItems.length === 0) {
    return (
      <div className="mt-4 space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="animate-pulse bg-muted rounded h-12" />
        ))}
      </div>
    );
  }

  return (
    <div className="mt-4">
      {actionError && (
        <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError}
        </div>
      )}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>이름</TableHead>
            <TableHead>이메일</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>가입일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                계정이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.displayName}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell>
                  <Badge variant={user.isActive ? "default" : "secondary"}>
                    {user.isActive ? "활성" : "비활성"}
                  </Badge>
                </TableCell>
                <TableCell>{formatDate(user.createdAt)}</TableCell>
                <TableCell>
                  {user.isActive ? (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          비활성화
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>계정을 비활성화하시겠습니까?</AlertDialogTitle>
                          <AlertDialogDescription>
                            비활성화하면 {user.displayName} 계정의 모든 활동이 즉시
                            차단됩니다. 기존 데이터는 보존됩니다. 재활성화로 복구할 수
                            있습니다.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>취소</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => deactivate.mutate({ userId: user.id })}
                          >
                            비활성화
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  ) : (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          재활성화
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>계정을 재활성화하시겠습니까?</AlertDialogTitle>
                          <AlertDialogDescription>
                            {user.displayName} 계정의 모든 API 활동이 즉시 복구됩니다.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>취소</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => activate.mutate({ userId: user.id })}
                          >
                            재활성화
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  )}
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
