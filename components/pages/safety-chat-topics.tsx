"use client";

import { useRouter } from "next/navigation";

import { hasPii } from "@/lib/pii-preview";
import { useConversationStore } from "@/store/conversation-store";

type SafetyChatTopicsProps = {
  heading: string;
  topics: string[];
  promptPrefix?: string;
};

export function SafetyChatTopics({ heading, topics, promptPrefix }: SafetyChatTopicsProps) {
  const router = useRouter();
  const { createConversation } = useConversationStore();

  function startChat(topic: string) {
    const prompt = `${promptPrefix ?? heading} ${topic.replace(/[?？]$/, "")}`;
    const conversation = createConversation(hasPii(prompt) ? "新對話" : prompt);
    sessionStorage.setItem("ai-guard-pending", prompt);
    router.push(`/chat/${conversation.id}`);
  }

  return <>
    {topics.map((topic) => (
      <li key={topic}>
        <button
          className="block w-full rounded text-left font-[inherit] text-inherit hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#c02d32]"
          onClick={() => startChat(topic)}
          type="button"
        >
          —　{topic}
        </button>
      </li>
    ))}
  </>;
}