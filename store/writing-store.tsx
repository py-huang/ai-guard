"use client";

import { createContext, type ReactNode, useContext, useEffect, useState } from "react";

import type { GenerateWritingResponse, WritingDraft, WritingMessage } from "@/lib/writing";

const STORAGE_KEY = "ai-guard-writing-drafts";

type WritingStoreValue = {
  ready: boolean;
  drafts: WritingDraft[];
  addDraft: (response: GenerateWritingResponse, subject: string) => void;
  appendMessage: (draftId: string, message: WritingMessage) => void;
  summarizeStage: (draftId: string, stageIndex: number, content: string, summarizedUserMessageCount: number) => void;
  selectStage: (draftId: string, stageIndex: number) => void;
  advanceStage: (draftId: string) => void;
};

const WritingStoreContext = createContext<WritingStoreValue | null>(null);

function updateDraft(drafts: WritingDraft[], draftId: string, update: (draft: WritingDraft) => WritingDraft) {
  return drafts.map((draft) => (draft.id === draftId ? update(draft) : draft));
}

function isWritingMessage(value: unknown, stepCount: number): value is WritingMessage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const message = value as WritingMessage;
  return (message.role === "assistant" || message.role === "user")
    && typeof message.content === "string"
    && Number.isInteger(message.stageIndex)
    && message.stageIndex >= 0
    && message.stageIndex < stepCount;
}

function isWritingDraft(value: unknown): value is WritingDraft {
  if (!value || typeof value !== "object") {
    return false;
  }

  const draft = value as WritingDraft;
  return typeof draft.id === "string"
    && typeof draft.subject === "string"
    && Number.isFinite(draft.updatedAt)
    && Array.isArray(draft.steps)
    && draft.steps.length > 0
    && draft.steps.every((step) => typeof step === "string")
    && Array.isArray(draft.outline)
    && draft.outline.length === draft.steps.length
    && draft.outline.every((item) => item
      && typeof item.stage === "string"
      && typeof item.content === "string"
      && (item.summarizedUserMessageCount === undefined || (Number.isInteger(item.summarizedUserMessageCount) && item.summarizedUserMessageCount >= 0)))
    && Array.isArray(draft.chat_history)
    && draft.chat_history.every((message) => isWritingMessage(message, draft.steps.length))
    && Number.isInteger(draft.currentStageIndex)
    && draft.currentStageIndex >= 0
    && draft.currentStageIndex < draft.steps.length;
}

function readStoredDrafts(): WritingDraft[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? (JSON.parse(raw) as unknown) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }

    const seen = new Set<string>();
    return parsed.filter((draft): draft is WritingDraft => {
      if (!isWritingDraft(draft) || seen.has(draft.id)) {
        return false;
      }

      seen.add(draft.id);
      return true;
    });
  } catch {
    return [];
  }
}

function persistDrafts(drafts: WritingDraft[]) {
  const ordered = [...drafts].sort((left, right) => right.updatedAt - left.updatedAt);

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ordered));
    return;
  } catch {
    const trimmed = ordered.slice(0, 20).map((draft) => ({
      ...draft,
      chat_history: draft.chat_history.slice(-30),
    }));

    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }
}

export function WritingStoreProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [drafts, setDrafts] = useState<WritingDraft[]>([]);

  useEffect(() => {
    setDrafts(readStoredDrafts());
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) {
      persistDrafts(drafts);
    }
  }, [drafts, ready]);

  function addDraft(response: GenerateWritingResponse, subject: string) {
    const draft: WritingDraft = {
      id: response.theme_id,
      subject,
      updatedAt: Date.now(),
      steps: response.steps,
      outline: response.outline,
      currentStageIndex: 0,
      chat_history: [{ role: "assistant", content: response.init_question, stageIndex: 0 }],
    };

    setDrafts((currentDrafts) => [draft, ...currentDrafts.filter((currentDraft) => currentDraft.id !== draft.id)]);
  }

  function appendMessage(draftId: string, message: WritingMessage) {
    setDrafts((currentDrafts) =>
      updateDraft(currentDrafts, draftId, (draft) => ({ ...draft, updatedAt: Date.now(), chat_history: [...draft.chat_history, message] }))
    );
  }

  function summarizeStage(draftId: string, stageIndex: number, content: string, summarizedUserMessageCount: number) {
    setDrafts((currentDrafts) =>
      updateDraft(currentDrafts, draftId, (draft) => ({
        ...draft,
        updatedAt: Date.now(),
        outline: draft.outline.map((item, index) => (index === stageIndex ? { ...item, content, summarizedUserMessageCount } : item)),
      }))
    );
  }

  function selectStage(draftId: string, stageIndex: number) {
    setDrafts((currentDrafts) =>
      updateDraft(currentDrafts, draftId, (draft) => ({
        ...draft,
        updatedAt: Date.now(),
        currentStageIndex: Math.min(Math.max(stageIndex, 0), draft.steps.length - 1),
      }))
    );
  }

  function advanceStage(draftId: string) {
    setDrafts((currentDrafts) =>
      updateDraft(currentDrafts, draftId, (draft) => ({
        ...draft,
        updatedAt: Date.now(),
        currentStageIndex: Math.min(draft.currentStageIndex + 1, draft.steps.length - 1),
      }))
    );
  }

  return (
    <WritingStoreContext.Provider value={{ ready, drafts, addDraft, appendMessage, summarizeStage, selectStage, advanceStage }}>
      {children}
    </WritingStoreContext.Provider>
  );
}

export function useWritingStore() {
  const context = useContext(WritingStoreContext);

  if (!context) {
    throw new Error("useWritingStore must be used within a WritingStoreProvider");
  }

  return context;
}