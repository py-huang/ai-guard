"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft } from "lucide-react";

import { useConversationStore } from "@/store/conversation-store";
import type { SafetyEvent, SafetyEventStatus } from "@/types/conversation";

type Item = SafetyEvent & { conversationId: string };
type EventKind = SafetyEvent["type"];
type ReviewDecision = "approved" | "revision" | "declined";

const reviewResults: Record<ReviewDecision, {
  header: string;
  subtitle: string;
  title: string;
  badge: string;
  description: string;
  background: string;
  badgeStyle: string;
  artwork: string;
}> = {
  approved: {
    header: "審核已完成", subtitle: "本次審核已完成", title: "已同意安全版本", badge: "已同意安全版本",
    description: "孩子可以使用不含個資的問題繼續提問。", background: "bg-[#ecf9f3]",
    badgeStyle: "bg-[#ddf5ea] text-[#177049]", artwork: "/mobile/review-result-approved.svg",
  },
  revision: {
    header: "已請孩子修改", subtitle: "等待修改後重新送出", title: "已請孩子修改", badge: "返回待確認",
    description: "孩子會收到修改提示。修改後仍會重新進行安全檢查。", background: "bg-[#ffe7d7]",
    badgeStyle: "bg-[#f4f0ff] text-[#6650a4]", artwork: "/mobile/review-result-revision.svg",
  },
  declined: {
    header: "審核已完成", subtitle: "本次審核已完成", title: "本次提問已停止", badge: "本次提問已停止",
    description: "孩子會收到不送出本次提問的提示，也可以改問其他問題。", background: "bg-[#fff0ee]",
    badgeStyle: "bg-[#fff0ee] text-[#9d1a25]", artwork: "/mobile/review-result-declined.svg",
  },
};

function isReviewDecision(status: SafetyEventStatus | undefined): status is ReviewDecision {
  return status === "approved" || status === "revision" || status === "declined";
}

const styles: Record<EventKind, { label: string; background: string; badge: string; color: string; icon: string; hero: string }> = {
  critical: { label: "高風險", background: "bg-[#fff0ee]", badge: "bg-[#ffe2df]", color: "text-[#c02d32]", icon: "/mobile/notify-icon-critical.svg", hero: "/mobile/notify-critical.svg" },
  pending: { label: "待確認", background: "bg-[#ffe7d7]", badge: "bg-[#fff8d9]", color: "text-[#8a6400]", icon: "/mobile/notify-icon-pending.svg", hero: "/mobile/notify-pending.svg" },
  protected: { label: "已保護", background: "bg-[#ecf9f3]", badge: "bg-[#ddf5ea]", color: "text-[#177049]", icon: "/mobile/notify-icon-protected.svg", hero: "/mobile/notify-protected.svg" },
};

const statusLabels: Record<SafetyEventStatus, string> = {
  pending: "待確認", approved: "已同意", revision: "已退回修改", declined: "已拒絕", cancelled: "已取消", completed: "已處理",
};

function formatTime(timestamp: number) {
  const date = new Date(timestamp);
  const day = date.toDateString() === new Date().toDateString() ? "今天" : `${date.getMonth() + 1}/${date.getDate()}`;
  return `${day} ${date.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false })}`;
}

function sourceLabel(item: Item) {
  return item.category === "image" ? "圖片" : item.category === "voice" ? "語音" : "文字";
}

