"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useConversationStore } from "@/store/conversation-store";
import { useWritingStore } from "@/store/writing-store";

type RecentItem = {
  id: string;
  title: string;
  updatedAt: number;
  href: string;
  mode: "chat" | "writing";
};

export function RecentConversations() {
  const { ready: conversationsReady, conversations } = useConversationStore();
  const { ready: draftsReady, drafts } = useWritingStore();
  const recent = useMemo<RecentItem[]>(
    () => [
      ...conversations.map((conversation) => ({
        id: conversation.id,
        title: conversation.title,
        updatedAt: conversation.updatedAt,
        href: `/chat/${conversation.id}`,
        mode: "chat" as const,
      })),
      ...drafts.map((draft) => ({
        id: draft.id,
        title: draft.subject,
        updatedAt: draft.updatedAt,
        href: `/theme/writing/${draft.id}`,
        mode: "writing" as const,
      })),
    ].sort((left, right) => right.updatedAt - left.updatedAt).slice(0, 4),
    [conversations, drafts],
  );

  if (!conversationsReady || !draftsReady || recent.length === 0) {
    return null;
  }

  return (
    <section className="mt-6 pl-2.5" aria-labelledby="recent-conversations-title">
      <h2 id="recent-conversations-title" className="text-base font-medium text-[#8a968f]">
        最近對話
      </h2>
      <ul className="mt-1.5 space-y-1.5 text-base text-[#506058]">
        {recent.map((item) => (
          <li key={`${item.mode}-${item.id}`}>
            <Link className="flex min-w-0 items-center gap-1.5 hover:text-[#177049]" href={item.href}>
              <span className="truncate whitespace-nowrap">{item.title}</span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
