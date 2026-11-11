"use client";

import { useCallback, useState } from "react";

import { WatchVoiceCall, type WatchBadgeTone } from "@/components/watch-voice-call";
import { useWatchLiveCall } from "@/hooks/use-watch-live-call";

type WatchStepId =
  | "ready"
  | "dialing"
  | "connecting"
  | "connected"
  | "question"
  | "processing"
  | "speaking"
  | "followup"
  | "ended"
  | "pii"
  | "critical"
  | "unreachable"
  | "dropped"
  | "unavailable";

type WatchAction = {
  label: string;
  tone: "primary" | "secondary";
  next: WatchStepId | { note: string };
};

type WatchStep = {
  title: string;
  scenario: string;
  badge: string;
  tone: WatchBadgeTone;
  headline: string;
  waveform: "live" | "idle";
  micOpen: boolean;
  status: readonly [string, string];
  showEnd: boolean;
  actions: WatchAction[];
};

const steps: Record<WatchStepId, WatchStep> = {
  ready: {
    title: "撥打遠傳智靈",
    scenario: "展示入口｜使用既有手錶通話能力。服務名稱為示意，不代表短碼已啟用。",
    badge: "服務已啟用",
    tone: "mint",
    headline: "準備撥號",
    waveform: "idle",
    micOpen: false,
    status: ["服務：開啟　通話：未連線", "麥克風：關閉"],
    showEnd: false,
    actions: [
      { label: "撥打示意", tone: "primary", next: "dialing" },
      { label: "個資保護情境", tone: "secondary", next: "pii" },
      { label: "重大安全情境", tone: "secondary", next: "critical" },
      { label: "異常情境", tone: "secondary", next: "unreachable" },
    ],
  },
  dialing: {
    title: "撥號中",
    scenario: "裝置原生操作概念；等待連線。",
    badge: "正在撥號",
    tone: "sky",
    headline: "撥號中…",
    waveform: "live",
    micOpen: false,
    status: ["服務：開啟　通話：撥號中", "麥克風：關閉"],
    showEnd: false,
    actions: [
      { label: "模擬接通", tone: "primary", next: "connecting" },
      { label: "模擬無法接通", tone: "secondary", next: "unreachable" },
      { label: "返回入口", tone: "secondary", next: "ready" },
    ],
  },
  connecting: {
    title: "正在連線",
    scenario: "通話接通前的等待狀態。",
    badge: "正在連線",
    tone: "sky",
    headline: "連線中…",
    waveform: "live",
    micOpen: false,
    status: ["服務：開啟　通話：連線中", "麥克風：關閉"],
    showEnd: false,
    actions: [
      { label: "已接通", tone: "primary", next: "connected" },
      { label: "模擬無法接通", tone: "secondary", next: "unreachable" },
    ],
  },
  connected: {
    title: "已接通",
    scenario: "語音引導：嗨！我是智靈，你今天想知道什麼呢？",
    badge: "正在聆聽",
    tone: "mint",
    headline: "00:00",
    waveform: "live",
    micOpen: true,
    status: ["服務：開啟　通話：已連線", "麥克風：開啟"],
    showEnd: true,
    actions: [
      { label: "孩子開始提問", tone: "primary", next: "question" },
      { label: "模擬通話中斷", tone: "secondary", next: "dropped" },
      { label: "結束通話", tone: "secondary", next: "ended" },
    ],
  },
  question: {
    title: "孩子說話中",
    scenario: "孩子：恐龍為什麼會滅絕？此為語音狀態示意，非真實 STT。",
    badge: "正在聆聽",
    tone: "mint",
    headline: "00:15",
    waveform: "live",
    micOpen: true,
    status: ["服務：開啟　通話：已連線", "麥克風：開啟"],
    showEnd: true,
    actions: [
      { label: "模擬處理", tone: "primary", next: "processing" },
      { label: "結束通話", tone: "secondary", next: "ended" },
    ],
  },
  processing: {
    title: "AI 處理中",
    scenario: "PII 與安全分類後產生適齡回答；後端流程見工程區。",
    badge: "正在安全處理",
    tone: "mint",
    headline: "00:20",
    waveform: "live",
    micOpen: false,
    status: ["服務：開啟　通話：已連線", "麥克風：暫停收音"],
    showEnd: true,
    actions: [
      { label: "模擬語音回答", tone: "primary", next: "speaking" },
      { label: "AI 暫時無法回應", tone: "secondary", next: "unavailable" },
      { label: "結束通話", tone: "secondary", next: "ended" },
    ],
  },
  speaking: {
    title: "AI 回答中",
    scenario:
      "AI：科學家認為，一顆很大的小行星撞上地球，可能是恐龍滅絕的原因之一。撞擊後灰塵遮住陽光，植物變少，許多動物也慢慢找不到食物。",
    badge: "AI 正在回答",
    tone: "sky",
    headline: "00:25",
    waveform: "live",
    micOpen: false,
    status: ["服務：開啟　通話：已連線", "麥克風：暫停收音"],
    showEnd: true,
    actions: [
      { label: "孩子繼續提問", tone: "primary", next: "followup" },
      { label: "結束通話", tone: "secondary", next: "ended" },
    ],
  },
  followup: {
    title: "孩子繼續提問",
    scenario: "孩子：那隕石有多大？第 2 輪提問；語音狀態為 Demo Simulation。",
    badge: "可以繼續提問",
    tone: "mint",
    headline: "01:00",
    waveform: "live",
    micOpen: true,
    status: ["服務：開啟　通話：已連線", "麥克風：開啟"],
    showEnd: true,
    actions: [
      { label: "模擬處理第 2 題", tone: "primary", next: "processing" },
      { label: "結束通話", tone: "secondary", next: "ended" },
    ],
  },
  ended: {
    title: "通話結束",
    scenario: "示範通話 05:42｜自然探索。系統建立 Session Record 並同步家長端。",
    badge: "通話已結束",
    tone: "mint",
    headline: "05:42",
    waveform: "idle",
    micOpen: false,
    status: ["服務：開啟　通話：已結束", "麥克風：關閉"],
    showEnd: false,
    actions: [
      {
        label: "Demo Simulation — 家長紀錄",
        tone: "primary",
        next: { note: "已模擬同步到家長端的手錶語音紀錄。" },
      },
      { label: "返回入口", tone: "secondary", next: "ready" },
      {
        label: "紀錄尚未產生",
        tone: "primary",
        next: {
          note: "模擬同步中的空狀態。通話資料尚未顯示。請稍後再查看；若持續無法載入，請重新整理。",
        },
      },
    ],
  },
  pii: {
    title: "個資自動保護",
    scenario:
      "Demo Session ID：PII-002　孩子：我住在［地址已隱藏］……附近公園有什麼昆蟲？系統遮蔽後繼續回答，無需家長審核。",
    badge: "正在安全處理",
    tone: "mint",
    headline: "02:32",
    waveform: "live",
    micOpen: false,
    status: ["服務：開啟　通話：已連線", "麥克風：暫停收音"],
    showEnd: true,
    actions: [
      {
        label: "模擬同步已保護紀錄",
        tone: "primary",
        next: { note: "已模擬同步已保護紀錄。系統遮蔽後繼續回答，無需家長審核。" },
      },
      { label: "返回入口", tone: "secondary", next: "ready" },
    ],
  },
  critical: {
    title: "需要關注的語音情境",
    scenario:
      "Demo Session ID：CRITICAL-003　AI 以支持性語音陪伴，鼓勵孩子尋找可信任的大人。偵測與通知僅為情境模擬。",
    badge: "正在安全處理",
    tone: "mint",
    headline: "02:32",
    waveform: "live",
    micOpen: false,
    status: ["服務：開啟　通話：已連線", "麥克風：暫停收音"],
    showEnd: true,
    actions: [
      {
        label: "模擬家長安全通知",
        tone: "primary",
        next: { note: "已模擬家長安全通知。偵測與通知僅為情境模擬。" },
      },
      { label: "返回入口", tone: "secondary", next: "ready" },
    ],
  },
  unreachable: {
    title: "無法接通",
    scenario: "通話未建立；可重試或返回手錶入口。",
    badge: "連線失敗",
    tone: "coral",
    headline: "請重試",
    waveform: "idle",
    micOpen: false,
    status: ["服務：開啟　通話：未連線", "麥克風：關閉"],
    showEnd: false,
    actions: [
      { label: "重新撥打", tone: "primary", next: "dialing" },
      { label: "返回入口", tone: "secondary", next: "ready" },
    ],
  },
  dropped: {
    title: "通話中斷",
    scenario: "通話已中斷；AI 不再持續回答。",
    badge: "通話中斷",
    tone: "coral",
    headline: "請重試",
    waveform: "idle",
    micOpen: false,
    status: ["服務：開啟　通話：已中斷", "麥克風：關閉"],
    showEnd: false,
    actions: [
      { label: "重新撥打", tone: "primary", next: "dialing" },
      { label: "返回入口", tone: "secondary", next: "ready" },
    ],
  },
  unavailable: {
    title: "AI 暫時無法回應",
    scenario: "請稍後再試，或先結束通話。",
    badge: "暫無回應",
    tone: "coral",
    headline: "請重試",
    waveform: "idle",
    micOpen: false,
    status: ["服務：開啟　通話：已連線", "請重試或結束"],
    showEnd: false,
    actions: [
      { label: "再試一次", tone: "primary", next: "processing" },
      { label: "結束通話", tone: "secondary", next: "ended" },
    ],
  },
};

