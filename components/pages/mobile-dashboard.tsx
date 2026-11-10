"use client";

import Link from "next/link";

import { useConversationStore } from "@/store/conversation-store";
import type { Conversation } from "@/types/conversation";

const topicRows = [
  { label: "自然探索", aliases: ["自然"], icon: "/mobile/topic-nature-usage.svg", color: "#177049" },
  { label: "作業寫作", aliases: ["寫作", "作文", "作業"], icon: "/mobile/topic-writing-usage.svg", color: "#6650a4" },
  { label: "數學", aliases: ["數學"], icon: "/mobile/topic-math.svg", color: "#c93636" },
  { label: "英文", aliases: ["英文", "英語"], icon: "/mobile/topic-english.svg", color: "#4f9cda" },
  { label: "生活問題", aliases: ["生活"], icon: "/mobile/topic-life.svg", color: "#e88b35" },
];

function timeLabel(timestamp: number) {
  return new Date(timestamp).toLocaleTimeString("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function recordIcon(conversation: Conversation) {
  const topic = conversation.topic ?? "";
  return topic.includes("自然") || /恐龍|植物|火山/.test(conversation.title)
    ? "/mobile/topic-nature-record.svg"
    : "/mobile/topic-writing-record.svg";
}

export function MobileDashboard() {
  const { ready, conversations } = useConversationStore();
  const recent = [...conversations].sort((left, right) => right.updatedAt - left.updatedAt).slice(0, 3);
  const topicCount = ready
    ? new Set(conversations.map(({ topic }) => topic?.trim()).filter((topic): topic is string => Boolean(topic))).size
    : 0;

  return (
    <section className="flex h-full flex-col bg-[#fffcf7]">
      <header className="flex h-16 shrink-0 items-center gap-2 bg-white px-4">
        <div className="grid size-[38px] shrink-0 place-items-center rounded-[12px] bg-[#d63a37] text-[18px] font-bold leading-[27px] text-white">✦</div>
        <div className="min-w-0 flex-1 overflow-hidden">
          <h1 className="truncate text-[18px] font-bold leading-7">本週使用總覽</h1>
          <p className="truncate text-[12px] font-medium leading-[18px] tracking-[0.2px] text-[#506058]">小宇 · 10/23–10/29</p>
        </div>
        <Link className="grid size-10 shrink-0 place-items-center rounded-full" href="/mobile/notify/" aria-label="通知">
          <img src="/mobile/nav-notification-action.svg" width="20" height="20" alt="" aria-hidden="true" />
        </Link>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
        <div className="flex flex-col gap-4 px-4 py-4">
          <section className="flex h-[222px] shrink-0 flex-col gap-[14px] overflow-hidden rounded-[24px] border border-[#ddf5ea] bg-[#ecf9f3] p-[18px]" aria-label="安全狀態">
            <div className="flex min-h-0 flex-1 items-center gap-1 overflow-hidden">
              <div className="min-w-0 flex-1 overflow-hidden">
                <p className="text-[11px] font-bold leading-[18px] text-[#177049]">安心守護中</p>
                <h2 className="text-[18px] font-bold leading-7">今天一切正常</h2>
                <p className="text-[13px] leading-5 text-[#506058]">目前沒有需要你處理的安全事件。</p>
              </div>
              <img src="/mobile/guardian-safe.svg" width="112" height="112" alt="安心守護" />
            </div>
            <Link className="flex h-12 shrink-0 items-center justify-center rounded-2xl border border-[#177049] bg-white px-4 text-[15px] font-medium leading-5 tracking-[0.1px] text-[#177049]" href="/mobile/history/">
              查看本週提問
            </Link>
          </section>

          <section className="mx-4 rounded-[20px] border border-[#dde3df] bg-white p-4" aria-label="本週摘要">
            <div className="flex items-center gap-2">
              <Metric icon="/mobile/metric-interactions.svg" value={ready ? conversations.length : 0} label="互動紀錄" />
              <Metric icon="/mobile/metric-topics.svg" value={topicCount} label="使用主題" />
              <Metric icon="/mobile/metric-pending.svg" value={0} label="待確認" accent />
            </div>
          </section>

          <section className="mx-4 rounded-[20px] border border-[#dde3df] bg-white p-4" aria-labelledby="mobile-recent-title">
            <div className="mb-2 flex items-center gap-2">
              <h2 id="mobile-recent-title" className="min-w-0 flex-1 text-[14px] font-medium leading-5 tracking-[0.1px]">最近提問</h2>
              <Link className="flex h-8 w-[86px] shrink-0 items-center justify-center rounded-xl border border-[#dde3df] px-3 text-[14px] font-medium leading-5 tracking-[0.1px] text-[#c02d32]" href="/mobile/history/">查看全部</Link>
            </div>
            {recent.length > 0 ? (
              <ul>
                {recent.map((conversation, index) => (
                  <li className={index ? "border-t border-[#dde3df]" : ""} key={conversation.id}>
                    <Link className="flex min-h-10 items-center gap-2 py-1" href={`/mobile/history/${conversation.id}`}>
                      <img src={recordIcon(conversation)} width="24" height="24" alt="" aria-hidden="true" />
                      <span className="min-w-0 flex-1 overflow-hidden">
                        <span className="block truncate text-[13px] leading-5 tracking-[0.1px]">{conversation.title}</span>
                        <span className="block truncate text-[11px] leading-[18px] tracking-[0.2px] text-[#506058]">{conversation.category === "voice" ? "語音" : conversation.topic?.trim() || "文字"} · {timeLabel(conversation.updatedAt)}</span>
                      </span>
                      <img src="/mobile/chevron-right.svg" width="20" height="20" alt="" aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-3 text-[12px] leading-5 text-[#506058]">{ready ? "還沒有提問紀錄" : "載入提問紀錄中…"}</p>
            )}
          </section>

          <section className="mx-4 flex shrink-0 flex-col gap-[10px] rounded-2xl border border-[#dde3df] bg-white p-4" aria-labelledby="mobile-quota-title">
            <div className="flex items-center gap-2">
              <img src="/mobile/quota-energy.svg" width="24" height="24" alt="" aria-hidden="true" />
              <h2 id="mobile-quota-title" className="min-w-0 flex-1 text-[14px] font-bold leading-[22px]">孩子剩餘 AI 使用額度</h2>
            </div>
            <div className="flex items-baseline gap-1">
              <p className="text-[28px] font-bold leading-9 text-[#6650a4]">28</p>
              <p className="text-[12px] font-medium leading-5 text-[#506058]">/ 100 單位</p>
              <p className="min-w-0 flex-1 text-right text-[12px] leading-5 text-[#506058]">已使用 72</p>
            </div>
            <div className="h-[7px] overflow-hidden rounded-[3px] bg-[#f4f0ff]" role="progressbar" aria-label="AI 額度使用進度" aria-valuemin={0} aria-valuemax={100} aria-valuenow={72}>
              <div className="h-full w-[72%] rounded-[3px] bg-[#6650a4]" />
            </div>
            <p className="text-[11px] leading-[18px] text-[#506058]">每週一重置 · Demo 示意額度</p>
          </section>

          <section className="mx-4 mb-4 rounded-[20px] border border-[#dde3df] bg-white p-4" aria-labelledby="mobile-topic-title">
            <h2 id="mobile-topic-title" className="mb-2 text-[14px] font-medium leading-5 tracking-[0.1px]">主題使用次數</h2>
            <ul className="space-y-1.5">
              {topicRows.map((row) => {
                const count = ready
                  ? conversations.filter((conversation) => row.aliases.some((alias) => conversation.topic?.includes(alias))).length
                  : 0;

                return (
                  <li className="flex min-h-6 items-center gap-2" key={row.label}>
                    <img src={row.icon} width="20" height="20" alt="" aria-hidden="true" />
                    <span className="w-16 shrink-0 text-[12px] leading-[18px] tracking-[0.2px] text-[#506058]">{row.label}</span>
                    <div className="h-[6px] min-w-0 flex-1 overflow-hidden rounded-[3px] bg-[#eef1ef]" role="progressbar" aria-label={`${row.label} 使用次數`} aria-valuemin={0} aria-valuemax={7} aria-valuenow={count}>
                      <div className="h-full rounded-[3px]" style={{ width: `${Math.min(count / 7, 1) * 100}%`, backgroundColor: row.color }} />
                    </div>
                    <span className="w-9 shrink-0 text-right text-[12px] leading-[18px] tracking-[0.2px]">{count} 次</span>
                  </li>
                );
              })}
            </ul>
          </section>
        </div>
      </div>
    </section>
  );
}

function Metric({ icon, value, label, accent = false }: { icon: string; value: number; label: string; accent?: boolean }) {
  const iconSize = icon.includes("pending") ? 20 : 24;

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2">
      <img src={icon} width={iconSize} height={iconSize} alt="" aria-hidden="true" />
      <div className="min-w-0">
        <p className={`text-[24px] font-bold leading-8 tracking-[-0.1px] ${accent ? "text-[#d63a37]" : "text-[#13221b]"}`}>{value}</p>
        <p className="truncate text-[12px] font-medium leading-[18px] tracking-[0.2px] text-[#506058]">{label}</p>
      </div>
    </div>
  );
}