function Panel({ title, children, tone = "white", icon }: {
  title: string;
  children: React.ReactNode;
  tone?: "white" | "red" | "peach" | "green" | "purple";
  icon: string;
}) {
  const colors = {
    white: "border-[#dde3df] bg-white text-[#506058]",
    red: "border-[#dde3df] bg-[#fff0ee] text-[#c93636]",
    peach: "border-[#ffe7d7] bg-[#ffe7d7] text-[#a35a2d]",
    green: "border-[#ddf5ea] bg-[#ecf9f3] text-[#177049]",
    purple: "border-[#dde3df] bg-[#f3efff] text-[#7055b5]",
  };
  return (
    <section className={`rounded-[16px] border p-4 ${colors[tone]}`}>
      <h3 className="flex items-center gap-2 text-[14px] font-medium leading-5"><span className="relative size-[18px] shrink-0"><img src={icon} alt="" className="absolute left-0 top-0 max-w-none" /></span>{title}</h3>
      <div className="mt-2 text-[14px] leading-[22px] text-[#506058]">{children}</div>
    </section>
  );
}

function SupportGuidance({ onBack }: { onBack: () => void }) {
  return (
    <div className="flex flex-col gap-3 px-4 pb-4 pt-4">
      <img src="/mobile/support-guardian.svg" alt="" className="size-20 shrink-0" />
      <h2 className="text-[22px] font-bold leading-8">你不需要獨自處理</h2>
      <section className="flex flex-col gap-2 rounded-[16px] border border-[#dde3df] bg-[#fff0ee] p-4">
        <h3 className="flex items-center gap-2 text-[14px] font-medium leading-5 text-[#c93636]">
          <span className="relative size-[18px] shrink-0"><img src="/mobile/support-immediate.svg" alt="" className="absolute left-0 top-0 max-w-none" /></span>
          若有立即危險
        </h3>
        <p className="text-[14px] leading-[22px] text-[#506058]">陪在孩子身旁並立即尋求緊急救援。臺灣緊急救護：119。</p>
      </section>
      <section className="flex flex-col gap-2 rounded-[16px] border border-[#ddf5ea] bg-[#ecf9f3] p-4">
        <h3 className="flex items-center gap-2 text-[14px] font-medium leading-5 text-[#177049]">
          <span className="relative size-[18px] shrink-0"><img src="/mobile/support-listen.svg" alt="" className="absolute left-0 top-0 max-w-none" /></span>
          先傾聽、先陪伴
        </h3>
        <p className="text-[14px] leading-[22px] text-[#506058]">可以說：「謝謝你告訴我，我會陪著你。」避免責備或要求孩子立刻振作。</p>
      </section>
      <section className="flex flex-col gap-2 rounded-[16px] border border-[#dde3df] bg-[#f4f0ff] p-4">
        <h3 className="flex items-center gap-2 text-[14px] font-medium leading-5 text-[#6650a4]">
          <span className="relative size-[18px] shrink-0"><img src="/mobile/support-connect.svg" alt="" className="absolute left-0 top-0 max-w-none" /></span>
          一起找可信任的協助
        </h3>
        <p className="text-[14px] leading-[22px] text-[#506058]">聯絡學校輔導老師、心理專業人員或 1925 安心專線。1925 為衛福部 24 小時免付費服務。</p>
      </section>
      <button type="button" className="h-12 w-full rounded-[16px] border border-[#d63a37] bg-[#d63a37] text-[15px] font-medium text-white">尋求協助</button>
      <button type="button" onClick={onBack} className="h-12 w-full rounded-[16px] border border-[#d63a37] bg-white text-[15px] font-medium text-[#c02d32]">返回安全提醒</button>
    </div>
  );
}

