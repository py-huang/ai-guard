"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowLeft, ThumbsUp, X, Zap } from "lucide-react";

import { useConversationStore } from "@/store/conversation-store";
import { useWritingStore } from "@/store/writing-store";
import type { Conversation, ConversationCategory } from "@/types/conversation";

type HistoryFilter = "all" | "text" | "homework" | "voice";
type RecordCategory = Exclude<HistoryFilter, "all">;
type HistoryIcon = {
  src: string;
  size: 20 | 24 | 28;
  shadow?: boolean;
};

type HistoryRecord = {
  id: string;
  title: string;
  updatedAt: number;
  category: RecordCategory;
  metadataCategory: string;
  href: string;
  icon: HistoryIcon;
  status: "待確認" | "處理中" | "已回覆";
  statusTone: "safe" | "pending";
  description?: string;
};

const filters: Array<{ id: HistoryFilter; label: string }> = [
  { id: "all", label: "全部" },
  { id: "text", label: "文字" },
  { id: "homework", label: "作業" },
  { id: "voice", label: "語音" },
];

const historyIcons = {
  protectedImage: { src: "/mobile/history-icon-protected-image.svg", size: 24 },
  pendingImage: { src: "/mobile/history-icon-pending-image.svg", size: 24 },
  imageTask: { src: "/mobile/history-icon-image-task.svg", size: 20 },
  text: { src: "/mobile/history-icon-text-lightbulb.svg", size: 28, shadow: true },
  homework: { src: "/mobile/history-icon-homework-pencil.svg", size: 28, shadow: true },
  nature: { src: "/mobile/history-icon-nature-leaf.svg", size: 28, shadow: true },
  math: { src: "/mobile/history-icon-math-calculator.svg", size: 28, shadow: true },
  english: { src: "/mobile/history-icon-english-abc.svg", size: 28, shadow: true },
  voice: { src: "/mobile/history-icon-voice-microphone.svg", size: 20 },
} satisfies Record<string, HistoryIcon>;

function weekContaining(timestamp: number) {
  const start = new Date(timestamp);
  start.setHours(0, 0, 0, 0);
  const daysSinceMonday = (start.getDay() + 6) % 7;
  start.setDate(start.getDate() - daysSinceMonday);

  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  end.setHours(23, 59, 59, 999);

  return {
    startAt: start.getTime(),
    endAt: end.getTime(),
    label: `${start.getMonth() + 1}/${start.getDate()}–${end.getMonth() + 1}/${end.getDate()}`,
  };
}

function currentWeek() {
  return weekContaining(Date.now());
}

function conversationIcon(
  conversation: Conversation,
  category: ConversationCategory,
  hasImage: boolean,
  wasProtected: boolean,
  wasBlocked: boolean,
): HistoryIcon {
  if (hasImage) {
    return wasBlocked ? historyIcons.pendingImage : wasProtected ? historyIcons.protectedImage : historyIcons.imageTask;
  }

  if (category === "voice") {
    return historyIcons.voice;
  }

  const topic = `${conversation.topic ?? ""} ${conversation.title}`;
  if (/自然|恐龍|植物|火山|海水|昆蟲/.test(topic)) {
    return historyIcons.nature;
  }
  if (/數學|三角形|分數|加法|減法|乘法|除法/.test(topic)) {
    return historyIcons.math;
  }
  if (/英文|英語|english/i.test(topic)) {
    return historyIcons.english;
  }
  if (/寫作|作文|故事|描寫|角色|段落|一句話/.test(topic)) {
    return historyIcons.homework;
  }

  return historyIcons.text;
}

function conversationRecord(conversation: Conversation): HistoryRecord {
  const userMessages = conversation.messages.filter((message) => message.role === "user");
  const hasImage = userMessages.some((message) => message.hasImage);
  const wasProtected = userMessages.some((message) => message.protected);
  const wasBlocked = conversation.messages.some((message) => message.blocked);
  const hasReply = conversation.messages.some((message) => message.role === "assistant");
  const category: ConversationCategory = conversation.category === "voice" ? "voice" : "text";

  return {
    id: conversation.id,
    title: conversation.title,
    updatedAt: conversation.updatedAt,
    category,
    metadataCategory: hasImage ? "圖片" : category === "voice" ? "語音" : "文字",
    href: `/mobile/history/${conversation.id}`,
    icon: conversationIcon(conversation, category, hasImage, wasProtected, wasBlocked),
    status: wasBlocked ? "待確認" : hasReply ? "已回覆" : "處理中",
    statusTone: wasBlocked || !hasReply ? "pending" : "safe",
    description: wasBlocked
      ? "安全檢查已攔截這則內容。"
      : wasProtected
        ? "個資已自動保護，無需家長核准。"
        : undefined,
  };
}

