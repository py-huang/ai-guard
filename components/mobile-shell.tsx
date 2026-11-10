"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { useConversationStore } from "@/store/conversation-store";
import type { SafetyEvent } from "@/types/conversation";

function notificationDescription(event: SafetyEvent) {
  if (event.type === "critical") {
    return "系統已攔截一則高風險內容，點擊查看。";
  }
  if (event.type === "pending") {
    return "有一則提問需要家長確認，點擊查看。";
  }
  return "偵測到可能包含個人資料的提問，點擊查看。";
}

const tabs = [
  { href: "/mobile/", label: "總覽", icon: "/mobile/nav-overview.svg" },
  { href: "/mobile/history/", label: "紀錄", icon: "/mobile/nav-history.svg" },
  { href: "/mobile/confirm/", label: "待確認", icon: "/mobile/nav-confirm.svg" },
  { href: "/mobile/notify/", label: "通知", icon: "/mobile/nav-notifications.svg" },
];

export function MobileShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { newSafetyNotification: notification, dismissSafetyNotification } = useConversationStore();
  const [scale, setScale] = useState(1);
  const [time, setTime] = useState("--:--");

  useEffect(() => {
    if (!notification) {
      return;
    }

    const timeout = window.setTimeout(() => dismissSafetyNotification(notification), 4_000);
    return () => window.clearTimeout(timeout);
  }, [notification, dismissSafetyNotification]);

  useEffect(() => {
    function updateScale() {
      setScale(Math.min(1, window.innerWidth / 390, window.innerHeight / 844));
    }

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, []);

  useEffect(() => {
    let timer: number;
    const updateTime = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false }));
      timer = window.setTimeout(updateTime, 60_000 - now.getSeconds() * 1_000 - now.getMilliseconds());
    };

    updateTime();
    return () => window.clearTimeout(timer);
  }, []);

  const notificationParams = notification
    ? new URLSearchParams({ conversation: notification.conversationId, event: notification.event.id }).toString()
    : "";
  const notificationHref = notification
    ? `${notification.event.type === "pending" ? "/mobile/confirm/" : "/mobile/notify/"}?${notificationParams}`
    : "";

  return (
    <div className="flex h-dvh w-full items-center justify-center overflow-hidden bg-[#111]">
      <div
        className="relative flex h-[844px] w-[390px] shrink-0 flex-col overflow-hidden bg-[#fffcf7] text-[#13221b]"
        style={{ transform: `scale(${scale})`, transformOrigin: "center center" }}
      >
        <div className="flex h-6 shrink-0 items-center justify-between bg-white px-5 text-[12px] font-medium tracking-[0.2px]">
          <span className="w-16">{time}</span>
          <img src="/mobile/status-indicators.svg" width="58" height="14" alt="行動網路、Wi-Fi 與電量狀態" />
        </div>

        <main className="min-h-0 flex-1">{children}</main>

        <nav className="flex h-[84px] shrink-0 flex-col items-center bg-white shadow-[0_-4px_9px_rgba(20,56,41,0.06)]" aria-label="手機版導覽">
          <div className="flex h-[58px] w-[358px] items-center">
            {tabs.map(({ href, label, icon }) => {
              const isActive = href === "/mobile/"
                ? pathname === "/mobile" || pathname === "/mobile/"
                : pathname.startsWith(href.replace(/\/$/, ""));

              return (
                <Link
                  key={href}
                  aria-current={isActive ? "page" : undefined}
                  className={`flex h-[58px] w-[89.5px] shrink-0 flex-col items-center justify-center gap-[3px] rounded-[14px] pb-1 pt-1.5 ${isActive ? "bg-[#ecf9f3] text-[#177049]" : "text-[#506058]"}`}
                  href={href}
                >
                  <img src={isActive && href === "/mobile/confirm/" ? "/mobile/nav-confirm-active.svg" : icon} width="24" height="24" alt="" aria-hidden="true" />
                  <span className="w-20 text-center text-[11px] leading-[18px] tracking-[0.2px]">{label}</span>
                </Link>
              );
            })}
          </div>
          <div className="flex h-[26px] w-full items-center justify-center">
            <div className="h-[5px] w-[134px] rounded-full bg-[#13221b]" />
          </div>
        </nav>
        {notification && (
          <Link
            href={notificationHref}
            onClick={() => dismissSafetyNotification(notification)}
            aria-live="polite"
            className="absolute left-4 right-4 top-[50px] z-50 flex flex-col gap-2 rounded-[20px] border border-[#dde3df] bg-white p-3 text-left shadow-[0_2px_6px_rgba(20,33,26,0.06)]"
          >
            <span className="absolute right-3 top-3 text-[12px] font-medium leading-[18px] tracking-[0.2px] text-[#506058]">
              {notification.event.read ? "已讀" : "未讀"}
            </span>
            <span className="flex items-center gap-2">
              <span className="grid size-[38px] shrink-0 place-items-center rounded-[12px] bg-[#d63a37] text-[18px] font-bold leading-[27px] text-white">✦</span>
              <span className="flex w-[286px] min-w-0 flex-col gap-[2px]">
                <span className="flex items-center gap-2 text-[12px] font-medium leading-[18px] tracking-[0.2px] text-[#506058]">
                  <span className="w-[228px] shrink-0">遠傳智靈｜AI 心守護</span>
                  <span className="w-[30px] shrink-0">剛剛</span>
                </span>
                <span className="text-[14px] font-medium leading-5 tracking-[0.1px] text-[#13221b]">小宇有一則安全提醒</span>
              </span>
            </span>
            <span className="text-[14px] leading-[22px] text-[#506058]">{notificationDescription(notification.event)}</span>
          </Link>
        )}
      </div>
    </div>
  );
}