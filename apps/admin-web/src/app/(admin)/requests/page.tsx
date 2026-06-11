"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
  getListAdminServiceRequestsQueryKey,
  useAdminChangeServiceRequestStatus,
  useAdminHideServiceRequest,
  useListAdminServiceRequests,
  type ServiceRequestAdminRead,
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
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function RequestsPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">서비스 요청 관리</h1>
      <RequestsTable />
    </main>
  );
}

function RequestsTable() {
  const [includeHidden, setIncludeHidden] = useState(false);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<ServiceRequestAdminRead[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const handleToggleHidden = (checked: boolean) => {
    setIncludeHidden(checked);
    setCursor(undefined);
    setAllItems([]);
  };

  const { data, isLoading, isFetching } = useListAdminServiceRequests({
    limit: 20,
    cursor,
    include_hidden: includeHidden,
  });

  // eslint-disable-next-line react-hooks/exhaustive-deps
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
  }, [data]);

  const invalidateList = () => {
    setActionError(null);
    queryClient.invalidateQueries({
      queryKey: getListAdminServiceRequestsQueryKey(),
    });
    setCursor(undefined);
    setAllItems([]);
  };

  const changeStatus = useAdminChangeServiceRequestStatus({
    mutation: {
      onSuccess: invalidateList,
      onError: (error: unknown) => {
        setActionError(
          error instanceof Error ? error.message : "상태 변경 중 오류가 발생했습니다.",
        );
      },
    },
  });

  const hideRequest = useAdminHideServiceRequest({
    mutation: {
      onSuccess: invalidateList,
      onError: (error: unknown) => {
        setActionError(
          error instanceof Error ? error.message : "숨김 처리 중 오류가 발생했습니다.",
        );
      },
    },
  });

  const STATUS_LABEL: Record<string, string> = {
    open: "대기중",
    matched: "매칭됨",
    completed: "완료",
    cancelled: "취소됨",
  };

  const STATUS_VARIANT: Record<string, "default" | "outline" | "secondary" | "destructive"> = {
    open: "default",
    matched: "outline",
    completed: "secondary",
    cancelled: "destructive",
  };

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
      <div className="flex items-center gap-2 mb-4">
        <Checkbox
          id="include-hidden"
          checked={includeHidden}
          onCheckedChange={(checked) => handleToggleHidden(checked === true)}
        />
        <Label htmlFor="include-hidden" className="cursor-pointer">
          숨김 요청 포함
        </Label>
      </div>

      {actionError && (
        <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {actionError}
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>요청 ID</TableHead>
            <TableHead>카테고리</TableHead>
            <TableHead>지역</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>숨김여부</TableHead>
            <TableHead>생성일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                서비스 요청이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((req) => (
              <TableRow key={req.id} className={req.deletedAt ? "opacity-50" : ""}>
                <TableCell className="font-mono text-xs">
                  {String(req.id).substring(0, 8)}
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {String(req.categoryId).substring(0, 8)}
                </TableCell>
                <TableCell>{req.region}</TableCell>
                <TableCell>
                  <Badge variant={STATUS_VARIANT[req.status] ?? "default"}>
                    {STATUS_LABEL[req.status] ?? req.status}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={req.deletedAt ? "secondary" : "default"}>
                    {req.deletedAt ? "숨김" : "표시"}
                  </Badge>
                </TableCell>
                <TableCell>{formatDate(req.createdAt)}</TableCell>
                <TableCell>
                  <div className="flex gap-2 flex-wrap">
                    {req.status === "open" && (
                      <StatusActionButton
                        label="취소"
                        description={`요청 ${String(req.id).substring(0, 8)}의 상태를 취소로 변경합니다.`}
                        onConfirm={() =>
                          changeStatus.mutate({
                            requestId: req.id,
                            data: { action: "cancel" },
                          })
                        }
                        variant="outline"
                      />
                    )}
                    {req.status === "matched" && (
                      <>
                        <StatusActionButton
                          label="완료"
                          description={`요청 ${String(req.id).substring(0, 8)}을 완료 처리합니다.`}
                          onConfirm={() =>
                            changeStatus.mutate({
                              requestId: req.id,
                              data: { action: "complete" },
                            })
                          }
                          variant="outline"
                        />
                        <StatusActionButton
                          label="취소"
                          description={`요청 ${String(req.id).substring(0, 8)}의 상태를 취소로 변경합니다.`}
                          onConfirm={() =>
                            changeStatus.mutate({
                              requestId: req.id,
                              data: { action: "cancel" },
                            })
                          }
                          variant="outline"
                        />
                      </>
                    )}
                    {!req.deletedAt && (
                      <StatusActionButton
                        label="숨김"
                        description={`요청 ${String(req.id).substring(0, 8)}을 숨김 처리합니다. 연결된 견적·채팅은 보존됩니다.`}
                        onConfirm={() => hideRequest.mutate({ requestId: req.id })}
                        variant="destructive"
                      />
                    )}
                    {req.status !== "open" &&
                      req.status !== "matched" &&
                      req.deletedAt && (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                  </div>
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

function StatusActionButton({
  label,
  description,
  onConfirm,
  variant = "outline",
}: {
  label: string;
  description: string;
  onConfirm: () => void;
  variant?: "outline" | "destructive";
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant={variant} size="sm">
          {label}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>확인</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>취소</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>확인</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
