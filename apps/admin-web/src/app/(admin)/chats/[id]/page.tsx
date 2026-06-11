"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";

import {
  useGetAdminChatRoom,
  useListAdminChatMessages,
  type MessageRead,
} from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  params: Promise<{ id: string }>;
}

export default function ChatDetailPage({ params }: Props) {
  const { id } = use(params);
  return <ChatDetail chatRoomId={id} />;
}

function ChatDetail({ chatRoomId }: { chatRoomId: string }) {
  const [before, setBefore] = useState<string | undefined>(undefined);
  const [allMessages, setAllMessages] = useState<MessageRead[]>([]);

  const {
    data: room,
    isLoading: roomLoading,
    isError: roomIsError,
    error: roomErr,
  } = useGetAdminChatRoom(chatRoomId);

  const {
    data: messagesPage,
    isLoading: messagesLoading,
    isFetching,
    isError: messagesIsError,
    error: messagesErr,
  } = useListAdminChatMessages(chatRoomId, { limit: 50, before });

  useEffect(() => {
    if (!messagesPage?.items) return;
    if (!before) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAllMessages(messagesPage.items);
    } else {
      setAllMessages((prev) => {
        const existingIds = new Set(prev.map((m) => m.id));
        return [...messagesPage.items.filter((m) => !existingIds.has(m.id)), ...prev];
      });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messagesPage]);

  const formatTime = (iso: string) =>
    new Date(iso).toLocaleString("ko-KR", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });

  const getSenderName = (senderId: string): string => {
    if (!room) return senderId.substring(0, 8);
    if (senderId === room.customerId) return room.customerDisplayName;
    if (senderId === room.proId) return room.proDisplayName;
    return senderId.substring(0, 8);
  };

  const isCustomer = (senderId: string): boolean =>
    room ? senderId === room.customerId : false;

  const isError = roomIsError || messagesIsError;
  const errorMessage =
    ((roomErr ?? messagesErr) as { message?: string })?.message ??
    "채팅 내역을 불러오지 못했습니다.";

  if (roomLoading || (messagesLoading && allMessages.length === 0)) {
    return (
      <main className="max-w-screen-xl mx-auto p-6">
        <div className="animate-pulse bg-muted rounded h-64" />
      </main>
    );
  }

  if (isError) {
    return (
      <main className="max-w-screen-xl mx-auto p-6">
        <div className="mb-4">
          <Link href="/chats">
            <Button variant="ghost" size="sm">← 목록으로</Button>
          </Link>
        </div>
        <p className="text-destructive">{errorMessage}</p>
      </main>
    );
  }

  return (
    <main className="max-w-screen-xl mx-auto p-6">
      <div className="mb-4">
        <Link href="/chats">
          <Button variant="ghost" size="sm">← 목록으로</Button>
        </Link>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-xl">
            채팅방 상세 —{" "}
            <span className="font-mono text-base">{chatRoomId.substring(0, 8)}</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {room && (
            <div className="flex gap-6 text-sm text-muted-foreground">
              <span>
                고객: <strong className="text-foreground">{room.customerDisplayName}</strong>
              </span>
              <span>
                고수: <strong className="text-foreground">{room.proDisplayName}</strong>
              </span>
              <span>
                연관 요청:{" "}
                <strong className="font-mono text-foreground">
                  {room.serviceRequest
                    ? room.serviceRequest.id.substring(0, 8)
                    : room.serviceRequestId.substring(0, 8)}
                </strong>
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      {messagesPage?.nextCursor && (
        <div className="mb-3 flex justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setBefore(messagesPage.nextCursor ?? undefined)}
            disabled={isFetching}
          >
            {isFetching ? "불러오는 중..." : "이전 메시지 보기"}
          </Button>
        </div>
      )}

      <div className="space-y-3 max-h-[60vh] overflow-y-auto border rounded-md p-4 bg-muted/20">
        {allMessages.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">메시지가 없습니다.</p>
        ) : (
          allMessages.map((msg) => {
            const customer = isCustomer(msg.senderId);
            return (
              <div
                key={msg.id}
                className={`flex flex-col ${customer ? "items-start" : "items-end"}`}
              >
                <span className="text-xs text-muted-foreground mb-1">
                  {getSenderName(msg.senderId)} · {formatTime(msg.createdAt)}
                </span>
                <div
                  className={`max-w-[70%] rounded-lg px-3 py-2 text-sm ${
                    customer
                      ? "bg-background border"
                      : "bg-primary text-primary-foreground"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}
      </div>

      <p className="mt-4 text-xs text-muted-foreground text-center">
        읽기 전용 — 메시지 전송 불가
      </p>
    </main>
  );
}
