"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { useConversationStore } from "@/store/conversation-store";

function dayLabel(timestamp: number) {
  const date = new Date(timestamp);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (sameDay) {
    return "今天";
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return "昨天";
  }
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`;
}

function timeLabel(timestamp: number) {
  return new Date(timestamp).toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false });
}

export function ChatHistory() {
  const { ready, conversations } = useConversationStore();
  const [query, setQuery] = useState("");

  const grouped = useMemo(() => {
    const filtered = conversations.filter((conversation) => conversation.title.includes(query.trim()) || conversation.messages.some((message) => message.content.includes(query.trim())));
    const buckets = new Map<string, typeof filtered>();
    for (const conversation of filtered) {
      const key = dayLabel(conversation.updatedAt);
      buckets.set(key, [...(buckets.get(key) ?? []), conversation]);
    }
    return [...buckets.entries()];
  }, [conversations, query]);

  if (!ready) {
    return <p className="px-8 py-10 text-[#8a968f]">載入對話紀錄中…</p>;
  }

  return (
    <section className="px-5 py-8 sm:px-10 lg:px-16">
      <h1 className="text-[32px] font-bold leading-[44px]">對話紀錄</h1>
      <p className="mt-1 text-[#506058]">回到任何一次好奇，繼續你的探索。</p>

      <div className="mt-6 flex max-w-[860px] items-center gap-3">
        <input
          className="h-12 flex-1 rounded-full border border-[#dde3df] bg-white px-5 outline-none"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜尋問題或主題"
        />
        <span className="text-sm text-[#177049]">全部</span>
      </div>

      {conversations.length === 0 ? (
        <p className="mt-10 text-[#8a968f]">還沒有對話。按「新對話」開始後，紀錄會出現在這裡。</p>
      ) : (
        <div className="mt-8 max-w-[860px] space-y-8">
          {grouped.map(([label, items]) => (
            <section key={label}>
              <h2 className="mb-3 text-sm text-[#8a968f]">{label}</h2>
              <ul className="space-y-3">
                {items.map((conversation) => (
                  <li key={conversation.id}>
                    <Link className="flex items-center gap-4 rounded-[22px] border border-[#edf0ee] bg-white px-5 py-4 hover:border-[#cfe8da]" href={`/chat/${conversation.id}`}>
                      <span className="w-12 shrink-0 text-sm text-[#8a968f]">{timeLabel(conversation.updatedAt)}</span>
                      <span className="min-w-0 flex-1 truncate font-medium">{conversation.title}</span>
                      <span className="rounded-full bg-[#ecf9f3] px-3 py-1 text-xs text-[#177049]">文字</span>
                      <span aria-hidden="true">→</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </section>
  );
}
