"use client";

import { createContext, useContext, useLayoutEffect, useMemo, useState, type ReactNode } from "react";

import { READING_ASSIST_ZHUYIN_KEY, type ReadingAssistState } from "@/lib/reading-assist";

const ReadingAssistContext = createContext<ReadingAssistState | null>(null);

export function ReadingAssistProvider({ children }: { children: ReactNode }) {
  const [zhuyinEnabled, setZhuyinEnabledState] = useState(false);

  useLayoutEffect(() => {
    setZhuyinEnabledState(window.localStorage.getItem(READING_ASSIST_ZHUYIN_KEY) === "1");
  }, []);

  useLayoutEffect(() => {
    document.documentElement.classList.toggle("zhuyin-on", zhuyinEnabled);
  }, [zhuyinEnabled]);

  const value = useMemo<ReadingAssistState>(() => {
    function setZhuyinEnabled(enabled: boolean) {
      setZhuyinEnabledState(enabled);
      window.localStorage.setItem(READING_ASSIST_ZHUYIN_KEY, enabled ? "1" : "0");
    }

    return {
      zhuyinEnabled,
      setZhuyinEnabled,
      toggleZhuyin: () => setZhuyinEnabled(!zhuyinEnabled),
    };
  }, [zhuyinEnabled]);

  return <ReadingAssistContext.Provider value={value}>{children}</ReadingAssistContext.Provider>;
}

export function useReadingAssist() {
  const value = useContext(ReadingAssistContext);
  if (!value) {
    throw new Error("useReadingAssist must be used within ReadingAssistProvider");
  }
  return value;
}
