"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { ChatAiAvatar } from "@/components/chat-ai-avatar";
import { inspectPii, type PiiPreview } from "@/lib/pii-preview";

type Props = {
  original: string;
  preview: PiiPreview;
  onRewrite: () => void;
  onAskParent: () => void;
  onEditSelf: () => void;
};

function LoadingDots() {
  return (
    <span className="inline-flex items-center gap-1" aria-hidden="true">
      <span className="size-1.5 animate-pulse rounded-full bg-[#c02d32]" />
      <span className="size-1.5 animate-pulse rounded-full bg-[#c02d32] [animation-delay:150ms]" />
      <span className="size-1.5 animate-pulse rounded-full bg-[#c02d32] [animation-delay:300ms]" />
    </span>
  );
}

export function SafetyCardShell({
  badge,
  title,
  footer,
  children,
}: {
  badge: string;
  title: string;
  footer: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-[24px] bg-[#fff0ee] px-[22px] pb-8 pt-5">
      <div className="flex h-[42px] items-center gap-3.5">
        <img alt="" aria-hidden="true" className="size-[42px]" src="/discover/safety-shield-clean.svg" />
        <p className="inline-flex h-8 items-center rounded-2xl bg-white px-3 text-lg font-medium text-[#c02d32]">{badge}</p>
      </div>
      <h2 className="mt-[26px] text-2xl font-bold leading-[34px] text-[#13221b]">{title}</h2>
      <div className="mt-5">{children}</div>
      <p className="mt-6 text-base text-[#506058]">{footer}</p>
    </section>
  );
}

function DetectedRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-h-[54px] flex-wrap items-center gap-x-5 gap-y-2 rounded-[14px] bg-white py-3 pl-4 pr-4">
      <p className="w-[90px] shrink-0 text-base font-medium text-[#c02d32]">{label}</p>
      <p className="min-w-0 flex-1 text-lg font-bold text-[#13221b]">{value}</p>
      <span className="inline-flex h-8 items-center rounded-2xl bg-[#ecf9f3] px-4 text-base font-medium text-[#177049]">先保護再分享</span>
    </div>
  );
}

