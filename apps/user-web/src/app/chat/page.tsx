"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import {
  useReadMe,
  useListChatRooms,
  type PageChatRoomListItem,
} from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type ChatRoomListItem = PageChatRoomListItem["items"][0];

export default function ChatListPage() {
  const router = useRouter();
  const { data: me, isError: meError } = useReadMe();
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [allRooms, setAllRooms] = useState<ChatRoomListItem[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null | undefined>(undefined);
  const processedCursors = useRef(new Set<string | undefined>());

  useEffect(() => {
    if (meError) router.push("/login");
  }, [meError, router]);

  const { data, isFetching } = useListChatRooms<PageChatRoomListItem, Error>({
    mine: true,
    cursor,
  });

  useEffect(() => {
    if (isFetching || !data?.items) return;
    if (processedCursors.current.has(cursor)) return;
    processedCursors.current.add(cursor);
    setAllRooms((prev) => cursor === undefined ? data.items : [...prev, ...data.items]);
    setNextCursor(data.nextCursor);
  }, [data, cursor, isFetching]);

  if (!me && !meError) {
    return (
      <main className="max-w-screen-md mx-auto p-6">
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-screen-md mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">채팅 목록</h1>

      {allRooms.length === 0 && !isFetching && (
        <Card>
          <CardContent className="p-10 text-center text-muted-foreground">
            참여 중인 채팅방이 없습니다.
          </CardContent>
        </Card>
      )}

      <div className="space-y-2">
        {allRooms.map((room) => (
          <Card
            key={room.id}
            className="cursor-pointer hover:border-primary transition-colors"
            onClick={() => router.push(`/chat/${room.id}`)}
          >
            <CardContent className="p-4">
              <p className="font-medium text-sm">{room.counterpartDisplayName}</p>
              {room.serviceRequest && (
                <p className="text-sm text-muted-foreground mt-1 truncate">
                  {room.serviceRequest.description}
                </p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {nextCursor && (
        <Button
          variant="outline"
          className="w-full"
          onClick={() => setCursor(nextCursor ?? undefined)}
          disabled={isFetching}
        >
          {isFetching ? "로딩 중…" : "더 보기"}
        </Button>
      )}
    </main>
  );
}
