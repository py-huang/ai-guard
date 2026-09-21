"use client";

import Link from "next/link";

import { useConversationStore } from "@/store/conversation-store";

export function RecentConversations() {
  const { ready, conversations } = useConversationStore();
  const recent = conversations.slice(0, 4);

  if (!ready || recent.length === 0) {
    return null;
  }

  return (
    <section className="mt-6 pl-2.5" aria-labelledby="recent-conversations-title">
      <h2 id="recent-conversations-title" className="text-base font-medium text-[#8a968f]">
        最近對話
      </h2>
      <ul className="mt-1.5 space-y-1.5 text-base text-[#506058]">
        {recent.map((conversation) => (
          <li key={conversation.id}>
            <Link className="block truncate hover:text-[#177049]" href={`/chat/${conversation.id}`}>
              {conversation.title}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
