"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  useListAdminChatRooms,
  type ChatRoomAdminRead,
} from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function ChatsPage() {
  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <h1 className="text-2xl font-bold tracking-tight mb-6">채팅 내역</h1>
      <ChatRoomsTable />
    </main>
  );
}

function ChatRoomsTable() {
  const router = useRouter();
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allItems, setAllItems] = useState<ChatRoomAdminRead[]>([]);

  const { data, isLoading, isFetching, isError, error } = useListAdminChatRooms({
    limit: 20,
    cursor,
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

  if (isError) {
    return (
      <p className="text-destructive py-8 text-center">
        {(error as { message?: string })?.message ?? "채팅 목록을 불러오지 못했습니다."}
      </p>
    );
  }

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>채팅방 ID</TableHead>
            <TableHead>고객</TableHead>
            <TableHead>고수</TableHead>
            <TableHead>연관 요청</TableHead>
            <TableHead>생성일</TableHead>
            <TableHead>액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {allItems.length === 0 && !isFetching ? (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                채팅 내역이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            allItems.map((room) => (
              <TableRow key={room.id}>
                <TableCell className="font-mono text-xs">
                  {room.id.substring(0, 8)}
                </TableCell>
                <TableCell>{room.customerDisplayName}</TableCell>
                <TableCell>{room.proDisplayName}</TableCell>
                <TableCell className="font-mono text-xs">
                  {room.serviceRequest
                    ? room.serviceRequest.id.substring(0, 8)
                    : room.serviceRequestId.substring(0, 8)}
                </TableCell>
                <TableCell>{formatDate(room.createdAt)}</TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/chats/${room.id}`)}
                  >
                    상세보기
                  </Button>
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
