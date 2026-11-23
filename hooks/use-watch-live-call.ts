"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { WatchBadgeTone } from "@/components/watch-voice-call";
import { speakTextAsync, stopSpeaking } from "@/lib/speak-text";
import { transcribeVoice } from "@/lib/voice-transcribe";
import { buildWatchConversation, submitWatchConversation, type WatchTurnRecord } from "@/lib/voice-records";
import { WATCH_WAVE_BARS, openWatchMic } from "@/lib/watch-mic";
import { useConversationStore } from "@/store/conversation-store";

// Child-facing wording for each stage of the call. Keep lines short: the watch screen is small.
const GREETING = "嗨！我是 AI 心守護，你今天想知道什麼呢？";
const DIALING_HINT = "正在打給 AI 心守護…";
const CONNECTING_HINT = "快接通了，請等一下";
const LISTEN_HINT = "請說話，說完停一下就好";
const NOT_HEARD_HINT = "我沒有聽清楚，可以再說一次";
const PROCESSING_HINT = "我先檢查一下這句話，再來回答你";
const NO_MIC_HINT = "沒有取得麥克風，請允許使用麥克風後再試一次";
const UNAVAILABLE_HINT = "請再試一次，或先結束通話";
const SILENCE_MS = 2400;
const MIN_SPEECH_MS = 450;
const MAX_SPEECH_MS = 18000;

type LivePhase = "dialing" | "connecting" | "listening" | "processing" | "speaking" | "unavailable" | "unreachable";
type SpeakKind = "greeting" | "answer" | "guard";
type ModelTurn = { role: "user" | "assistant"; content: string };

export type WatchLiveView = {
  title: string;
  scenario: string;
  badge: string;
  tone: WatchBadgeTone;
  headline: string;
  waveform: "live" | "idle" | "levels";
  levels: number[] | null;
  micOpen: boolean;
  status: readonly [string, string];
  showEnd: boolean;
  retryOnPress: boolean;
};

type Hangup = (destination: "ready" | "ended", clock: string) => void;

