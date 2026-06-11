"use client";

import { useEffect, useReducer, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";

import {
  list_messages,
  send_message,
  useReadMe,
  type MessageRead,
} from "@gosoom/api-client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function messagesReducer(state: MessageRead[], incoming: MessageRead[]) {
  const existingIds = new Set(state.map((m) => m.id));
  return [...state, ...incoming.filter((m) => !existingIds.has(m.id))];
}

export default function ChatRoomPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: me, isError: meError } = useReadMe();

  const lastIdRef = useRef<string | undefined>(undefined);
  const [allMessages, dispatch] = useReducer(messagesReducer, []);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [content, setContent] = useState("");

  useEffect(() => {
    if (meError) router.push("/login");
  }, [meError, router]);

  // 증분 폴링 — 쿼리 키에 lastId 포함 금지 (refetchInterval 리셋 방지)
  const { data: pollData } = useQuery({
    queryKey: ["chat-messages", id],
    queryFn: ({ signal }) =>
      list_messages(id, { after: lastIdRef.current }, undefined, signal),
    refetchInterval: 2000,
    enabled: !!id,
  });

  useEffect(() => {
    if (pollData?.items?.length) {
      dispatch(pollData.items);
      lastIdRef.current = pollData.items[pollData.items.length - 1].id;
    }
  }, [pollData]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [allMessages]);

  const sendMutation = useMutation({
    mutationFn: (c: string) => send_message(id, { content: c }),
    onSuccess: (newMsg) => {
      dispatch([newMsg]);
      lastIdRef.current = newMsg.id;
      setContent("");
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    sendMutation.mutate(content.trim());
  };

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* 메시지 목록 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {allMessages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.senderId === me?.id ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-xs px-3 py-2 rounded-xl text-sm leading-relaxed ${
                msg.senderId === me?.id
                  ? "bg-primary text-primary-foreground rounded-br-sm"
                  : "bg-muted text-foreground rounded-bl-sm"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 전송 폼 */}
      <div className="border-t bg-background p-4">
        {sendMutation.isError && (
          <p className="text-destructive text-xs mb-2" role="alert">
            메시지 전송에 실패했습니다.
          </p>
        )}
        <form onSubmit={handleSend} className="flex gap-2">
          <Input
            type="text"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="메시지를 입력하세요"
            disabled={sendMutation.isPending}
            className="flex-1"
          />
          <Button
            type="submit"
            size="sm"
            disabled={sendMutation.isPending || !content.trim()}
          >
            {sendMutation.isPending ? "전송 중…" : "전송"}
          </Button>
        </form>
      </div>
    </div>
  );
}
