"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { ReadingAssistToggle } from "@/components/reading-assist-toggle";
import { RecentConversations } from "@/components/recent-conversations";
import { ZhuyinScope } from "@/components/zhuyin-scope";
import { cn } from "@/lib/utils";

type PageName = "探索首頁" | "探索主題" | "對話紀錄" | "AI 安全小幫手";

type NavigationItem = {
  label: PageName;
  href: string;
  iconSrc: string;
  activeIconSrc: string;
};

const navigationItems: NavigationItem[] = [
  {
    label: "探索首頁",
    href: "/",
    iconSrc: "/navigation/sidebar-home.svg",
    activeIconSrc: "/navigation/sidebar-home-active.svg",
  },
  {
    label: "探索主題",
    href: "/theme",
    iconSrc: "/navigation/sidebar-explore.svg",
    activeIconSrc: "/navigation/sidebar-explore-active.svg",
  },
  {
    label: "對話紀錄",
    href: "/history",
    iconSrc: "/navigation/sidebar-history.svg",
    activeIconSrc: "/navigation/sidebar-history-active.svg",
  },
  {
    label: "AI 安全小幫手",
    href: "/safety",
    iconSrc: "/navigation/sidebar-safety.svg",
    activeIconSrc: "/navigation/sidebar-safety-active.svg",
  },
];

type ChildrenShellProps = {
  children?: ReactNode;
  activeItem?: PageName;
  accountName?: string;
};

export function ChildrenShell({
  children,
  activeItem = "探索首頁",
  accountName = "小小",
}: ChildrenShellProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-[#fffcf7] text-[#13221b]">
      <header className="fixed inset-x-0 top-0 z-50 flex h-20 items-center justify-between bg-white px-4 lg:h-[72px] lg:px-6">
        <div className="flex items-center gap-3 lg:contents">
          <button
            aria-controls="mobile-navigation"
            aria-expanded={mobileMenuOpen}
            aria-label={mobileMenuOpen ? "關閉選單" : "開啟選單"}
            className="grid size-10 place-items-center text-[#506058] lg:hidden"
            onClick={() => setMobileMenuOpen((isOpen) => !isOpen)}
            type="button"
          >
            {mobileMenuOpen ? (
              <X className="size-8" strokeWidth={2.5} />
            ) : (
              <Menu className="size-8" strokeWidth={2.5} />
            )}
          </button>
          <Link
            aria-label="遠傳智靈 AI 心守護首頁"
            className="flex h-14 items-center gap-3 lg:h-10 lg:gap-3 lg:w-[362px]"
            href="/"
          >
            <img className="size-14 lg:size-10" src="/brand-mark.svg" alt="" aria-hidden="true" />
            <span className="whitespace-nowrap text-[26px] font-bold leading-none lg:hidden">AI 心守護</span>
            <span className="hidden text-[18px] font-bold leading-7 lg:inline">遠傳智靈｜AI 心守護</span>
          </Link>
        </div>

        <div className="flex h-16 shrink-0 items-center gap-4 lg:h-12">
          <a
            aria-label="新對話"
            className="hidden h-12 items-center justify-center gap-1.5 rounded-2xl bg-[#d63a37] px-3 text-[15px] font-medium text-white lg:inline-flex"
            href="/chat"
          >
            <img className="size-5 shrink-0" src="/navigation/new-chat-plus.svg" alt="" aria-hidden="true" />
            <span className="whitespace-nowrap">新對話</span>
          </a>
          <div className="hidden lg:block">
            <ReadingAssistToggle />
          </div>
          <button
            className="grid size-16 place-items-center rounded-full bg-[#dceeff] text-[26px] font-bold text-[#25324a] lg:h-12 lg:w-[46px] lg:rounded-[22px] lg:text-[15px]"
            type="button"
          >
            {accountName.slice(0, 1)}
          </button>
        </div>
      </header>

      {mobileMenuOpen && (
        <>
          <button
            aria-label="關閉選單"
            className="fixed inset-x-0 bottom-0 top-20 z-40 bg-black/20 lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            type="button"
          />
          <aside
            id="mobile-navigation"
            className="fixed inset-x-0 top-20 z-40 bg-white px-6 py-6 shadow-lg lg:hidden"
          >
            <a
              className="flex h-12 items-center justify-center gap-1.5 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium text-white"
              href="/chat"
              onClick={() => setMobileMenuOpen(false)}
            >
              <img className="size-5 shrink-0" src="/navigation/new-chat-plus.svg" alt="" aria-hidden="true" />
              <span>新對話</span>
            </a>
            <nav className="mt-4" aria-label="主要導覽">
              {navigationItems.map(({ label, href, iconSrc, activeIconSrc }) => {
                const isActive = activeItem === label;

                return (
                  <Link
                    className={cn(
                      "flex h-14 items-center rounded-2xl text-lg font-medium",
                      isActive ? "bg-[#f4f0ff] text-[#13221b]" : "text-[#506058]"
                    )}
                    href={href}
                    key={label}
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    <span className="grid size-14 shrink-0 place-items-center">
                      <img
                        alt=""
                        aria-hidden="true"
                        className={isActive ? "size-[52px]" : "size-5"}
                        src={isActive ? activeIconSrc : iconSrc}
                      />
                    </span>
                    {label}
                  </Link>
                );
              })}
            </nav>
          </aside>
        </>
      )}

      <ZhuyinScope className="mt-20 flex min-h-[calc(100dvh-80px)] lg:mt-[72px] lg:min-h-[calc(100dvh-72px)]">
        <aside className="hidden w-[220px] shrink-0 flex-col bg-white px-4 pt-6 pb-7 lg:flex">
          <a
            aria-label="新對話"
            className="flex h-12 w-[180px] self-center items-center justify-center gap-1.5 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium text-white transition-colors hover:bg-[#bd2e2c]"
            href="/chat"
          >
            <img className="size-5 shrink-0" src="/navigation/new-chat-plus.svg" alt="" aria-hidden="true" />
            <span className="whitespace-nowrap">新對話</span>
          </a>

          <nav className="mt-4" aria-label="主要導覽">
            {navigationItems.map(({ label, href, iconSrc, activeIconSrc }) => {
              const isActive = activeItem === label;

              return (
                <Link
                  className={cn(
                    "flex h-14 w-full items-center whitespace-nowrap rounded-2xl text-left text-lg font-medium tracking-[0.1px] transition-colors",
                    isActive
                      ? "bg-[#f4f0ff] text-[#13221b]"
                      : "text-[#506058] hover:bg-[#f7f8f7]"
                  )}
                  href={href}
                  key={label}
                >
                  <span className="grid size-14 shrink-0 place-items-center overflow-hidden">
                    <img
                      alt=""
                      aria-hidden="true"
                      className={cn(
                        isActive
                          ? "size-[52px] drop-shadow-[0px_1.083px_1.625px_rgba(20,33,26,0.06)]"
                          : "size-5"
                      )}
                      src={isActive ? activeIconSrc : iconSrc}
                    />
                  </span>
                  <span className="whitespace-nowrap">{label}</span>
                </Link>
              );
            })}
          </nav>

          <RecentConversations />

          <p className="mt-auto text-base font-medium text-[#8a968f]">低年級模式 · 7 歲</p>
        </aside>

        <main className="min-w-0 flex-1 bg-[#fffcf7]">{children}</main>
      </ZhuyinScope>
    </div>
  );
}