export function useWatchLiveCall(onHangup: Hangup) {
  const [phase, setPhase] = useState<LivePhase | null>(null);
  const [levels, setLevels] = useState<number[] | null>(null);
  const [clock, setClock] = useState("00:00");
  const [scenario, setScenario] = useState("");
  const [line, setLine] = useState("");
  const [kind, setKind] = useState<SpeakKind>("greeting");
  const [heard, setHeard] = useState(false);
  const [listenNonce, setListenNonce] = useState(0);
  const onHangupRef = useRef(onHangup);
  const generationRef = useRef(0);
  const startedAtRef = useRef(0);
  const historyRef = useRef<ModelTurn[]>([]);
  const sessionRef = useRef("");
  const micRef = useRef<Awaited<ReturnType<typeof openWatchMic>> | null>(null);
  const blobRef = useRef<Blob | null>(null);
  const lineRef = useRef("");
  const recordsRef = useRef<WatchTurnRecord[]>([]);
  const { importConversations } = useConversationStore();
  const importRef = useRef(importConversations);

  useEffect(() => {
    onHangupRef.current = onHangup;
    importRef.current = importConversations;
  }, [onHangup, importConversations]);

  // Keeps the masked record of this call. The server decides whether it is stored on the server
  // (sqlite) or stays in this browser; if the server cannot take it, it stays here too.
  // It only reads refs, so it is stable and safe to call from the unmount cleanup.
  const saveRecord = useCallback(() => {
    const turns = recordsRef.current;
    recordsRef.current = [];
    const conversation = buildWatchConversation({
      sessionId: sessionRef.current,
      startedAt: startedAtRef.current || Date.now(),
      endedAt: Date.now(),
      turns,
    });
    if (!conversation) {
      return;
    }
    void submitWatchConversation(conversation).then((result) => {
      if (result !== "sqlite") {
        importRef.current([conversation]);
      }
    });
  }, []);

  useEffect(() => {
    lineRef.current = line;
  }, [line]);

  useEffect(() => {
    return () => {
      generationRef.current += 1;
      stopSpeaking();
      micRef.current?.close();
      // Leaving the page mid-call must not lose what was already said.
      saveRecord();
    };
  }, [saveRecord]);

  useEffect(() => {
    if (!phase || phase === "dialing" || phase === "connecting" || phase === "unreachable") {
      return;
    }
    if (!startedAtRef.current) {
      startedAtRef.current = Date.now();
    }
    const tick = () => setClock(formatClock(Date.now() - startedAtRef.current));
    tick();
    const timer = window.setInterval(tick, 250);
    return () => window.clearInterval(timer);
  }, [phase]);

  useEffect(() => {
    if (phase !== "dialing") {
      return;
    }
    const generation = generationRef.current;
    const timer = window.setTimeout(() => {
      if (generation === generationRef.current) {
        setPhase("connecting");
      }
    }, 800);
    return () => window.clearTimeout(timer);
  }, [phase]);

  useEffect(() => {
    if (phase !== "connecting") {
      return;
    }
    const generation = generationRef.current;
    const timer = window.setTimeout(() => {
      if (generation !== generationRef.current) {
        return;
      }
      startedAtRef.current = Date.now();
      setKind("greeting");
      setLine(GREETING);
      setScenario(GREETING);
      setPhase("speaking");
    }, 700);
    return () => window.clearTimeout(timer);
  }, [phase]);

  useEffect(() => {
    if (phase !== "speaking" || !line) {
      return;
    }
    const generation = generationRef.current;
    const energyRef = { current: 0 };
    let frame = 0;
    let raf = 0;
    let cancelled = false;
    const paint = () => {
      frame += 1;
      // Some voices never fire onstart/onboundary, so the reported energy stays 0 and the bars
      // would sit flat while the audio plays. While the browser still says it is speaking, fall
      // back to a gentle pulse; real events (energyRef > 0) take over as soon as they arrive.
      const reported = energyRef.current;
      const speaking = typeof window !== "undefined" && Boolean(window.speechSynthesis?.speaking);
      const energy = reported > 0 ? reported : speaking ? 0.32 + 0.68 * Math.abs(Math.sin(performance.now() / 150)) : 0;
      setLevels(barsFromSpeech(energy, frame));
      raf = window.requestAnimationFrame(paint);
    };
    raf = window.requestAnimationFrame(paint);
    void speakTextAsync(line, (energy) => {
      energyRef.current = energy;
    }).finally(() => {
      window.cancelAnimationFrame(raf);
      if (cancelled || generation !== generationRef.current) {
        return;
      }
      setLevels(null);
      setHeard(false);
      setScenario(LISTEN_HINT);
      setPhase("listening");
    });
    return () => {
      cancelled = true;
      window.cancelAnimationFrame(raf);
      stopSpeaking();
    };
  }, [phase, line]);

  useEffect(() => {
    if (phase !== "listening") {
      return;
    }
    const generation = generationRef.current;
    let mic: Awaited<ReturnType<typeof openWatchMic>> | null = null;
    let raf = 0;
    let stopped = false;
    let noise = 0.01;
    let speechAt = 0;
    let quietAt = 0;
    let voiced = false;
    const hearAfter = Date.now() + 900;

    const finish = () => {
      if (stopped || !mic) {
        return;
      }
      stopped = true;
      window.cancelAnimationFrame(raf);
      const blob = mic.capture();
      mic.close();
      if (micRef.current === mic) {
        micRef.current = null;
      }
      if (generation !== generationRef.current) {
        return;
      }
      if (blob.size < 1000) {
        setScenario(NOT_HEARD_HINT);
        setHeard(false);
        setListenNonce((value) => value + 1);
        return;
      }
      blobRef.current = blob;
      setScenario(PROCESSING_HINT);
      setLevels(null);
      setPhase("processing");
    };

    void openWatchMic()
      .then((opened) => {
        if (generation !== generationRef.current) {
          opened.close();
          return;
        }
        mic = opened;
        micRef.current = opened;
        const watch = () => {
          if (stopped || generation !== generationRef.current) {
            return;
          }
          const rms = opened.rms();
          setLevels(opened.readLevels());
          const now = Date.now();
          if (now < hearAfter) {
            if (rms < 0.03) {
              noise = noise * 0.9 + rms * 0.1;
            }
            raf = window.requestAnimationFrame(watch);
            return;
          }
          if (rms < 0.03) {
            noise = noise * 0.92 + rms * 0.08;
          }
          const threshold = Math.min(0.08, Math.max(0.016, noise * 3.2));
          if (rms > threshold) {
            if (!voiced) {
              speechAt = now;
              setHeard(true);
            }
            voiced = true;
            quietAt = 0;
          } else if (voiced) {
            quietAt = quietAt || now;
            if (now - quietAt > SILENCE_MS && now - speechAt > MIN_SPEECH_MS) {
              finish();
              return;
            }
          }
          if (voiced && now - speechAt > MAX_SPEECH_MS) {
            finish();
            return;
          }
          raf = window.requestAnimationFrame(watch);
        };
        raf = window.requestAnimationFrame(watch);
      })
      .catch(() => {
        if (generation === generationRef.current) {
          setPhase("unreachable");
        }
      });

    return () => {
      stopped = true;
      window.cancelAnimationFrame(raf);
      mic?.close();
      if (micRef.current === mic) {
        micRef.current = null;
      }
    };
  }, [phase, listenNonce]);

  useEffect(() => {
    if (phase !== "processing") {
      return;
    }
    const generation = generationRef.current;
    const blob = blobRef.current;
    blobRef.current = null;
    if (!blob) {
      return;
    }
    const controller = new AbortController();

    void (async () => {
      try {
        const text = await transcribeVoice(blob, controller.signal);
        if (generation !== generationRef.current) {
          return;
        }
        if (!text || looksLikeEcho(text, lineRef.current)) {
          setScenario(text ? LISTEN_HINT : NOT_HEARD_HINT);
          setHeard(false);
          setPhase("listening");
          return;
        }
        const response = await fetch("/api/watch/turn", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sessionId: sessionRef.current,
            text,
            history: historyRef.current,
          }),
          signal: controller.signal,
        });
        const payload = (await response.json()) as {
          speak?: string;
          blocked?: boolean;
          protected?: boolean;
          remember?: { user?: string; assistant?: string } | null;
          record?: { user?: string; safeUser?: string; assistant?: string; status?: string };
          error?: string;
        };
        if (generation !== generationRef.current) {
          return;
        }
        if (!response.ok || !payload.speak) {
          setPhase("unavailable");
          return;
        }
        const record = payload.record;
        if (record?.assistant && (record.status === "safe" || record.status === "protected" || record.status === "critical")) {
          recordsRef.current.push({
            user: record.user ?? "",
            safeUser: record.safeUser ?? "",
            assistant: record.assistant,
            status: record.status,
            at: Date.now(),
          });
        }
        const remember = payload.remember;
        if (remember?.user && remember.assistant) {
          const userTurn: ModelTurn = { role: "user", content: remember.user };
          const assistantTurn: ModelTurn = { role: "assistant", content: remember.assistant };
          historyRef.current = [...historyRef.current, userTurn, assistantTurn].slice(-8);
        }
        setKind(payload.blocked ? "guard" : "answer");
        setLine(payload.speak);
        // The masked-data notice gets its own line; only `payload.speak` is read aloud.
        setScenario(payload.protected && !payload.blocked ? `個資已先保護\n${payload.speak}` : payload.speak);
        setPhase("speaking");
      } catch (error) {
        if (controller.signal.aborted || generation !== generationRef.current) {
          return;
        }
        console.error(error);
        setPhase("unavailable");
      }
    })();

    return () => controller.abort();
  }, [phase]);

  function hangup(destination: "ready" | "ended") {
    generationRef.current += 1;
    stopSpeaking();
    micRef.current?.close();
    micRef.current = null;
    const clockValue = startedAtRef.current ? formatClock(Date.now() - startedAtRef.current) : "00:00";
    saveRecord();
    startedAtRef.current = 0;
    historyRef.current = [];
    setPhase(null);
    setLevels(null);
    setHeard(false);
    onHangupRef.current(destination, clockValue);
  }

  function start() {
    generationRef.current += 1;
    stopSpeaking();
    micRef.current?.close();
    micRef.current = null;
    historyRef.current = [];
    recordsRef.current = [];
    sessionRef.current = crypto.randomUUID();
    startedAtRef.current = 0;
    setClock("00:00");
    setLine("");
    setKind("greeting");
    setHeard(false);
    setScenario(DIALING_HINT);
    setLevels(null);
    setPhase("dialing");
  }

  const view: WatchLiveView | null = phase
    ? {
        title: titleFor(phase, kind, heard),
        scenario: scenarioFor(phase, scenario),
        badge: badgeFor(phase, kind).label,
        tone: badgeFor(phase, kind).tone,
        headline: phase === "dialing" ? "撥號中…" : phase === "connecting" ? "連線中…" : phase === "unavailable" || phase === "unreachable" ? "請重試" : clock,
        waveform: phase === "listening" || phase === "speaking" ? "levels" : phase === "unavailable" || phase === "unreachable" ? "idle" : "live",
        levels: phase === "listening" || phase === "speaking" ? levels : null,
        micOpen: phase === "listening",
        status: statusFor(phase),
        showEnd: phase === "dialing" || phase === "connecting" || phase === "listening" || phase === "processing" || phase === "speaking",
        retryOnPress: phase === "unreachable" || phase === "unavailable",
      }
    : null;

  return { active: phase !== null, view, start, end: () => hangup("ended") };
}