export function MobileNotifications({ confirmationsOnly = false }: { confirmationsOnly?: boolean }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { ready, conversations, updateSafetyEvent } = useConversationStore();
  const [notificationSelected, setNotificationSelected] = useState<{ conversationId: string; eventId: string } | null>(null);
  const [outcome, setOutcome] = useState<{ item: Item; decision: ReviewDecision } | null>(null);
  const [showAdvice, setShowAdvice] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const conversationId = searchParams.get("conversation");
  const eventId = searchParams.get("event");
  const selected = confirmationsOnly
    ? conversationId && eventId ? { conversationId, eventId } : null
    : notificationSelected ?? (conversationId && eventId ? { conversationId, eventId } : null);
  const items: Item[] = conversations.flatMap((conversation) =>
    (conversation.safetyEvents ?? []).map((event) => ({ ...event, conversationId: conversation.id })),
  ).filter((event) => confirmationsOnly
    ? event.type === "pending" && event.status === "pending"
    : !((event.type === "critical" || event.type === "protected") && event.acknowledged)
      && !(event.type === "pending" && (isReviewDecision(event.status) || event.status === "completed" || event.status === "cancelled")))
    .sort((a, b) => b.createdAt - a.createdAt);
  const current = selected && conversations.flatMap((conversation) =>
    (conversation.safetyEvents ?? []).map((event) => ({ ...event, conversationId: conversation.id })),
  ).find((item) => item.id === selected.eventId && item.conversationId === selected.conversationId
    && (confirmationsOnly ? item.type === "pending" && item.status === "pending" : item.type !== "pending"));
  const activeOutcome = outcome && selected?.eventId === outcome.item.id && selected.conversationId === outcome.item.conversationId ? outcome : null;

  useEffect(() => {
    if (confirmationsOnly && ready && conversationId && eventId && !current && !activeOutcome) {
      router.replace("/mobile/confirm/");
    }
  }, [confirmationsOnly, ready, conversationId, eventId, current, activeOutcome, router]);

  useEffect(() => {
    if (ready && conversationId && eventId && current && !current.read) {
      updateSafetyEvent(current.conversationId, current.id, { read: true });
    }
  }, [ready, conversationId, eventId, current, updateSafetyEvent]);

  function open(item: Item) {
    setOutcome(null);
    setShowAdvice(false);
    if (!item.read) updateSafetyEvent(item.conversationId, item.id, { read: true });
    if (item.type === "pending") {
      const params = new URLSearchParams({ conversation: item.conversationId, event: item.id });
      router.push(`/mobile/confirm/?${params.toString()}`);
    } else {
      setNotificationSelected({ conversationId: item.conversationId, eventId: item.id });
    }
  }

  function decide(status: ReviewDecision) {
    if (current && current.status === "pending") {
      setOutcome({ item: current, decision: status });
      scrollRef.current?.scrollTo({ top: 0 });
      updateSafetyEvent(current.conversationId, current.id, { status, read: true });
    }
  }

  function returnToList() {
    setOutcome(null);
    setNotificationSelected(null);
    setShowAdvice(false);
    if (confirmationsOnly && selected) router.push("/mobile/confirm/");
    if (!confirmationsOnly && conversationId && eventId) router.replace("/mobile/notify/");
    scrollRef.current?.scrollTo({ top: 0 });
  }

  function returnToCriticalDetail() {
    setShowAdvice(false);
    scrollRef.current?.scrollTo({ top: 0 });
  }

  function acknowledgeNotification() {
    if (current?.type === "critical" || current?.type === "protected") {
      updateSafetyEvent(current.conversationId, current.id, { acknowledged: true });
    }
    returnToList();
  }

  const result = activeOutcome && reviewResults[activeOutcome.decision];
  const config = current ? styles[current.type] : null;
  return (
    <section className="flex h-full flex-col bg-[#fffcf7]">
      <header className="flex h-16 shrink-0 items-center gap-2 bg-white px-4">
        {current || activeOutcome ? (
          <button type="button" onClick={showAdvice ? returnToCriticalDetail : returnToList} aria-label={showAdvice ? "返回安全提醒" : "返回列表"} className="grid size-10 shrink-0 place-items-center text-[#c02d32]">{activeOutcome ? <img src="/mobile/review-result-back.svg" alt="" /> : <ArrowLeft size={20} />}</button>
        ) : (
          <div className="grid size-[38px] shrink-0 place-items-center rounded-[12px] bg-[#d63a37] text-lg font-bold text-white" aria-hidden="true">✦</div>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-[18px] font-bold leading-7">{showAdvice ? "陪孩子一起尋求協助" : result ? result.header : current ? current.type === "critical" ? "重要安全提醒" : current.type === "pending" ? "提問安全確認" : "安全提醒詳情" : confirmationsOnly ? "待確認事項" : "通知"}</h1>
          <p className="truncate text-[12px] font-medium leading-[18px] text-[#506058]">{showAdvice ? "先確認安全，支持可以從現在開始" : activeOutcome && result ? `${sourceLabel(activeOutcome.item)} · ${result.subtitle}` : current ? `${sourceLabel(current)} · ${formatTime(current.createdAt)}` : "小宇 · 安全提醒"}</p>
        </div>
        <Link href="/mobile/notify/" onClick={confirmationsOnly ? undefined : returnToList} aria-label="通知" className="grid size-10 shrink-0 place-items-center"><img src="/mobile/nav-notification-action.svg" width="20" height="20" alt="" /></Link>
      </header>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {showAdvice && current?.type === "critical" ? (
          <SupportGuidance onBack={returnToCriticalDetail} />
        ) : activeOutcome && result ? (
          <div className="flex flex-col gap-4 px-4 py-4">
            <section className={`flex flex-col items-center gap-3 rounded-[20px] border border-[#dde3df] p-4 text-center ${result.background}`}>
              <img src={result.artwork} alt="" width="104" height="104" className="shrink-0" />
              <p className={`rounded-full px-3 py-2 text-xs font-medium leading-[18px] ${result.badgeStyle}`}>{result.badge}</p>
              <h2 className="text-[18px] font-bold leading-7">{result.title}</h2>
              <p className="text-[14px] leading-[22px] text-[#506058]">{activeOutcome.decision === "approved" && activeOutcome.item.category === "image" ? "孩子可以使用安全圖片繼續提問。" : result.description}</p>
            </section>
            <section className={`flex flex-col gap-2 rounded-[20px] p-4 ${activeOutcome.decision === "approved" ? "bg-[#ecf9f3]" : "bg-[#fff8d9]"}`}>
              <h3 className={`flex items-center gap-2 text-[14px] font-medium leading-5 ${activeOutcome.decision === "approved" ? "text-[#177049]" : "text-[#13221b]"}`}>
                <img src={activeOutcome.decision === "approved" ? "/mobile/review-result-safe.svg" : activeOutcome.decision === "revision" ? "/mobile/review-result-revision-info.svg" : "/mobile/review-result-declined-info.svg"} alt="" width="18" height="18" />
                {activeOutcome.decision === "approved" ? activeOutcome.item.category === "image" ? "只會使用安全圖片" : "只會送出這個安全版本" : "資料保護持續生效"}
              </h3>
              <p className="text-[14px] leading-[22px] text-[#506058]">{activeOutcome.decision === "approved" ? activeOutcome.item.safeText || (activeOutcome.item.category === "image" ? "圖片不會儲存在紀錄中；返回對話後可能需要重新上傳並檢查。" : "此紀錄沒有可顯示的安全版本。") : "原始個資未送出 AI，也不會因審核操作而繞過安全檢查。"}</p>
            </section>
            <Link href="/mobile/" className="flex h-12 items-center justify-center rounded-[16px] bg-[#d63a37] text-[15px] font-medium text-white">完成</Link>
            <button type="button" onClick={returnToList} className="flex h-12 items-center justify-center rounded-[16px] border border-[#d63a37] bg-white text-[15px] font-medium text-[#c02d32]">返回待確認</button>
          </div>
        ) : current && config ? (
          <div className="flex flex-col gap-[14px] px-4 py-4">
            <div className={`flex min-h-[126px] items-center justify-between gap-1 rounded-[24px] border border-[#dde3df] p-[18px] ${config.background}`}>
              <div className="min-w-0 flex-1">
                <p className={`text-[11px] font-bold ${config.color}`}>{current.type === "critical" ? "需要你的關注" : current.type === "pending" ? "家長審核" : "一般安全提醒"}</p>
                <h2 className="mt-1 text-[18px] font-bold leading-7">{current.type === "critical" ? "偵測到高風險安全訊息" : current.type === "pending" ? `${sourceLabel(current)}｜${statusLabels[current.status ?? "pending"]}` : "個資已受保護"}</h2>
                {current.type !== "protected" && <p className="mt-1 text-[13px] leading-5 text-[#506058]">{current.type === "critical" ? "已採取安全處理，請先確認孩子安全。" : "個資已自動保護，請確認是否繼續。"}</p>}
              </div>
              <img src={config.hero} width={current.type === "protected" ? 88 : 112} height={current.type === "protected" ? 88 : 112} alt="" className="shrink-0" />
            </div>
            <p className={`w-fit rounded-full px-3 py-2 text-xs font-medium ${config.badge} ${config.color}`}>{current.type === "critical" ? "高風險 · 需要家長關注" : current.type === "protected" ? "已自動保護 · 無需家長審核" : `${statusLabels[current.status ?? "pending"]}${current.status === "pending" ? " · 尚未送出 AI" : ""}`}</p>
            {current.type === "critical" ? (
              <>
                <Panel title="事件類型 · 安全內容攔截" tone="red" icon="/mobile/detail-critical-alert.svg">{formatTime(current.createdAt)} · 系統已攔截這次內容。這是安全提醒，不是診斷。</Panel>
                <Panel title="經處理的事件摘要" icon="/mobile/detail-critical-message.svg">敏感原文不會顯示在通知中。請關心孩子的狀況。</Panel>
                <Panel title="系統已採取的安全措施" tone="green" icon="/mobile/detail-critical-safe.svg">{current.category === "image" ? "已阻擋圖片，並提示孩子換一張圖片。" : "已阻擋內容，並提示孩子尋求可信任的大人協助。"}</Panel>
              </>
            ) : (
              <>
                {current.type === "protected" && <Panel title="事件類型 · 個人資料保護" tone="peach" icon="/mobile/detail-protected-alert.svg">偵測到{current.fields?.length ? [...new Set(current.fields)].join("、") : "需要保護的資料"}，已使用安全版本。</Panel>}
                <Panel title={current.type === "pending" ? "1 · 孩子的問題（已遮蔽）" : "孩子的提問（已遮蔽）"} icon={current.type === "pending" ? "/mobile/detail-pending-original.svg" : "/mobile/detail-protected-message.svg"}>{current.maskedOriginal || (current.category === "image" ? "圖片不會儲存在通知紀錄中。" : "此紀錄沒有保存遮蔽後的原始提問。")}</Panel>
                {current.type === "pending" ? (
                  <>
                    <Panel title="2 · 系統偵測風險" icon="/mobile/detail-pending-alert.svg">請確認是否適合繼續；個人資料不會因家長同意而解除遮蔽。</Panel>
                    <Panel title="3 · 將使用的安全版本" tone="green" icon="/mobile/detail-pending-safe.svg">{current.safeText || "圖片需重新進行安全檢查。"}</Panel>
                  </>
                ) : (
                  <>
                    <Panel title="已使用的安全版本" tone="green" icon="/mobile/detail-protected-safe.svg">{current.safeText || "已使用遮蔽後的圖片。"}</Panel>
                    <Panel title="系統已完成的處理" tone="purple" icon="/mobile/detail-protected-info.svg">已使用安全版本，不需要家長再次審核。</Panel>
                  </>
                )}
              </>
            )}
            {current.type === "pending" && current.status !== "pending" && <Link href={`/chat/${current.conversationId}`} className="rounded-2xl border border-[#d63a37] bg-white px-4 py-3 text-center text-[15px] font-medium text-[#c02d32]">返回孩子的對話</Link>}
            <p className="text-xs leading-5 text-[#506058]">本機示範：通知與審核結果僅儲存在同一瀏覽器，不會跨裝置同步。</p>
          </div>
        ) : confirmationsOnly && ready && items.length === 0 ? (
          <div className="flex flex-col gap-4 px-4 pb-6 pt-4">
            <section className="flex flex-col items-center gap-3 rounded-[20px] border border-[#dde3df] bg-[#ecf9f3] p-4 text-center">
              <img src="/mobile/confirm-empty.svg" width="104" height="104" alt="" className="shrink-0" />
              <p className="rounded-full bg-[#ddf5ea] px-3 py-2 text-xs font-medium leading-[18px] tracking-[0.2px] text-[#177049]">0 件待確認</p>
              <h2 className="text-[18px] font-bold leading-7">目前沒有待確認事項</h2>
              <p className="text-[14px] leading-[22px] text-[#506058]">目前沒有需要家長確認的內容。</p>
            </section>
            <Link href="/mobile/" className="flex h-12 items-center justify-center rounded-[16px] bg-[#d63a37] text-[15px] font-medium text-white">返回總覽</Link>
          </div>
        ) : confirmationsOnly ? (
          <div className="flex flex-col gap-[14px] px-4 pb-6 pt-4">
            <h2 className="text-[18px] font-bold leading-7">{ready ? `${items.length} 件等待確認` : "正在載入待確認事項…"}</h2>
            <p className="text-[14px] leading-[22px] text-[#506058]">先處理下方待確認內容；系統已自動保護的事件不需逐筆核准。</p>
            {items.map((item) => (
              <article key={`${item.conversationId}-${item.id}`} className="flex flex-col gap-3 rounded-[16px] border border-[#dde3df] bg-white p-4">
                <div className="flex items-center gap-2">
                  <img src="/mobile/confirm-item-shield.svg" width="24" height="24" alt="" />
                  <p className="min-w-0 flex-1 text-[14px] font-medium leading-5">小宇 · {sourceLabel(item)}提問</p>
                  <span className="rounded-full bg-[#fff8d9] px-3 py-2 text-xs font-medium leading-[18px] text-[#8a6400]">待確認</span>
                </div>
                <h3 className="break-words text-[18px] font-bold leading-7">{item.maskedOriginal || (item.category === "image" ? "圖片提問" : "此紀錄沒有保存遮蔽後的原始提問。")}</h3>
                <p className="text-xs leading-[18px] text-[#506058]">{formatTime(item.createdAt)} · {item.category === "image" ? "圖片需要家長確認" : "需要家長協助確認"}</p>
                <button type="button" onClick={() => open(item)} className="h-12 w-full rounded-[16px] bg-[#d63a37] text-[15px] font-medium text-white">查看並確認</button>
              </article>
            ))}
            <section className="flex flex-col gap-2 rounded-[20px] bg-[#fff8d9] p-4">
              <h3 className="flex items-center gap-2 text-[14px] font-medium leading-5"><img src="/mobile/confirm-info.svg" width="18" height="18" alt="" />家長可以怎麼協助？</h3>
              <p className="text-[14px] leading-[22px] text-[#506058]">只會使用已移除個資的安全版本。你也可以請孩子修改，或停止這次提問。</p>
            </section>
          </div>
        ) : (
          <div className="flex flex-col gap-[14px] px-4 py-4">
            <div className="flex items-center gap-3"><img src="/mobile/notify-bell.svg" width="32" height="32" alt="" /><div><h2 className="text-base font-bold">重要的時刻，一起守護</h2><p className="mt-0.5 text-[11px] text-[#506058]">安全提醒與待確認事件，清楚分開</p></div></div>
            <p className="text-xs text-[#506058]">本機示範：只顯示此瀏覽器的紀錄。</p>
            {!ready ? <p className="text-sm text-[#506058]">正在載入通知…</p> : items.length === 0 ? <p className="rounded-2xl bg-white p-4 text-sm text-[#506058]">{confirmationsOnly ? "目前沒有待確認事項。" : "目前沒有新通知。"}</p> : items.map((item, index) => {
              const style = styles[item.type];
              const previous = items[index - 1];
              const day = formatTime(item.createdAt).split(" ")[0];
              return (
                <div key={`${item.conversationId}-${item.id}`}>
                  {(!previous || formatTime(previous.createdAt).split(" ")[0] !== day) && <h2 className="mb-[14px] text-lg font-bold">{day}</h2>}
                  <article className={`flex flex-col gap-2 rounded-[16px] border border-[#dde3df] p-4 shadow-[0_8px_12px_rgba(20,33,26,0.08)] ${style.background}`}>
                    <div className="flex items-center gap-2"><span className="relative size-5 shrink-0"><img src={style.icon} alt="" className="absolute left-0 top-0 max-w-none" /></span><span className={`rounded-full px-3 py-2 text-xs font-medium ${style.badge} ${style.color}`}>{style.label}</span><span className="text-[11px] text-[#506058]">{item.type === "critical" ? "高風險安全提醒" : item.type === "pending" ? item.status === "pending" ? "需要家長確認" : "家長確認紀錄" : "一般安全提醒 · 無需審核"}</span></div>
                    <h3 className="text-lg font-bold">{item.type === "critical" ? "請先確認孩子的安全" : item.type === "pending" ? "小宇需要你的確認" : "個資已受保護"}</h3>
                    <p className="text-[13px] leading-[22px] text-[#506058]">{item.type === "critical" ? "系統已攔截內容，請查看提醒與協助建議。" : item.type === "pending" ? item.status === "pending" ? "有一則提問需要家長協助處理。" : "此確認事項已有處理結果。" : "已使用安全版本保護個人資料。"}</p>
                    <p className="text-[11px] text-[#506058]">{sourceLabel(item)} · {formatTime(item.createdAt)}</p>
                    <button type="button" onClick={() => open(item)} className="h-12 w-full rounded-[16px] bg-[#d63a37] text-[15px] font-medium text-white">{item.type === "critical" ? "查看重要安全提醒" : item.type === "pending" ? "查看待確認事項" : "查看安全提醒"}</button>
                    <p className="text-[11px] text-[#506058]">{item.read ? "已讀" : "未讀"} · {item.type === "pending" ? statusLabels[item.status ?? "pending"] : item.type === "critical" ? "需要關注" : "無需審核"}</p>
                  </article>
                </div>
              );
            })}
          </div>
        )}
      </div>
      {!showAdvice && !activeOutcome && (current?.type === "critical" || current?.type === "protected") && <div className="flex shrink-0 flex-col gap-2 bg-white p-4">{current.type === "critical" && <button type="button" onClick={() => { setShowAdvice(true); scrollRef.current?.scrollTo({ top: 0 }); }} className="h-12 rounded-2xl bg-[#d63a37] text-[15px] font-medium text-white">查看協助建議</button>}<button type="button" onClick={acknowledgeNotification} className="h-12 rounded-2xl border border-[#d63a37] text-[15px] font-medium text-[#c02d32]">我已查看</button></div>}
      {!activeOutcome && current?.type === "pending" && current.status === "pending" && <div className="flex shrink-0 flex-col gap-2 border border-[#dde3df] bg-white p-4">{([["approved", "同意並繼續"], ["revision", "退回修改"], ["declined", "拒絕本次內容"]] as const).map(([status, label], index) => <button key={status} type="button" onClick={() => decide(status)} className={`h-12 rounded-2xl text-[15px] font-medium ${index === 0 ? "bg-[#d63a37] text-white" : "border border-[#d63a37] text-[#c02d32]"}`}>{label}</button>)}</div>}
    </section>
  );
}
