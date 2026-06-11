"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  getListAdminsQueryKey,
  useCreateAdmin,
  useDeactivateAdmin,
  useListAdmins,
  type UserRead,
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

export default function AdminsPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">관리자 계정 관리</h1>
      <AddAdminForm />
      <AdminTable />
    </main>
  );
}

function AddAdminForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const createAdmin = useCreateAdmin({
    mutation: {
      onSuccess: () => {
        setEmail("");
        setPassword("");
        setDisplayName("");
        setFormError(null);
        queryClient.invalidateQueries({ queryKey: getListAdminsQueryKey() });
      },
      onError: (error: unknown) => {
        setFormError(error instanceof Error ? error.message : "관리자 추가 중 오류가 발생했습니다.");
      },
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    createAdmin.mutate({ data: { email, password, displayName } });
  };

  return (
    <Card className="mb-8">
      <CardHeader>
        <CardTitle>신규 관리자 추가</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex gap-3 flex-wrap items-end">
          <div className="grid gap-1.5">
            <Label htmlFor="admin-email">이메일</Label>
            <Input
              id="admin-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="admin@example.com"
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="admin-password">비밀번호</Label>
            <Input
              id="admin-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="admin-displayName">표시명</Label>
            <Input
              id="admin-displayName"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </div>
          <Button type="submit" disabled={createAdmin.isPending}>
            {createAdmin.isPending ? "추가 중..." : "관리자 추가"}
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

function AdminTable() {
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<UserRead[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data, isLoading, isFetching } = useListAdmins({ limit: 20, cursor });

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
    queryClient.invalidateQueries({ queryKey: getListAdminsQueryKey() });
    setCursor(undefined);
    setAllItems([]);
  };

  const deactivate = useDeactivateAdmin({
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
        {Array.from({ length: 3 }).map((_, i) => (
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
                관리자 계정이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((admin) => (
              <TableRow key={admin.id}>
                <TableCell className="font-medium">
                  {admin.displayName}
                  {admin.isSeed && (
                    <Badge variant="outline" className="ml-2 text-xs">
                      시드
                    </Badge>
                  )}
                </TableCell>
                <TableCell>{admin.email}</TableCell>
                <TableCell>
                  <Badge variant={admin.isActive ? "default" : "secondary"}>
                    {admin.isActive ? "활성" : "비활성"}
                  </Badge>
                </TableCell>
                <TableCell>{formatDate(admin.createdAt)}</TableCell>
                <TableCell>
                  {admin.isSeed ? (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled
                      title="시드 관리자는 비활성화할 수 없습니다"
                    >
                      비활성화 불가
                    </Button>
                  ) : admin.isActive ? (
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          비활성화
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>관리자를 비활성화하시겠습니까?</AlertDialogTitle>
                          <AlertDialogDescription>
                            비활성화하면 {admin.displayName} 관리자가 즉시 콘솔에서
                            로그아웃되고 재로그인이 불가능합니다.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>취소</AlertDialogCancel>
                          <AlertDialogAction
                            onClick={() => deactivate.mutate({ adminId: admin.id })}
                          >
                            비활성화
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  ) : (
                    <span className="text-sm text-muted-foreground">비활성</span>
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
