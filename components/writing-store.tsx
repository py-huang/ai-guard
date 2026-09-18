"use client";

import { createContext, type ReactNode, useContext, useState } from "react";

import type { GenerateWritingResponse, WritingDraft, WritingMessage } from "@/lib/writing";

type WritingStoreValue = {
  drafts: WritingDraft[];
  addDraft: (response: GenerateWritingResponse, subject: string) => void;
  appendMessage: (draftId: string, message: WritingMessage) => void;
  summarizeStage: (draftId: string, stageIndex: number, content: string) => void;
  advanceStage: (draftId: string) => void;
};

const WritingStoreContext = createContext<WritingStoreValue | null>(null);

function updateDraft(drafts: WritingDraft[], draftId: string, update: (draft: WritingDraft) => WritingDraft) {
  return drafts.map((draft) => (draft.id === draftId ? update(draft) : draft));
}

export function WritingStoreProvider({ children }: { children: ReactNode }) {
  const [drafts, setDrafts] = useState<WritingDraft[]>([]);

  function addDraft(response: GenerateWritingResponse, subject: string) {
    setDrafts((currentDrafts) => [
      ...currentDrafts,
      {
        id: response.theme_id,
        subject,
        steps: response.steps,
        outline: response.outline,
        currentStageIndex: 0,
        chat_history: [{ role: "assistant", content: response.init_question, stageIndex: 0 }],
      },
    ]);
  }

  function appendMessage(draftId: string, message: WritingMessage) {
    setDrafts((currentDrafts) =>
      updateDraft(currentDrafts, draftId, (draft) => ({ ...draft, chat_history: [...draft.chat_history, message] }))
    );
  }

  function summarizeStage(draftId: string, stageIndex: number, content: string) {
    setDrafts((currentDrafts) =>
      updateDraft(currentDrafts, draftId, (draft) => ({
        ...draft,
        outline: draft.outline.map((item, index) => (index === stageIndex ? { ...item, content } : item)),
      }))
    );
  }

  function advanceStage(draftId: string) {
    setDrafts((currentDrafts) =>
      updateDraft(currentDrafts, draftId, (draft) => ({
        ...draft,
        currentStageIndex: Math.min(draft.currentStageIndex + 1, draft.steps.length - 1),
      }))
    );
  }

  return (
    <WritingStoreContext.Provider value={{ drafts, addDraft, appendMessage, summarizeStage, advanceStage }}>
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