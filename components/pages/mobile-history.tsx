"use client";

import Link from "next/link";

import { useConversationStore } from "@/store/conversation-store";

export function MobileHistoryPage() {
  const { ready, conversations } = useConversationStore();
  const recent = [...conversations].sort((left, right) => right.updatedAt - left.updatedAt);

  return (
    <section className="flex h-full flex-col bg-[#fffcf7]">
      <header className="flex h-16 shrink-0 items-center bg-white px-4">
        <h1 className="text-[18px] font-bold leading-7">對話紀錄</h1>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {recent.length ? (
          <ul className="divide-y divide-[#dde3df] rounded-[20px] border border-[#dde3df] bg-white px-4">
            {recent.map((conversation) => (
              <li key={conversation.id}>
                <Link className="flex min-h-[64px] items-center gap-3" href={`/mobile/history/${conversation.id}`}>
                  <img src="/mobile/topic-writing-record.svg" width="24" height="24" alt="" aria-hidden="true" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[14px] font-medium leading-5">{conversation.title}</span>
                    <span className="block text-[11px] leading-[18px] text-[#506058]">{conversation.topic?.trim() || "文字"} · {formatTime(conversation.updatedAt)}</span>
                  </span>
                  <img src="/mobile/chevron-right.svg" width="20" height="20" alt="" aria-hidden="true" />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-[20px] border border-[#dde3df] bg-white p-4 text-[13px] leading-5 text-[#506058]">
            {ready ? "還沒有對話紀錄" : "載入對話紀錄中…"}
          </p>
        )}
      </div>
    </section>
  );
}

export function MobileHistoryDetail({ conversationId }: { conversationId: string }) {
  const { ready, getConversation } = useConversationStore();
  const conversation = getConversation(conversationId);

  return (
    <section className="flex h-full flex-col bg-[#fffcf7]">
      <header className="flex h-16 shrink-0 items-center gap-3 bg-white px-4">
        <Link className="grid size-10 shrink-0 place-items-center rounded-full text-[#177049]" href="/mobile/history/" aria-label="返回對話紀錄">
          <span aria-hidden="true">‹</span>
        </Link>
        <h1 className="min-w-0 truncate text-[16px] font-bold leading-6">{conversation?.title || "對話內容"}</h1>
      </header>
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {!ready ? <p className="text-[13px] leading-5 text-[#506058]">載入對話中…</p> : null}
        {ready && !conversation ? <p className="text-[13px] leading-5 text-[#506058]">找不到這筆對話。</p> : null}
        {conversation?.messages.filter((message) => message.role !== "system-note").map((message, index) => (
          <div className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`} key={`${message.role}-${index}`}>
            <p className={`max-w-[84%] whitespace-pre-wrap break-words rounded-2xl px-3 py-2 text-[14px] leading-[22px] ${message.role === "user" ? "rounded-br-md bg-[#ecf9f3]" : "rounded-bl-md border border-[#dde3df] bg-white"}`}>
              {message.content || (message.hasImage ? "圖片提問" : "")}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

function formatTime(timestamp: number) {
  return new Date(timestamp).toLocaleString("zh-TW", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false });
}