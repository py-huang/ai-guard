"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import {
  Compass,
  Diamond,
  Headphones,
  History,
  MoreHorizontal,
  Plus,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { AiHelper } from "@/components/pages/ai-helper";
import { ChatHistory } from "@/components/pages/chat-history";
import { DiscoverHome } from "@/components/pages/discover-home";
import { DiscoverTheme } from "@/components/pages/discover-theme";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PageName = "探索首頁" | "探索主題" | "對話紀錄" | "AI 安全小幫手";

type NavigationItem = {
  icon: typeof Compass;
  label: PageName;
};

const navigationItems: NavigationItem[] = [
  { icon: Sparkles, label: "探索首頁" },
  { icon: Diamond, label: "探索主題" },
  { icon: History, label: "對話紀錄" },
  { icon: ShieldCheck, label: "AI 安全小幫手" },
];

const recentConversations = ["恐龍為什麼會滅絕？", "夏天作文怎麼開始？"];

const pageComponents = {
  探索首頁: DiscoverHome,
  探索主題: DiscoverTheme,
  對話紀錄: ChatHistory,
  "AI 安全小幫手": AiHelper,
};

type AppShellProps = {
  children?: ReactNode;
  activeItem?: PageName;
  accountName?: string;
};

export function AppShell({
  children,
  activeItem = "探索首頁",
  accountName = "小小",
}: AppShellProps) {
  const [selectedItem, setSelectedItem] = useState(activeItem);
  const ActivePage = pageComponents[selectedItem];

  return (
    <div className="min-h-dvh bg-[#fffcf7] text-[#13221b]">
      <header className="flex h-[72px] items-center justify-between border-b border-[#edf0ed] bg-white px-4 sm:px-6">
        <Link className="flex items-center gap-3" href="/" aria-label="遠傳智靈 AI 心守護首頁">
          <span className="grid size-10 place-items-center rounded-[13px] bg-[#d63a37] text-white">
            <Sparkles className="size-5 fill-current" aria-hidden="true" />
          </span>
          <span className="text-[18px] font-bold leading-7">遠傳智靈｜AI 心守護</span>
        </Link>

        <div className="flex items-center gap-3 sm:gap-4">
          <button className="hidden h-[34px] rounded-full bg-[#ecf6ff] px-3 text-xs font-medium text-[#25324a] sm:block">
            <span className="flex items-center gap-1.5">
              <Headphones className="size-3.5" aria-hidden="true" />
              閱讀輔助
            </span>
          </button>
          <button className="grid size-12 place-items-center rounded-full bg-[#dceeff] text-[15px] font-bold text-[#25324a]">
            {accountName.slice(0, 1)}
          </button>
          <button className="grid size-8 place-items-center text-[#8a968f]" aria-label="更多選項">
            <MoreHorizontal className="size-5" aria-hidden="true" />
          </button>
        </div>
      </header>

      <div className="flex min-h-[calc(100dvh-72px)]">
        <aside className="hidden w-[220px] shrink-0 flex-col bg-white px-4 py-6 lg:flex">
          <Button className="h-12 w-full justify-start rounded-2xl bg-[#d63a37] px-4 text-sm hover:bg-[#bd2e2c]" size="lg">
            <Plus className="size-4" aria-hidden="true" />
            新對話
          </Button>

          <nav className="mt-6 space-y-1.5" aria-label="主要導覽">
            {navigationItems.map(({ icon: Icon, label }) => {
              const isActive = selectedItem === label;

              return (
                <button
                  className={cn(
                    "flex h-12 w-full items-center gap-3 rounded-[14px] px-3 text-[13px] transition-colors",
                    isActive
                      ? "bg-[#ecf9f3] font-bold text-[#13221b]"
                      : "text-[#506058] hover:bg-[#f7f8f7]"
                  )}
                  key={label}
                  onClick={() => setSelectedItem(label)}
                  type="button"
                >
                  <Icon className={cn("size-4", isActive ? "text-[#177049]" : "text-[#8a968f]")} aria-hidden="true" />
                  {label}
                </button>
              );
            })}
          </nav>

          <section className="mt-10" aria-labelledby="recent-conversations-title">
            <h2 id="recent-conversations-title" className="px-2.5 text-xs font-medium text-[#8a968f]">
              最近對話
            </h2>
            <ul className="mt-4 space-y-3 px-2.5 text-[13px] text-[#506058]">
              {recentConversations.map((conversation) => (
                <li key={conversation}>
                  <Link className="block truncate hover:text-[#177049]" href="/">
                    {conversation}
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          <p className="mt-auto px-1 text-xs font-medium text-[#8a968f]">低年級模式 · 7 歲</p>
        </aside>

        <main className="min-w-0 flex-1 bg-[#fffcf7]">{children ?? <ActivePage />}</main>
      </div>
    </div>
  );
}