function titleFor(phase: LivePhase, kind: SpeakKind, heard: boolean) {
  if (phase === "dialing") return "撥號中";
  if (phase === "connecting") return "正在連線";
  if (phase === "listening") return heard ? "我在聽你說" : "已接通，請說話";
  if (phase === "processing") return "正在想答案";
  if (phase === "speaking") return kind === "guard" ? "我們先聊別的" : "AI 回答中";
  if (phase === "unreachable") return "無法接通";
  return "我暫時答不出來";
}

function scenarioFor(phase: LivePhase, scenario: string) {
  if (phase === "dialing") return DIALING_HINT;
  if (phase === "connecting") return CONNECTING_HINT;
  if (phase === "listening") return scenario || LISTEN_HINT;
  if (phase === "processing") return PROCESSING_HINT;
  if (phase === "unreachable") return NO_MIC_HINT;
  if (phase === "unavailable") return UNAVAILABLE_HINT;
  return scenario;
}

function badgeFor(phase: LivePhase, kind: SpeakKind): { label: string; tone: WatchBadgeTone } {
  if (phase === "dialing") return { label: "正在撥號", tone: "sky" };
  if (phase === "connecting") return { label: "正在連線", tone: "sky" };
  if (phase === "listening") return { label: "正在聆聽", tone: "mint" };
  if (phase === "processing" || (phase === "speaking" && kind === "guard")) return { label: "正在安全處理", tone: "mint" };
  if (phase === "speaking") return { label: "AI 正在回答", tone: "sky" };
  if (phase === "unreachable") return { label: "連線失敗", tone: "coral" };
  return { label: "暫無回應", tone: "coral" };
}