function formatRecordTime(timestamp: number) {
  const date = new Date(timestamp);
  const today = new Date();
  const dateLabel = date.toDateString() === today.toDateString()
    ? "今天"
    : `${date.getMonth() + 1}/${date.getDate()}`;
  const timeLabel = date.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false });
  return `${dateLabel} ${timeLabel}`;
}

export function MobileHistoryPage() {
  const { ready: conversationsReady, conversations } = useConversationStore();
  const { ready: draftsReady, drafts } = useWritingStore();
  const [filter, setFilter] = useState<HistoryFilter>("all");
  const thisWeek = currentWeek();
  const records = useMemo(() => {
    const conversationRecords = conversations.map(conversationRecord);
    const writingRecords: HistoryRecord[] = drafts.map((draft) => ({
      id: `draft-${draft.id}`,
      title: draft.subject,
      updatedAt: draft.updatedAt,
      category: "homework",
      metadataCategory: "作業",
      href: `/mobile/history/draft-${draft.id}`,
      icon: historyIcons.homework,
      status: draft.chat_history.some((message) => message.role === "assistant") ? "已回覆" : "處理中",
      statusTone: draft.chat_history.some((message) => message.role === "assistant") ? "safe" : "pending",
    }));

    return [...conversationRecords, ...writingRecords].sort((left, right) => right.updatedAt - left.updatedAt);
  }, [conversations, drafts]);
  const categoryRecords = filter === "all" ? records : records.filter((record) => record.category === filter);
  const thisWeekRecords = categoryRecords.filter((record) => record.updatedAt >= thisWeek.startAt && record.updatedAt <= thisWeek.endAt);
  const week = thisWeekRecords.length > 0 || categoryRecords.length === 0
    ? thisWeek
    : weekContaining(categoryRecords[0].updatedAt);
  const filteredRecords = categoryRecords.filter((record) => record.updatedAt >= week.startAt && record.updatedAt <= week.endAt);
  const isCurrentWeek = week.startAt === thisWeek.startAt;
  const ready = conversationsReady && draftsReady;

  return (
    <section className="flex h-full flex-col bg-[#fffcf7]">
      <header className="flex h-16 shrink-0 items-center gap-2 bg-white px-4">
        <div className="grid size-[38px] shrink-0 place-items-center rounded-[12px] bg-[#d63a37] text-[18px] font-bold leading-[27px] text-white" aria-hidden="true">✦</div>
        <div className="min-w-0 flex-1 overflow-hidden">
          <h1 className="truncate text-[18px] font-bold leading-7">{isCurrentWeek ? "本週提問紀錄" : "歷史提問紀錄"}</h1>
          <p className="truncate text-[12px] font-medium leading-[18px] tracking-[0.2px] text-[#506058]">小宇 · {week.label}</p>
        </div>
        <Link className="grid size-10 shrink-0 place-items-center rounded-full" href="/mobile/notify/" aria-label="通知">
          <img src="/mobile/nav-notification-action.svg" width="20" height="20" alt="" aria-hidden="true" />
        </Link>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="flex flex-col gap-3 px-4 py-4">
          <section className="flex flex-col gap-[10px]" aria-label="紀錄分類篩選">
            <p className="text-[14px] font-medium leading-5 tracking-[0.1px] text-black">{week.label} · {filteredRecords.length} 筆互動紀錄</p>
            <div className="flex h-11 gap-2" role="group" aria-label="篩選紀錄類別">
              {filters.map(({ id, label }) => {
                const isSelected = filter === id;
                return (
                  <button
                    aria-pressed={isSelected}
                    className={`flex h-11 min-w-0 flex-1 items-center justify-center rounded-2xl border px-2 text-[13px] font-medium leading-5 transition-colors ${isSelected ? "border-[#d63a37] bg-[#fff0ee] text-[#c02d32]" : "border-[#dde3df] bg-white text-[#506058]"}`}
                    key={id}
                    onClick={() => setFilter(id)}
                    type="button"
                  >
                    {label}
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] font-medium leading-[18px] tracking-[0.2px] text-black">
              {isCurrentWeek
                ? "點選紀錄，查看提問、AI 回覆與安全狀態。"
                : `本週沒有${filter === "all" ? "互動" : filters.find((item) => item.id === filter)?.label}紀錄，以下顯示最近有紀錄的一週。`}
            </p>
          </section>

          {!ready ? (
            <p className="rounded-2xl border border-[#dde3df] bg-white p-4 text-[13px] leading-5 text-[#506058]">載入對話紀錄中…</p>
          ) : filteredRecords.length ? (
            <ul className="flex flex-col gap-3">
              {filteredRecords.map((record) => (
                <li key={record.id}>
                  <Link className="flex items-start gap-3 rounded-2xl border border-[#dde3df] bg-white p-4 shadow-[0_8px_12px_rgba(20,33,26,0.08)]" href={record.href}>
                    <span className={`size-7 shrink-0 ${record.icon.shadow ? "drop-shadow-[0_2px_3px_rgba(20,33,26,0.06)]" : ""}`} aria-hidden="true">
                      <img className="block" src={record.icon.src} width={record.icon.size} height={record.icon.size} alt="" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[14px] font-medium leading-5 tracking-[0.1px] text-black">{record.title}</span>
                      <span className="mt-2 flex items-center gap-2">
                        <span className="min-w-0 flex-1 truncate text-[11px] font-medium leading-[18px] tracking-[0.2px] text-[#506058]">小宇 · {record.metadataCategory} · {formatRecordTime(record.updatedAt)}</span>
                        <span className={`shrink-0 rounded-full px-3 py-2 text-[12px] font-medium leading-[18px] tracking-[0.2px] ${record.statusTone === "safe" ? "bg-[#ddf5ea] text-[#177049]" : "bg-[#fff8d9] text-[#8a6400]"}`}>{record.status}</span>
                      </span>
                      {record.description ? <span className="mt-2 block text-[13px] leading-[18px] tracking-[0.2px] text-[#506058]">{record.description}</span> : null}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-2xl border border-[#dde3df] bg-white p-4 text-[13px] leading-5 text-[#506058]">
              {filter === "all" ? "目前還沒有互動紀錄。" : "目前沒有這個分類的互動紀錄。"}
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export function MobileHistoryDetail({ conversationId }: { conversationId: string }) {
  const { ready: conversationsReady, getConversation } = useConversationStore();
  const { ready: draftsReady, drafts } = useWritingStore();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const isDraft = conversationId.startsWith("draft-");
  const draftId = isDraft ? conversationId.slice("draft-".length) : "";
  const conversation = isDraft ? undefined : getConversation(conversationId);
  const draft = drafts.find((item) => item.id === draftId);
  const ready = conversationsReady && draftsReady;
  const messages = conversation?.messages.filter((message) => message.role !== "system-note") ?? draft?.chat_history ?? [];
  const timestamp = conversation?.updatedAt ?? draft?.updatedAt;
  const hasProtectedMessages = messages.some((message) => "protected" in message && message.protected);
  const hasAssistantReply = messages.some((message) => message.role === "assistant");
  const conversationType = conversation?.category === "voice" ? "Web 語音" : "Web 文字";
  const topic = conversation?.topic || (draft ? "作業" : "");
  const detailTime = timestamp
    ? `${timestampDate(timestamp)} ${timestampTime(timestamp)}`
    : "";

  return (
    <section className="relative flex h-full flex-col bg-[#fffcf7]">
      <header className="flex h-16 shrink-0 items-center gap-2 bg-white px-4">
        <Link className="grid size-10 shrink-0 place-items-center rounded-full text-[#c02d32]" href="/mobile/history/" aria-label="返回對話紀錄">
          <ArrowLeft aria-hidden="true" size={24} strokeWidth={2} />
        </Link>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-[18px] font-bold leading-7">對話詳情</h1>
          <p className="truncate text-[12px] font-medium leading-[18px] tracking-[0.2px] text-[#506058]">
            {detailTime}{detailTime && topic ? " · " : ""}{topic}
          </p>
        </div>
        <Link className="grid size-10 shrink-0 place-items-center rounded-full" href="/mobile/notify/" aria-label="通知">
          <img src="/mobile/nav-notification-action.svg" width="20" height="20" alt="" aria-hidden="true" />
        </Link>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <div className="px-4 pt-3">
          <p className="text-[12px] leading-[19px] text-[#13221b]">
            小宇 · {conversationType} · {detailTime}{hasProtectedMessages ? " · 已保護" : ""}
          </p>
        </div>
        <div className="flex flex-col gap-4 px-4 pb-6 pt-4">
          {!ready ? <p className="text-[13px] leading-5 text-[#506058]">載入對話中…</p> : null}
          {ready && !conversation && !draft ? <p className="text-[13px] leading-5 text-[#506058]">找不到這筆對話。</p> : null}
          {messages.map((message, index) => {
            if (message.role === "system-note") {
              return null;
            }

            const isUser = message.role === "user";
            const isProtected = isUser && "protected" in message && message.protected;
            const hasImage = "hasImage" in message && message.hasImage;

            return (
              <div className="flex flex-col gap-2" key={`${message.role}-${index}`}>
                <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                  <div className={`w-fit max-w-[calc(100%-16px)] rounded-2xl px-3 py-3 ${isUser ? "bg-[#f4f0ff]" : "bg-white"}`}>
                    <p className={`mb-1 text-[12px] font-medium leading-[18px] tracking-[0.2px] ${isUser ? "text-[#506058]" : "text-[#177049]"}`}>
                      {isUser ? "小宇" : "智靈 AI"}
                    </p>
                    <p className="whitespace-pre-wrap break-words text-[14px] leading-6 text-[#13221b]">
                      {message.content || (hasImage ? "圖片提問" : "")}
                    </p>
                  </div>
                </div>
                {isProtected ? (
                  <div className="flex flex-col items-start gap-2">
                    <span className="rounded-full bg-[#ddf5ea] px-3 py-2 text-[12px] font-medium leading-[18px] tracking-[0.2px] text-[#177049]">
                      PII PROTECTED · 個資已保護
                    </span>
                    <p className="text-[14px] leading-[22px] text-[#506058]">
                      姓名與學校已移除；原始個資未送出 AI。
                    </p>
                  </div>
                ) : null}
              </div>
            );
          })}
          {ready && hasAssistantReply && (conversation || draft) ? (
            <section className="rounded-[20px] border border-[#eae1ff] bg-[#f4f0ff] p-4 shadow-[0_8px_12px_rgba(20,33,26,0.08)]" aria-label="AI 評估與回饋">
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 text-[#6650a4]">
                  <Zap aria-hidden="true" size={20} />
                  <h2 className="text-[14px] font-bold leading-[22px] tracking-[0.1px]">AI 評估</h2>
                </div>
                <p className="text-[12px] leading-5 text-[#506058]">
                  {hasProtectedMessages ? "已移除個資，改用適齡安全內容回覆。" : "這則 AI 回覆已通過安全檢查。"}
                </p>
                <p className="text-[12px] leading-5 text-[#506058]">
                  這是對提問與回答的判斷，不是對孩子的評分。
                </p>
                <button
                  className="mt-1 flex h-12 w-full items-center justify-center rounded-2xl border border-[#d63a37] bg-white px-4 text-[15px] font-medium leading-5 tracking-[0.1px] text-[#c02d32] transition-colors hover:bg-[#fff8f7] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#c02d32]"
                  onClick={() => setFeedbackOpen(true)}
                  type="button"
                >
                  提供 AI 回饋
                </button>
              </div>
            </section>
          ) : null}
        </div>
      </div>
      {feedbackOpen ? <MobileFeedbackModal onClose={() => setFeedbackOpen(false)} /> : null}
    </section>
  );
}

type FeedbackModalProps = {
  onClose: () => void;
};

function MobileFeedbackModal({ onClose }: FeedbackModalProps) {
  const [assessment, setAssessment] = useState<"agree" | "inaccurate" | null>(null);
  const [helpfulness, setHelpfulness] = useState<"helpful" | "improve" | null>(null);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const canSubmit = assessment !== null || helpfulness !== null;

  return (
    <div
      className="fixed inset-x-0 bottom-0 top-[88px] z-50 bg-[#13221b]/10"
      onClick={onClose}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          onClose();
        }
      }}
      role="presentation"
      tabIndex={-1}
    >
      <div
        aria-labelledby="mobile-feedback-title"
        aria-modal="true"
        className="absolute inset-x-0 bottom-0 top-4 flex flex-col rounded-t-[24px] bg-white"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-12 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <div className="mx-auto mt-4 h-[5px] w-10 rounded-full bg-[#dde3df]" />
          <header className="mt-6 flex items-center gap-2">
            <ThumbsUp aria-hidden="true" className="shrink-0 text-[#7252b8]" size={24} />
            <h2 className="min-w-0 flex-1 text-[19px] font-bold leading-7 text-[#13221b]" id="mobile-feedback-title">
              回饋 AI 回覆與評估
            </h2>
            <button
              aria-label="關閉回饋視窗"
              autoFocus
              className="grid size-10 shrink-0 place-items-center rounded-full text-[#c02d32] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#c02d32]"
              onClick={onClose}
              type="button"
            >
              <X aria-hidden="true" size={24} />
            </button>
          </header>

          {submitted ? (
            <div className="mt-8 rounded-2xl bg-[#ecf9f3] p-5 text-center">
              <p className="font-bold leading-6 text-[#177049]">感謝你的意見！</p>
              <p className="mt-2 text-[14px] leading-6 text-[#506058]">這是展示畫面，回饋不會送出或保存。</p>
              <button
                className="mt-5 h-12 w-full rounded-2xl bg-[#177049] font-medium text-white"
                onClick={onClose}
                type="button"
              >
                完成
              </button>
            </div>
          ) : (
            <>
              <p className="mt-5 whitespace-pre-line text-[14px] leading-[22px] text-[#506058]">
                {"你的意見將協助我們改善 AI。\n這裡不會對孩子的能力或表現評分。"}
              </p>

              <fieldset className="mt-5">
                <legend className="mb-3 text-[14px] font-medium leading-[22px] text-[#13221b]">AI 評估是否合適？</legend>
                <div className="grid grid-cols-2 gap-2">
                  <FeedbackChoice
                    onClick={() => setAssessment("agree")}
                    selected={assessment === "agree"}
                  >
                    同意 AI 評估
                  </FeedbackChoice>
                  <FeedbackChoice
                    onClick={() => setAssessment("inaccurate")}
                    selected={assessment === "inaccurate"}
                  >
                    AI 評估不準確
                  </FeedbackChoice>
                </div>
              </fieldset>

              <fieldset className="mt-4">
                <legend className="mb-3 text-[14px] font-medium leading-[22px] text-[#13221b]">AI 回答是否有幫助？</legend>
                <div className="grid grid-cols-2 gap-2">
                  <FeedbackChoice
                    onClick={() => setHelpfulness("helpful")}
                    selected={helpfulness === "helpful"}
                  >
                    回答有幫助
                  </FeedbackChoice>
                  <FeedbackChoice
                    onClick={() => setHelpfulness("improve")}
                    selected={helpfulness === "improve"}
                  >
                    回答需要改善
                  </FeedbackChoice>
                </div>
              </fieldset>

              <label className="mt-4 block text-[14px] font-medium leading-[22px] text-[#13221b]" htmlFor="mobile-feedback-comment">
                補充意見（選填）
                <textarea
                  className="mt-3 h-[72px] w-full resize-none rounded-[16px] border border-[#dde3df] bg-white px-4 py-4 text-[14px] font-normal leading-6 outline-none placeholder:text-[#13221b] focus:border-[#7252b8] focus:ring-2 focus:ring-[#7252b8]/20"
                  id="mobile-feedback-comment"
                  onChange={(event) => setComment(event.target.value)}
                  placeholder="寫下你的看法（選填）"
                  value={comment}
                />
              </label>

              <button
                className={`mt-3 h-[56px] w-full rounded-[18px] text-[16px] font-bold leading-6 transition-colors ${canSubmit ? "bg-[#c02d32] text-white hover:bg-[#a8262b]" : "cursor-not-allowed bg-[#e1e3e5] text-[#6d7277]"}`}
                disabled={!canSubmit}
                onClick={() => setSubmitted(true)}
                type="button"
              >
                {canSubmit ? "送出 AI 回饋" : "請先選擇至少一項"}
              </button>
              <p className="mt-4 text-[12px] leading-5 text-[#778078]">點選意見框切換輸入示意；內容與送出僅供展示。</p>
            </>
          )}
        </div>
        <div className="flex h-7 shrink-0 items-center justify-center">
          <div className="h-[5px] w-[134px] rounded-full bg-[#13221b]" />
        </div>
      </div>
    </div>
  );
}

function FeedbackChoice({
  children,
  onClick,
  selected,
}: {
  children: string;
  onClick: () => void;
  selected: boolean;
}) {
  return (
    <button
      aria-pressed={selected}
      className={`flex h-[56px] min-w-0 items-center justify-center rounded-[18px] border px-2 text-center text-[14px] font-medium leading-5 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#7252b8] ${selected ? "border-[#7252b8] bg-[#f4f0ff] text-[#6650a4]" : "border-[#dde3df] bg-white text-[#506058]"}`}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function timestampDate(timestamp: number) {
  const date = new Date(timestamp);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

function timestampTime(timestamp: number) {
  return new Date(timestamp).toLocaleTimeString("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}