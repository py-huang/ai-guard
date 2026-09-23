"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useConversationStore } from "@/store/conversation-store";

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
  const router = useRouter();
  const { createConversation } = useConversationStore();

  function startNewChat() {
    const conversation = createConversation("新對話");
    router.push(`/chat/${conversation.id}`);
  }

  return (
    <div className="min-h-dvh bg-[#fffcf7] text-[#13221b]">
      <header className="flex h-[72px] items-center justify-between bg-white px-4 py-[10px] sm:px-6 sm:pt-[14px]">
        <Link className="flex h-10 items-center gap-3 sm:w-[362px]" href="/" aria-label="遠傳智靈 AI 心守護首頁">
          <img className="size-10" src="/brand-mark.svg" alt="" aria-hidden="true" />
          <span className="text-[18px] font-bold leading-7">遠傳智靈｜AI 心守護</span>
        </Link>

        <div className="flex h-12 shrink-0 items-center gap-4">
          <ReadingAssistToggle />
          <button className="grid h-12 w-[46px] place-items-center rounded-[22px] bg-[#dceeff] text-[15px] font-bold text-[#25324a]">
            {accountName.slice(0, 1)}
          </button>
        </div>
      </header>

      <ZhuyinScope className="flex min-h-[calc(100dvh-72px)]">
        <aside className="hidden w-[220px] shrink-0 flex-col bg-white px-4 pt-6 pb-7 lg:flex">
          <button
            aria-label="新對話"
            className="flex h-12 w-[180px] self-center items-center justify-center gap-1.5 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium text-white transition-colors hover:bg-[#bd2e2c]"
            onClick={startNewChat}
            type="button"
          >
            <img className="size-5" src="/navigation/new-chat-plus.svg" alt="" aria-hidden="true" />
            新對話
          </button>

          <nav className="mt-4" aria-label="主要導覽">
            {navigationItems.map(({ label, href, iconSrc, activeIconSrc }) => {
              const isActive = activeItem === label;

              return (
                <Link
                  className={cn(
                    "flex h-14 w-[188px] items-center rounded-2xl text-left text-lg font-medium tracking-[0.1px] transition-colors",
                    isActive
                      ? "bg-[#f4f0ff] text-[#13221b]"
                      : "text-[#506058] hover:bg-[#f7f8f7]"
                  )}
                  href={href}
                  key={label}
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