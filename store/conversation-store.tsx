"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";

import type { Conversation, ConversationMessage } from "@/types/conversation";

const STORAGE_KEY = "ai-guard-conversations";

type ConversationStoreValue = {
  ready: boolean;
  conversations: Conversation[];
  createConversation: (title: string, firstMessage?: ConversationMessage) => Conversation;
  appendMessage: (id: string, message: ConversationMessage) => void;
  replaceMessages: (id: string, messages: ConversationMessage[]) => void;
  renameConversation: (id: string, title: string) => void;
  getConversation: (id: string) => Conversation | undefined;
};

const ConversationStoreContext = createContext<ConversationStoreValue | null>(null);

function createConversationId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function readStoredConversations(): Conversation[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as Conversation[]) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }

    const seen = new Set<string>();
    return parsed
      .filter((conversation) => conversation && typeof conversation.id === "string" && typeof conversation.title === "string" && Array.isArray(conversation.messages))
      .map((conversation) => {
        if (seen.has(conversation.id)) {
          return { ...conversation, id: createConversationId() };
        }

        seen.add(conversation.id);
        return conversation;
      });
  } catch {
    return [];
  }
}

export function ConversationStoreProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);

  useEffect(() => {
    setConversations(readStoredConversations());
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) {
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations, ready]);

  const createConversation = useCallback((title: string, firstMessage?: ConversationMessage) => {
    const conversation: Conversation = {
      id: createConversationId(),
      title: title.trim() || "新對話",
      updatedAt: Date.now(),
      messages: firstMessage ? [firstMessage] : [],
    };

    setConversations((current) => [conversation, ...current]);
    return conversation;
  }, []);

  function appendMessage(id: string, message: ConversationMessage) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === id
          ? { ...conversation, updatedAt: Date.now(), messages: [...conversation.messages, message] }
          : conversation
      )
    );
  }

  function replaceMessages(id: string, messages: ConversationMessage[]) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === id ? { ...conversation, updatedAt: Date.now(), messages } : conversation
      )
    );
  }

  function renameConversation(id: string, title: string) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === id ? { ...conversation, title: title.trim() || conversation.title, updatedAt: Date.now() } : conversation
      )
    );
  }

  function getConversation(id: string) {
    return conversations.find((conversation) => conversation.id === id);
  }

  return (
    <ConversationStoreContext.Provider value={{ ready, conversations, createConversation, appendMessage, replaceMessages, renameConversation, getConversation }}>
      {children}
    </ConversationStoreContext.Provider>
  );
}

export function useConversationStore() {
  const context = useContext(ConversationStoreContext);

  if (!context) {
    throw new Error("useConversationStore must be used within a ConversationStoreProvider");
  }

  return context;
}
