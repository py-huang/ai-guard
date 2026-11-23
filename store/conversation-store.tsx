"use client";

import { usePathname } from "next/navigation";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useRef, useState } from "react";

import { fetchRemoteSessions, isExpiredRecord, parentToken } from "@/lib/voice-records";
import type { Conversation, ConversationCategory, ConversationMessage, SafetyEvent } from "@/types/conversation";

const STORAGE_KEY = "ai-guard-conversations";

type NewSafetyNotification = {
  conversationId: string;
  event: SafetyEvent;
};

function isVisibleSafetyNotification(event: SafetyEvent) {
  return event.type === "pending" ? event.status === "pending" : !event.acknowledged;
}

type ConversationStoreValue = {
  ready: boolean;
  conversations: Conversation[];
  newSafetyNotification: NewSafetyNotification | null;
  dismissSafetyNotification: (notification: NewSafetyNotification) => void;
  createConversation: (title: string, firstMessage?: ConversationMessage, category?: ConversationCategory) => Conversation;
  appendMessage: (id: string, message: ConversationMessage) => void;
  addSafetyEvent: (id: string, event: SafetyEvent) => void;
  updateSafetyEvent: (id: string, eventId: string, changes: Partial<Pick<SafetyEvent, "status" | "read" | "acknowledged">>) => void;
  replaceMessages: (id: string, messages: ConversationMessage[]) => void;
  setConversationCategory: (id: string, category: ConversationCategory) => void;
  renameConversation: (id: string, title: string) => void;
  removeConversation: (id: string) => void;
  getConversation: (id: string) => Conversation | undefined;
  /** Adds conversations that arrived from elsewhere (a watch call). Known ids are left alone. */
  importConversations: (incoming: Conversation[]) => void;
};

const REMOTE_POLL_MS = 5_000;

function findNewestNotification(
  previous: Conversation[],
  next: Conversation[],
): NewSafetyNotification | null {
  const previousEventIds = new Set(previous.flatMap((conversation) =>
    (conversation.safetyEvents ?? []).map((event) => `${conversation.id}:${event.id}`),
  ));
  let newest: NewSafetyNotification | null = null;

  for (const conversation of next) {
    for (const event of conversation.safetyEvents ?? []) {
      if (previousEventIds.has(`${conversation.id}:${event.id}`) || !isVisibleSafetyNotification(event)) {
        continue;
      }
      if (!newest || event.createdAt >= newest.event.createdAt) {
        newest = { conversationId: conversation.id, event };
      }
    }
  }

  return newest;
}

const ConversationStoreContext = createContext<ConversationStoreValue | null>(null);

function createConversationId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function withoutStoredImages(conversations: Conversation[]): Conversation[] {
  return conversations.map((conversation) => ({
    ...conversation,
    messages: conversation.messages.map((message) => {
      if (!message.imagePreview) {
        return message;
      }

      const { imagePreview: _imagePreview, ...rest } = message;
      return { ...rest, hasImage: true };
    }),
  }));
}

function persistConversations(conversations: Conversation[]) {
  const payload = withoutStoredImages(conversations);

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    return;
  } catch {
    const trimmed = payload.slice(0, 20).map((conversation) => ({
      ...conversation,
      messages: conversation.messages.slice(-30),
    }));

    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }
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
    return withoutStoredImages(
      parsed
        .filter((conversation) => conversation && typeof conversation.id === "string" && typeof conversation.title === "string" && Array.isArray(conversation.messages))
        .map((conversation) => {
          if (seen.has(conversation.id)) {
            return {
              ...conversation,
              id: createConversationId(),
              category: conversation.category === "voice" ? "voice" : "text",
            };
          }

          seen.add(conversation.id);
          return {
            ...conversation,
            category: conversation.category === "voice" ? "voice" : "text",
          };
        }),
    );
  } catch {
    return [];
  }
}

