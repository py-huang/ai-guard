"use client";

import { useEffect, useRef, useState } from "react";

type BrowserSpeechRecognition = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript?: string }>> }) => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type BrowserSpeechRecognitionCtor = new () => BrowserSpeechRecognition;

import { pcmToWav } from "@/lib/audio-wav";
import { transcribeVoice } from "@/lib/voice-transcribe";

type VoicePhase = "listening" | "processing" | "preview" | "error";

type Props = {
  onConfirm: (text: string) => void;
  onUseText: () => void;
};

const WAVE_HEIGHTS = [24, 36, 48, 60, 72];
const WAVE_COUNT = 31;
const ACTIVE_BARS = 24;

export function VoiceAsk({ onConfirm, onUseText }: Props) {
  const [phase, setPhase] = useState<VoicePhase>("listening");
  const [seconds, setSeconds] = useState(0);
  const [liveText, setLiveText] = useState("");
  const [previewText, setPreviewText] = useState("");
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const chunksRef = useRef<Float32Array[]>([]);
  const sampleRateRef = useRef(44100);
  const abortRef = useRef<AbortController | null>(null);
  const startedAtRef = useRef(0);
  const speechRef = useRef<BrowserSpeechRecognition | null>(null);
  const liveTextRef = useRef("");

  useEffect(() => {
    void startListening();
    return () => stopHardware();
  }, []);

  useEffect(() => {
    if (phase !== "listening") {
      return;
    }
    const timer = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - startedAtRef.current) / 1000));
    }, 250);
    return () => window.clearInterval(timer);
  }, [phase]);

  function stopHardware() {
    abortRef.current?.abort();
    abortRef.current = null;
    speechRef.current?.stop();
    speechRef.current = null;
    processorRef.current?.disconnect();
    processorRef.current = null;
    void contextRef.current?.close();
    contextRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }

  async function startListening() {
    stopHardware();
    setPhase("listening");
    setSeconds(0);
    setLiveText("");
    setPreviewText("");
    chunksRef.current = [];
    startedAtRef.current = Date.now();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContext();
      await context.resume();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const mute = context.createGain();
      mute.gain.value = 0;
      processor.onaudioprocess = (event) => {
        chunksRef.current.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };
      source.connect(processor);
      processor.connect(mute);
      mute.connect(context.destination);
      streamRef.current = stream;
      contextRef.current = context;
      processorRef.current = processor;
      sampleRateRef.current = context.sampleRate;
      startSpeechPreview();
    } catch {
      setPhase("error");
    }
  }

  function startSpeechPreview() {
    const SpeechAPI = (window as Window & { SpeechRecognition?: BrowserSpeechRecognitionCtor; webkitSpeechRecognition?: BrowserSpeechRecognitionCtor }).SpeechRecognition
      || (window as Window & { webkitSpeechRecognition?: BrowserSpeechRecognitionCtor }).webkitSpeechRecognition;
    if (!SpeechAPI) {
      return;
    }
    const recognition = new SpeechAPI();
    recognition.lang = "zh-TW";
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      let next = "";
      for (let i = 0; i < event.results.length; i += 1) {
        next += event.results[i]?.[0]?.transcript ?? "";
      }
      liveTextRef.current = next.trim();
      setLiveText(liveTextRef.current);
    };
    recognition.onerror = () => undefined;
    speechRef.current = recognition;
    try {
      recognition.start();
    } catch {
      speechRef.current = null;
    }
  }

  function collectRecording() {
    const chunks = chunksRef.current;
    const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const merged = new Float32Array(total);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }
    return pcmToWav(merged, sampleRateRef.current);
  }

  async function finishAndTranscribe() {
    const elapsed = Date.now() - startedAtRef.current;
    setPhase("processing");
    const blob = collectRecording();
    stopHardware();

    if (elapsed < 800 || blob.size < 1000) {
      setPhase("error");
      return;
    }

    const abort = new AbortController();
    abortRef.current = abort;
    try {
      const text = (await transcribeVoice(blob, abort.signal)) || liveTextRef.current;
      if (abort.signal.aborted) {
        return;
      }
      if (!text) {
        setPhase("error");
        return;
      }
      setPreviewText(text);
      setPhase("preview");
    } catch (error) {
      if (abort.signal.aborted) {
        return;
      }
      setPhase("error");
      console.error(error);
    }
  }

  function cancelProcessing() {
    abortRef.current?.abort();
    abortRef.current = null;
    void startListening();
  }

  const copy = copyFor(phase, liveText || previewText);
  const halo = haloFor(phase);

  return (
    <section className="flex min-h-[calc(100dvh-72px)] flex-col px-5 py-6 sm:px-10 lg:px-16">
      <div className="mx-auto flex w-full max-w-[860px] flex-1 flex-col">
        <h1 className="text-lg font-bold leading-7 text-[#13221b]">用聲音提問</h1>

        <div className="relative mt-10 pr-[180px]">
          <p className="text-[13px] font-medium leading-5 text-[#4f9cda]">AI 語音</p>
          <h2 className="mt-2 text-[38px] font-bold leading-[52px] text-[#13221b]">{copy.title}</h2>
          <p className="mt-1 max-w-[640px] text-base font-normal leading-[26px] text-[#506058]">{copy.subtitle}</p>
          <div className="absolute right-0 top-0 grid size-40 place-items-center">
            <img alt="" aria-hidden="true" className="max-w-none" height={halo.haloHeight} src={halo.halo} width={halo.haloWidth} />
            <div className="absolute left-1/2 top-1/2 size-[54px] -translate-x-1/2 -translate-y-1/2 overflow-hidden drop-shadow-[0px_2px_3px_rgba(20,33,26,0.06)]">
              <img alt="" aria-hidden="true" className="absolute left-0 top-0 max-w-none origin-top-left scale-[0.5625]" height={96} src={halo.icon} width={96} />
            </div>
          </div>
        </div>

        <div className="relative mt-8 h-40 overflow-hidden rounded-[24px] border border-solid border-[#dde3df] bg-white">
          <div className="flex h-full items-center justify-center gap-3 overflow-hidden px-7">
            {Array.from({ length: WAVE_COUNT }, (_, index) => {
              const height = WAVE_HEIGHTS[index % WAVE_HEIGHTS.length];
              const active = index < ACTIVE_BARS;
              return (
                <span
                  className={`w-2 shrink-0 rounded-[4px] ${active ? "bg-[#4f9cda]" : "bg-[#dceeff]"} ${phase === "listening" ? "animate-pulse" : ""}`}
                  key={index}
                  style={{ height }}
                />
              );
            })}
          </div>
          <p className="absolute right-7 top-[19px] w-[88px] text-right text-sm font-medium leading-[22px] text-[#506058]">{formatClock(seconds)}</p>
        </div>

        <div className="mt-6 flex min-h-[146px] flex-col gap-2.5 rounded-[20px] bg-white px-5 pb-[22px] pt-[18px]">
          <p className="inline-flex h-[34px] w-[144px] items-center rounded-[17px] pl-3 text-lg font-medium text-[#25324a]">{copy.tag}</p>
          {phase === "preview" ? (
            <textarea
              className="min-h-[60px] w-full resize-none bg-transparent text-xl font-bold leading-[30px] text-[#13221b] outline-none"
              onChange={(event) => setPreviewText(event.target.value)}
              value={previewText}
            />
          ) : (
            <p className="text-xl font-bold leading-[30px] text-[#13221b]">{copy.body}</p>
          )}
          <p className="text-lg font-normal text-[#506058]">{copy.hint}</p>
        </div>

        <div className="mt-8 flex flex-wrap gap-4">
          {phase === "listening" ? (
            <>
              <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={() => void startListening()} type="button">
                <img alt="" aria-hidden="true" height={20} src="/safety/icon-voice-refresh.svg" width={20} />
                重說一次
              </button>
              <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium tracking-[0.1px] text-white" onClick={() => void finishAndTranscribe()} type="button">
                送出問題
                <img alt="" aria-hidden="true" height={20} src="/safety/icon-arrow-right.svg" width={20} />
              </button>
            </>
          ) : null}
          {phase === "processing" ? (
            <>
              <button className="inline-flex h-12 w-[150px] items-center justify-center rounded-2xl border border-solid border-[#d63a37] bg-white text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={cancelProcessing} type="button">
                取消
              </button>
              <button className="inline-flex h-12 w-[180px] items-center justify-center rounded-2xl bg-[#d63a37] text-[15px] font-medium tracking-[0.1px] text-white" disabled type="button">
                處理中…
              </button>
            </>
          ) : null}
          {phase === "preview" ? (
            <>
              <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={() => void startListening()} type="button">
                <img alt="" aria-hidden="true" height={20} src="/safety/icon-voice-refresh.svg" width={20} />
                重說一次
              </button>
              <button className="inline-flex h-12 w-[180px] items-center justify-center rounded-2xl bg-[#d63a37] text-[15px] font-medium tracking-[0.1px] text-white disabled:bg-[#d7ddd9]" disabled={!previewText.trim()} onClick={() => onConfirm(previewText.trim())} type="button">
                確認並送出
              </button>
            </>
          ) : null}
          {phase === "error" ? (
            <>
              <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={() => void startListening()} type="button">
                <img alt="" aria-hidden="true" height={20} src="/safety/icon-voice-refresh.svg" width={20} />
                再試一次
              </button>
              <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium tracking-[0.1px] text-white" onClick={onUseText} type="button">
                改用文字
                <img alt="" aria-hidden="true" height={20} src="/safety/icon-arrow-right.svg" width={20} />
              </button>
            </>
          ) : null}
        </div>
        <p className="mt-4 text-xs font-medium leading-[19px] text-[#177049]">{copy.footer}</p>
      </div>
    </section>
  );
}

