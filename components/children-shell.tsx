"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";

import { AiHelper } from "@/components/pages/ai-helper";
import { Chat } from "@/components/pages/chat";
import { ChatHistory } from "@/components/pages/chat-history";
import { DiscoverHome } from "@/components/pages/discover-home";
import { DiscoverTheme } from "@/components/pages/discover-theme";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PageName = "探索首頁" | "探索主題" | "對話紀錄" | "AI 安全小幫手";

type NavigationItem = {
  label: PageName;
  iconSrc: string;
  activeIconSrc: string;
};

const navigationItems: NavigationItem[] = [
  {
    label: "探索首頁",
    iconSrc: "/navigation/sidebar-home.svg",
    activeIconSrc: "/navigation/sidebar-home-active.svg",
  },
  {
    label: "探索主題",
    iconSrc: "/navigation/sidebar-explore.svg",
    activeIconSrc: "/navigation/sidebar-explore-active.svg",
  },
  {
    label: "對話紀錄",
    iconSrc: "/navigation/sidebar-history.svg",
    activeIconSrc: "/navigation/sidebar-history-active.svg",
  },
  {
    label: "AI 安全小幫手",
    iconSrc: "/navigation/sidebar-safety.svg",
    activeIconSrc: "/navigation/sidebar-safety-active.svg",
  },
];

const recentConversations = ["恐龍為什麼會滅絕？", "夏天作文怎麼開始？"];

const pageComponents = {
  探索首頁: DiscoverHome,
  探索主題: DiscoverTheme,
  對話紀錄: ChatHistory,
  "AI 安全小幫手": AiHelper,
};

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
  const [selectedItem, setSelectedItem] = useState<PageName | null>(activeItem);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const ActivePage = selectedItem ? pageComponents[selectedItem] : null;

  return (
    <div className="min-h-dvh bg-[#fffcf7] text-[#13221b]">
      <header className="flex h-[72px] items-center justify-between bg-white px-4 py-[10px] sm:pl-6 sm:pr-8 sm:pt-[14px] xl:pr-[130px]">
        <Link className="flex h-10 items-center gap-3 sm:w-[362px]" href="/" aria-label="遠傳智靈 AI 心守護首頁">
          <img className="size-10" src="/brand-mark.svg" alt="" aria-hidden="true" />
          <span className="text-[18px] font-bold leading-7">遠傳智靈｜AI 心守護</span>
        </Link>

        <div className="flex h-12 shrink-0 items-center gap-4">
          <button className="hidden h-[34px] w-[92px] rounded-[17px] bg-[#ecf6ff] text-xs font-medium text-[#25324a] sm:block">
            閱讀輔助
          </button>
          <button className="grid h-12 w-[46px] place-items-center rounded-[22px] bg-[#dceeff] text-[15px] font-bold text-[#25324a]">
            {accountName.slice(0, 1)}
          </button>
        </div>
      </header>

      <div className="flex min-h-[calc(100dvh-72px)]">
        <aside className="hidden w-[220px] shrink-0 flex-col bg-white px-4 pt-6 pb-7 lg:flex">
          <Button
            className="h-12 w-[180px] self-center rounded-2xl bg-[#d63a37] px-4 text-[15px] hover:bg-[#bd2e2c]"
            onClick={() => {
              setSelectedItem(null);
              setIsChatOpen(true);
            }}
            size="lg"
          >
            <img className="size-5" src="/navigation/new-chat-plus.svg" alt="" aria-hidden="true" />
            新對話
          </Button>

          <nav className="mt-4" aria-label="主要導覽">
            {navigationItems.map(({ label, iconSrc, activeIconSrc }) => {
              const isActive = selectedItem === label;

              return (
                <button
                  className={cn(
                    "flex h-14 w-[188px] items-center rounded-2xl text-left text-lg font-medium tracking-[0.1px] transition-colors",
                    isActive
                      ? "bg-[#f4f0ff] text-[#13221b]"
                      : "text-[#506058] hover:bg-[#f7f8f7]"
                  )}
                  key={label}
                  onClick={() => {
                    setSelectedItem(label);
                    setIsChatOpen(false);
                  }}
                  type="button"
                >
                  <span className="grid size-14 shrink-0 place-items-center overflow-hidden">
                    <img
                      className={cn(
                        isActive
                          ? "size-[52px] drop-shadow-[0px_1.083px_1.625px_rgba(20,33,26,0.06)]"
                          : "size-5"
                      )}
                      src={isActive ? activeIconSrc : iconSrc}
                      alt=""
                      aria-hidden="true"
                    />
                  </span>
                  {label}
                </button>
              );
            })}
          </nav>

          <section className="mt-6 pl-2.5" aria-labelledby="recent-conversations-title">
            <h2 id="recent-conversations-title" className="text-base font-medium text-[#8a968f]">
              最近對話
            </h2>
            <ul className="mt-1.5 space-y-1.5 text-base text-[#506058]">
              {recentConversations.map((conversation) => (
                <li key={conversation}>
                  <Link className="block truncate hover:text-[#177049]" href="/">
                    {conversation}
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <p className="mt-auto text-base font-medium text-[#8a968f]">低年級模式 · 7 歲</p>
        </aside>

        <main className="min-w-0 flex-1 bg-[#fffcf7]">{children ?? (isChatOpen ? <Chat /> : ActivePage && <ActivePage />)}</main>
      </div>
    </div>
  );
}