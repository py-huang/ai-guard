"use client";

import { useEffect, useState } from "react";
import { Volume2 } from "lucide-react";

import { speakText, stopSpeaking } from "@/lib/speak-text";

type Props = {
  text: string;
  showLabel?: boolean;
};

export function SpeakButton({ text, showLabel = false }: Props) {
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing || typeof window === "undefined") {
      return;
    }

    const timer = window.setInterval(() => {
      if (!window.speechSynthesis.speaking) {
        setPlaying(false);
      }
    }, 300);

    return () => window.clearInterval(timer);
  }, [playing]);

  useEffect(() => {
    return () => stopSpeaking();
  }, []);

  if (!text.trim()) {
    return null;
  }

  return (
    <button
      aria-label={playing ? showLabel ? "停止朗讀" : "停止播放" : showLabel ? "朗讀" : "播放這段回覆"}
      className={showLabel
        ? "inline-flex min-h-11 items-center gap-2 whitespace-nowrap py-2 text-[17px] font-semibold text-[#c02d32] hover:text-[#a9232a]"
        : "mt-2 grid size-8 place-items-center rounded-full border border-solid border-[#dde3df] bg-white text-[#c02d32] hover:bg-[#fff0ee]"}
      onClick={() => {
        if (playing) {
          stopSpeaking();
          setPlaying(false);
          return;
        }
        setPlaying(speakText(text));
      }}
      title={playing ? showLabel ? "停止朗讀" : "停止播放" : showLabel ? "朗讀" : "播放"}
      type="button"
    >
      {showLabel ? (
        <>
          <Volume2 aria-hidden="true" size={26} strokeWidth={2.5} />
          <span>{playing ? "停止朗讀" : "朗讀"}</span>
        </>
      ) : playing ? (
        <span className="block h-2.5 w-2.5 rounded-[2px] bg-[#c02d32]" />
      ) : (
        <svg aria-hidden="true" fill="none" height="14" viewBox="0 0 14 14" width="14">
          <path d="M4 2.8v8.4L11.2 7 4 2.8Z" fill="#C02D32" />
        </svg>
      )}
    </button>
  );
}