export function PiiDetectedCard({ preview, onRewrite, onAskParent, onEditSelf }: Props) {
  const rewriteRef = useRef(onRewrite);
  rewriteRef.current = onRewrite;

  useEffect(() => {
    const timer = window.setTimeout(() => rewriteRef.current(), 1400);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <SafetyCardShell badge="送出前安全檢查" footer="現在還沒有送出去。" title="這裡有幾個資料不需要一起分享">
      <div className="flex flex-col gap-3.5">
        {preview.hits.map((hit, index) => (
          <DetectedRow key={`${hit.kind}-${hit.value}-${index}`} label={hit.kind} value={hit.value} />
        ))}
      </div>
      <p className="mt-[30px] flex items-center gap-2.5 text-lg font-medium text-[#c02d32]">
        我可以先幫你改成安全版本。
        <LoadingDots />
      </p>
      <div className="mt-5 flex flex-wrap gap-3">
        <button className="h-12 text-[15px] font-medium text-[#d63a37]" onClick={onAskParent} type="button">
          送給家長看
        </button>
        <button className="h-12 text-[15px] font-medium text-[#d63a37]" onClick={onEditSelf} type="button">
          我自己改
        </button>
      </div>
    </SafetyCardShell>
  );
}

export function PiiRewriteCard({ preview, onPutBack, onAskParent, onEditSelf }: Omit<Props, "original" | "onRewrite"> & { onPutBack: () => void }) {
  return (
    <section className="rounded-[28px] bg-[#ecf9f3] p-6 sm:p-8">
      <p className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-medium text-[#177049]">送出前安全檢查</p>
      <h2 className="mt-4 text-[22px] font-bold leading-8">好了！我先把不需要分享的資料拿掉了。</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {preview.hits.map((hit) => (
          <span className="rounded-full bg-white px-3 py-1 text-sm text-[#c02d32]" key={`${hit.kind}-${hit.value}`}>
            {hit.kind} · {hit.kind === "姓名" || hit.kind === "學校" ? hit.value : "已隱藏"}
          </span>
        ))}
      </div>
      <div className="mt-5 rounded-[22px] bg-white p-4">
        <p className="text-xs font-medium text-[#177049]">安全版本</p>
        <p className="mt-2 text-[17px] leading-8">{preview.safeText}</p>
      </div>
      <p className="mt-3 text-sm text-[#506058]">已移除姓名與學校，只保留回答需要的城市層級位置。</p>
      <div className="mt-5 flex flex-wrap gap-3">
        <button className="h-12 rounded-full bg-[#d63a37] px-5 text-[15px] font-medium text-white" onClick={onPutBack} type="button">
          放回問題框
        </button>
        <button className="h-12 rounded-full border border-[#d63a37] px-5 text-[15px] font-medium text-[#d63a37]" onClick={onAskParent} type="button">
          送給家長看
        </button>
        <button className="h-12 text-[15px] font-medium text-[#d63a37]" onClick={onEditSelf} type="button">
          我自己改
        </button>
      </div>
      <p className="mt-3 text-sm text-[#c02d32]">改好後不會馬上送出去，你可以先看看。</p>
    </section>
  );
}

export function ParentPendingCard({ safeText, onUseSafe, onEdit, onAskElse, onDemoApprove }: { safeText: string; onUseSafe: () => void; onEdit: () => void; onAskElse: () => void; onDemoApprove: () => void }) {
  return (
    <SafetyCardShell badge="家長確認" footer="確認前，這段內容不會送出去。" title="已經送給家長看囉">
      <p className="flex items-center gap-2.5 text-lg font-medium text-[#c02d32]">
        正在等待家長確認…
        <LoadingDots />
      </p>
      <div className="mt-6 rounded-[14px] bg-white p-4">
        <p className="text-sm font-medium text-[#177049]">建議的安全版本</p>
        <p className="mt-2 text-[17px] leading-8">{safeText}</p>
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        <button className="h-12 rounded-full bg-[#d63a37] px-5 text-[15px] font-medium text-white" onClick={onUseSafe} type="button">
          改用安全版本
        </button>
        <button className="h-12 rounded-full border border-[#d63a37] px-5 text-[15px] font-medium text-[#d63a37]" onClick={onEdit} type="button">
          修改問題
        </button>
        <button className="h-12 text-[15px] font-medium text-[#d63a37]" onClick={onAskElse} type="button">
          先問別的問題
        </button>
      </div>
      <button className="mt-4 text-sm text-[#8a968f] underline" onClick={onDemoApprove} type="button">
        示範：家長已確認
      </button>
    </SafetyCardShell>
  );
}

export function ParentApprovedCard({ safeText, onContinue, onEdit, onAskElse }: { safeText: string; onContinue: () => void; onEdit: () => void; onAskElse: () => void }) {
  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <p className="rounded-full bg-[#ddf5ea] px-4 py-2 text-sm text-[#177049]">✓ 家長確認好了</p>
      </div>
      <div className="ml-auto max-w-[520px] rounded-[24px] bg-[#eee6ff] px-5 py-4">
        <p className="inline-flex rounded-full bg-[#177049] px-3 py-1 text-xs text-white">已保護</p>
        <p className="mt-2 text-[17px] leading-8">{safeText}</p>
      </div>
      <div className="flex gap-3">
        <ChatAiAvatar />
        <div>
          <p className="font-bold">我們會使用安全版本。</p>
          <p className="mt-1 text-sm text-[#506058]">按下「繼續」後才會送出；原始姓名與學校不會傳給 AI。</p>
        </div>
      </div>
      <section className="rounded-[28px] bg-[#ecf9f3] p-6">
        <p className="font-bold">準備好了嗎？</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button className="h-12 rounded-full bg-[#d63a37] px-6 text-[15px] font-medium text-white" onClick={onContinue} type="button">
            繼續
          </button>
          <button className="h-12 rounded-full border border-[#d63a37] px-5 text-[15px] font-medium text-[#d63a37]" onClick={onEdit} type="button">
            修改問題
          </button>
          <button className="h-12 text-[15px] font-medium text-[#d63a37]" onClick={onAskElse} type="button">
            先問別的問題
          </button>
        </div>
      </section>
    </div>
  );
}

export function inspectDraft(text: string) {
  return inspectPii(text);
}