export function ConversationStoreProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [newSafetyNotification, setNewSafetyNotification] = useState<NewSafetyNotification | null>(null);
  const conversationsRef = useRef<Conversation[]>([]);
  const pathname = usePathname();
  const onParentPages = pathname.startsWith("/mobile");

  useEffect(() => {
    // A pairing link (#token=...) is saved and removed from the address bar as soon as any page opens.
    parentToken();
    const storedConversations = readStoredConversations();
    conversationsRef.current = storedConversations;
    setConversations(storedConversations);
    setReady(true);
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) {
        const nextConversations = readStoredConversations();
        const notification = findNewestNotification(conversationsRef.current, nextConversations);
        if (notification) {
          setNewSafetyNotification(notification);
        }
        conversationsRef.current = nextConversations;
        setConversations(nextConversations);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    conversationsRef.current = conversations;
  }, [conversations]);

  useEffect(() => {
    if (!ready) {
      return;
    }

    persistConversations(conversations);
  }, [conversations, ready]);

  const createConversation = useCallback((title: string, firstMessage?: ConversationMessage, category: ConversationCategory = "text") => {
    const conversation: Conversation = {
      id: createConversationId(),
      title: title.trim() || "新對話",
      updatedAt: Date.now(),
      category,
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

  function addSafetyEvent(id: string, event: SafetyEvent) {
    if (isVisibleSafetyNotification(event)) {
      setNewSafetyNotification({ conversationId: id, event });
    }
    setConversations((current) => current.map((conversation) =>
      conversation.id === id
        ? { ...conversation, safetyEvents: [...(conversation.safetyEvents ?? []), event] }
        : conversation
    ));
  }

  const importConversations = useCallback((incoming: Conversation[]) => {
    const known = new Set(conversationsRef.current.map((conversation) => conversation.id));
    const fresh = incoming.filter((conversation) => conversation && !known.has(conversation.id));
    if (fresh.length === 0) {
      return;
    }

    const previous = conversationsRef.current;
    const next = [...fresh, ...previous];
    const notification = findNewestNotification(previous, next);
    conversationsRef.current = next;
    setConversations(next);
    if (notification) {
      setNewSafetyNotification(notification);
    }
  }, []);

  // Watch calls expire on the server after VOICE_RECORD_RETENTION_DAYS; the copies kept in this
  // browser expire on the same schedule. Typed chats are not touched.
  const dropExpiredWatchCalls = useCallback((retentionDays: number) => {
    const current = conversationsRef.current;
    const kept = current.filter((conversation) => !(conversation.channel === "watch" && isExpiredRecord(conversation.updatedAt, retentionDays)));
    if (kept.length !== current.length) {
      conversationsRef.current = kept;
      setConversations(kept);
    }
  }, []);

  // With the sqlite store, calls made on the watch show up here by polling the server. Anything
  // else (local store, no token, server refusing) ends the polling after the first answer.
  useEffect(() => {
    if (!ready || !onParentPages) {
      return;
    }

    const controller = new AbortController();
    let timer: number | undefined;

    const poll = async () => {
      const result = await fetchRemoteSessions(controller.signal);
      if (controller.signal.aborted) {
        return;
      }
      if (result.kind === "sessions" || result.kind === "local") {
        dropExpiredWatchCalls(result.retentionDays);
      }
      if (result.kind === "sessions") {
        importConversations(result.conversations);
      }
      if (result.kind === "sessions" || result.kind === "error") {
        timer = window.setTimeout(poll, REMOTE_POLL_MS);
      }
    };

    void poll();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [ready, onParentPages, importConversations, dropExpiredWatchCalls]);

  const dismissSafetyNotification = useCallback((notification: NewSafetyNotification) => {
    setNewSafetyNotification((current) =>
      current?.conversationId === notification.conversationId && current.event.id === notification.event.id
        ? null
        : current,
    );
  }, []);

  function updateSafetyEvent(id: string, eventId: string, changes: Partial<Pick<SafetyEvent, "status" | "read" | "acknowledged">>) {
    setConversations((current) => current.map((conversation) =>
      conversation.id === id
        ? { ...conversation, safetyEvents: conversation.safetyEvents?.map((event) => {
          if (event.id !== eventId) return event;
          if (changes.status === "cancelled" || changes.status === "completed") {
            const { originalText: _originalText, ...rest } = event;
            return { ...rest, ...changes };
          }
          return { ...event, ...changes };
        }) }
        : conversation
    ));
  }

  function replaceMessages(id: string, messages: ConversationMessage[]) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === id ? { ...conversation, updatedAt: Date.now(), messages } : conversation
      )
    );
  }

  function setConversationCategory(id: string, category: ConversationCategory) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === id ? { ...conversation, category } : conversation
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

  function removeConversation(id: string) {
    setConversations((current) => current.filter((conversation) => conversation.id !== id));
  }

  function getConversation(id: string) {
    return conversations.find((conversation) => conversation.id === id);
  }

  return (
    <ConversationStoreContext.Provider value={{ ready, conversations, newSafetyNotification, dismissSafetyNotification, createConversation, appendMessage, addSafetyEvent, updateSafetyEvent, replaceMessages, setConversationCategory, renameConversation, removeConversation, getConversation, importConversations }}>
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