function formatClock(total: number) {
  const safe = Math.max(0, total);
  const minutes = String(Math.floor(safe / 60)).padStart(2, "0");
  const seconds = String(safe % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function copyFor(phase: VoicePhase, text: string) {
  if (phase === "processing") {
    return {
      title: "正在轉成文字…",
      subtitle: "我正在整理你的語音，這一步還沒有送出。",
      tag: "AI 正在想",
      body: "AI 正在整理答案…",
      hint: "等一下就好，答案快好了。",
      footer: "語音只用來完成本次轉錄，完成後依設定刪除",
    };
  }
  if (phase === "preview") {
    return {
      title: "請確認我聽得對不對",
      subtitle: "送出前可以修改文字，原始語音不會直接傳給 AI。",
      tag: "我正在聽",
      body: text,
      hint: "還沒有送出，你可以再說一次或修改。",
      footer: "確認文字後，才會檢查看看有沒有個人資料或不適合分享的內容",
    };
  }
  if (phase === "error") {
    return {
      title: "我沒有聽清楚",
      subtitle: "周圍可能太吵，或語音太短。可以再試一次，也能改用文字。",
      tag: "我正在聽",
      body: "未取得可辨識的文字",
      hint: "沒有任何內容送出。",
      footer: "錄音已停止，未保存這次語音",
    };
  }
  return {
    title: "正在聆聽…",
    subtitle: "說完後，我會先把你的話變成文字，再請你確認。",
    tag: "我正在聽",
    body: text || "說出來就好",
    hint: "還沒有送出，你可以再說一次或修改。",
    footer: "送出前會先檢查個人資料與不適合內容",
  };
}

function haloFor(phase: VoicePhase) {
  if (phase === "processing") {
    return { halo: "/safety/voice-mic-halo.svg", haloWidth: 160, haloHeight: 160, icon: "/safety/illustration-system-spark.svg" };
  }
  if (phase === "preview") {
    return { halo: "/safety/voice-mic-halo-success.svg", haloWidth: 95, haloHeight: 95, icon: "/safety/illustration-system-success.svg" };
  }
  if (phase === "error") {
    return { halo: "/safety/voice-mic-halo.svg", haloWidth: 160, haloHeight: 160, icon: "/safety/illustration-safety-warning-triangle.svg" };
  }
  return { halo: "/safety/voice-mic-halo.svg", haloWidth: 160, haloHeight: 160, icon: "/safety/illustration-system-microphone.svg" };
}