export function WatchVoiceFlow() {
  const [stepId, setStepId] = useState<WatchStepId>("ready");
  const [endedClock, setEndedClock] = useState<string | null>(null);
  const hangup = useCallback((destination: "ready" | "ended", clock: string) => {
    setEndedClock(destination === "ended" ? clock : null);
    setStepId(destination);
  }, []);
  const live = useWatchLiveCall(hangup);
  const step = steps[stepId];
  const screen = live.view;

  const canCall = !screen || screen.retryOnPress;

  const title = screen?.title ?? step.title;
  const scenario = screen?.scenario ?? step.scenario;

  return (
    <div className="grid min-h-dvh place-items-center bg-[#f7f8fc] px-4 py-6">
      <div className="flex w-[min(430px,calc(100vw-2rem))] flex-col items-center gap-3">
        <div className="max-h-28 w-full overflow-y-auto text-center">
          <p className="text-sm leading-5 font-bold text-[#333852]">{title}</p>
          <p className="mt-1 text-xs leading-5 text-[#506058]">{scenario}</p>
        </div>
        <div className="w-[min(430px,calc(100vw-2rem),calc((100dvh-9rem)*430/592))]">
          <WatchVoiceCall
            badge={screen?.badge ?? step.badge}
            headline={screen?.headline ?? (stepId === "ended" && endedClock ? endedClock : step.headline)}
            levels={screen?.levels}
            micOpen={screen?.micOpen ?? step.micOpen}
            onActivate={canCall ? live.start : undefined}
            onEnd={live.end}
            showEnd={screen?.showEnd ?? false}
            status={screen?.status ?? step.status}
            tone={screen?.tone ?? step.tone}
            waveform={screen?.waveform ?? step.waveform}
          />
        </div>
      </div>
    </div>
  );
}
