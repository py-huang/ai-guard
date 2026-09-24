"use client";

import { useEffect, useState } from "react";

import { speakText, stopSpeaking } from "@/lib/speak-text";

type Props = {
  text: string;
};

export function SpeakButton({ text }: Props) {
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
      aria-label={playing ? "停止播放" : "播放這段回覆"}
      className="mt-2 grid size-8 place-items-center rounded-full border border-solid border-[#dde3df] bg-white text-[#c02d32] hover:bg-[#fff0ee]"
      onClick={() => {
        if (playing) {
          stopSpeaking();
          setPlaying(false);
          return;
        }
        setPlaying(speakText(text));
      }}
      title={playing ? "停止播放" : "播放"}
      type="button"
    >
      {playing ? (
        <span className="block h-2.5 w-2.5 rounded-[2px] bg-[#c02d32]" />
      ) : (
        <svg aria-hidden="true" fill="none" height="14" viewBox="0 0 14 14" width="14">
          <path d="M4 2.8v8.4L11.2 7 4 2.8Z" fill="#C02D32" />
        </svg>
      )}
    </button>
  );
}
