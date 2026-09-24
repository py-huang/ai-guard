"use client";

import { cn } from "@/lib/utils";
import { useReadingAssist } from "@/hooks/use-reading-assist";

export function ReadingAssistToggle() {
  const { zhuyinEnabled, toggleZhuyin } = useReadingAssist();

  return (
    <button
      aria-label="切換注音顯示"
      aria-pressed={zhuyinEnabled}
      className={cn(
        "relative z-50 h-[34px] shrink-0 rounded-[17px] px-3 text-xs font-medium text-[#25324a] transition-colors",
        zhuyinEnabled ? "bg-[#c9e4ff]" : "bg-[#ecf6ff]"
      )}
      data-zhuyin-skip=""
      onClick={toggleZhuyin}
      title={zhuyinEnabled ? "關閉注音顯示" : "顯示注音"}
      type="button"
    >
      閱讀輔助
    </button>
  );
}