function statusFor(phase: LivePhase): readonly [string, string] {
  if (phase === "dialing") return ["服務：開啟　通話：撥號中", "麥克風：關閉"];
  if (phase === "connecting") return ["服務：開啟　通話：連線中", "麥克風：關閉"];
  if (phase === "unreachable") return ["服務：開啟　通話：未連線", "麥克風：關閉"];
  if (phase === "listening") return ["服務：開啟　通話：已連線", "麥克風：開啟"];
  if (phase === "unavailable") return ["服務：開啟　通話：已連線", "請重試或結束"];
  return ["服務：開啟　通話：已連線", "麥克風：暫停收音"];
}

function looksLikeEcho(heard: string, spoken: string) {
  const said = heard.replace(/\s/g, "");
  const played = spoken.replace(/\s/g, "");
  if (said.length < 4 || played.length < 4) {
    return false;
  }
  return played.includes(said) || said.includes(played.slice(0, Math.min(played.length, 12)));
}

function barsFromSpeech(energy: number, frame: number) {
  return Array.from({ length: WATCH_WAVE_BARS }, (_, index) => {
    const shape = 0.4 + 0.6 * Math.abs(Math.sin(frame * 0.37 + index * 0.62));
    return Math.max(0, Math.min(1, energy * shape));
  });
}

function formatClock(elapsed: number) {
  const total = Math.max(0, Math.floor(elapsed / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}
