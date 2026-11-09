"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

const tabs = [
  { href: "/mobile/", label: "總覽", icon: "/mobile/nav-overview.svg" },
  { href: "/mobile/history/", label: "紀錄", icon: "/mobile/nav-history.svg" },
  { href: "/mobile/confirm/", label: "待確認", icon: "/mobile/nav-confirm.svg" },
  { href: "/mobile/notify/", label: "通知", icon: "/mobile/nav-notifications.svg" },
];

export function MobileShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [scale, setScale] = useState(1);
  const [time, setTime] = useState("--:--");

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

  return (
    <div className="flex h-dvh w-full items-center justify-center overflow-hidden bg-[#111]">
      <div
        className="flex h-[844px] w-[390px] shrink-0 flex-col overflow-hidden bg-[#fffcf7] text-[#13221b]"
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
                  <img src={icon} width="24" height="24" alt="" aria-hidden="true" />
                  <span className="w-20 text-center text-[11px] leading-[18px] tracking-[0.2px]">{label}</span>
                </Link>
              );
            })}
          </div>
          <div className="flex h-[26px] w-full items-center justify-center">
            <div className="h-[5px] w-[134px] rounded-full bg-[#13221b]" />
          </div>
        </nav>
      </div>
    </div>
  );
}