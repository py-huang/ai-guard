"use client";

import { ChatAiAvatar } from "@/components/chat-ai-avatar";
import { ProtectedBadge } from "@/components/protected-badge";
import { inspectPii, type PiiPreview } from "@/lib/pii-preview";

type Props = {
  original: string;
  preview: PiiPreview;
  onRewrite: () => void;
  onAskParent: () => void;
  onEditSelf: () => void;
};

function joinKinds(kinds: string[]) {
  if (kinds.length === 0) {
    return "這些資料";
  }
  if (kinds.length === 1) {
    return kinds[0];
  }
  if (kinds.length === 2) {
    return `${kinds[0]}和${kinds[1]}`;
  }
  return `${kinds.slice(0, -1).join("、")}和${kinds[kinds.length - 1]}`;
}

export function PiiDetectedCard({ original, preview, onRewrite, onAskParent, onEditSelf }: Props) {
  const kinds = [...new Set(preview.hits.map((hit) => hit.kind))];

  return (
    <section className="flex flex-col gap-3 rounded-3xl bg-[#fff0ee] px-[22px] py-5">
      <div className="flex items-center gap-3.5">
        <div className="relative size-[42px] shrink-0 overflow-hidden rounded-[14px] bg-white">
          <img alt="" aria-hidden="true" className="absolute left-[5px] top-[5px] max-w-none origin-top-left scale-[0.333]" height={96} src="/safety/illustration-shield.svg" width={96} />
        </div>
        <p className="inline-flex h-8 items-center rounded-2xl bg-white px-3 text-xs font-medium leading-[19px] text-[#c02d32]">送出前安全檢查</p>
      </div>

      <div className="flex flex-col gap-2">
        <p className="text-xs font-medium leading-[18px] text-[#506058]">我注意到</p>
        <h2 className="text-2xl font-bold leading-[34px] text-[#13221b]">找到 {preview.hits.length} 個可以先藏起來的資料</h2>
        <div className="flex flex-wrap gap-2.5">
          {kinds.map((kind) => (
            <span className="rounded-2xl bg-white px-3.5 py-[7px] text-xs font-medium leading-[19px] text-[#c02d32]" key={kind}>
              {kind}
            </span>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-2 rounded-2xl bg-[#fff6f4] px-4 py-3.5">
        <p className="inline-flex h-8 w-fit shrink-0 items-center rounded-2xl bg-[#ddf5ea] px-3 text-xs font-medium leading-[19px] text-[#177049]">你原本寫的是</p>
        <p className="text-base font-medium leading-[26px] text-[#13221b]">
          {preview.highlighted.map((part, index) =>
            part.sensitive ? (
              <mark className="bg-transparent text-[#bf2e33]" key={`${part.text}-${index}`}>
                {part.text}
              </mark>
            ) : (
              <span key={`${part.text}-${index}`}>{part.text}</span>
            )
          )}
        </p>
      </div>

      <p className="text-sm font-medium leading-[22px] text-[#c02d32]">我會拿掉{joinKinds(kinds)}，只保留你真正想問的內容。</p>

      <div className="flex flex-col gap-2 rounded-2xl bg-[#e8f7f1] px-4 py-3.5">
        <p className="inline-flex h-8 w-fit shrink-0 items-center rounded-2xl bg-[#ddf5ea] px-3 text-xs font-medium leading-[19px] text-[#177049]">可以這樣問</p>
        <p className="text-base font-medium leading-[26px] text-[#13221b]">{preview.safeText || original}</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium tracking-[0.1px] text-white" onClick={onRewrite} type="button">
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-shield-check.svg" width={20} />
          幫我改安全一點
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onAskParent} type="button">
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-parent-review.svg" width={20} />
          送給家長看
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onEditSelf} type="button">
          我自己改
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-edit.svg" width={20} />
        </button>
      </div>
      <p className="text-xs font-normal leading-[18px] text-[#506058]">現在還沒有送出去。</p>
    </section>
  );
}

export function PiiRewriteCard({ preview, onPutBack, onAskParent, onEditSelf }: Omit<Props, "original" | "onRewrite"> & { onPutBack: () => void }) {
  const kinds = [...new Set(preview.hits.map((hit) => hit.kind))];

  return (
    <section className="flex flex-col gap-3.5 rounded-3xl bg-[#ecf9f3] px-[22px] py-5">
      <div className="flex items-center gap-3.5">
        <div className="relative size-[42px] shrink-0 overflow-hidden rounded-[14px] bg-white">
          <img alt="" aria-hidden="true" className="absolute left-[5px] top-[5px] max-w-none origin-top-left scale-[0.333]" height={96} src="/safety/illustration-shield-check.svg" width={96} />
        </div>
        <p className="inline-flex h-8 items-center rounded-2xl bg-white px-3 text-xs font-medium leading-[19px] text-[#177049]">送出前安全檢查</p>
      </div>

      <h2 className="text-2xl font-bold leading-[34px] text-[#13221b]">好了！我先把不需要分享的資料拿掉了。</h2>
      <p className="text-xs font-medium leading-[18px] text-[#506058]">找到的資料</p>
      <div className="flex flex-wrap gap-2.5">
        {preview.hits.map((hit) => (
          <span className="inline-flex h-8 items-center rounded-2xl bg-white px-3 text-xs font-medium leading-[19px] text-[#c02d32]" key={`${hit.kind}-${hit.value}`}>
            {hit.kind} · {hit.kind === "姓名" || hit.kind === "學校" ? hit.value : "已隱藏"}
          </span>
        ))}
      </div>

      <div className="flex flex-col gap-2 rounded-2xl bg-white px-4 py-3.5">
        <p className="inline-flex h-8 w-fit shrink-0 items-center rounded-2xl bg-[#ddf5ea] px-3 text-xs font-medium leading-[19px] text-[#177049]">安全版本</p>
        <p className="text-base font-medium leading-[26px] text-[#13221b]">{preview.safeText}</p>
      </div>

      <p className="text-[13px] font-normal leading-[21px] text-[#506058]">已移除{joinKinds(kinds)}，只保留回答需要的城市層級位置。</p>

      <div className="flex flex-wrap gap-3">
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium tracking-[0.1px] text-white" onClick={onPutBack} type="button">
          放回問題框
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-arrow-right.svg" width={20} />
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onAskParent} type="button">
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-parent-review.svg" width={20} />
          送給家長看
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onEditSelf} type="button">
          我自己改
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-edit.svg" width={20} />
        </button>
      </div>
      <p className="text-[11px] font-medium leading-[17px] text-[#c02d32]">改好後不會馬上送出去，你可以先看看。</p>
    </section>
  );
}

export function ParentPendingCard({ safeText, onUseSafe, onEdit, onAskElse, onDemoApprove }: { safeText: string; onUseSafe: () => void; onEdit: () => void; onAskElse: () => void; onDemoApprove: () => void }) {
  return (
    <section className="flex flex-col gap-3.5 rounded-3xl bg-[#ecf9f3] px-[22px] py-5">
      <div className="flex items-center gap-3.5">
        <div className="relative size-[42px] shrink-0 overflow-hidden rounded-[14px] bg-white">
          <img alt="" aria-hidden="true" className="absolute left-[5px] top-[5px] max-w-none origin-top-left scale-[0.333]" height={96} src="/safety/illustration-parent-review.svg" width={96} />
        </div>
        <p className="inline-flex h-8 w-fit shrink-0 items-center rounded-2xl bg-white px-3 text-xs font-medium leading-[19px] text-[#8a6400]">送出前安全檢查</p>
      </div>

      <h2 className="text-2xl font-bold leading-[34px] text-[#13221b]">家長確認前，這段內容不會送給 AI。</h2>
      <p className="text-[15px] font-normal leading-[25px] text-[#506058]">你可以改用安全版本、修改問題，或先去問別的問題。</p>

      <div className="flex flex-col gap-2 rounded-2xl bg-white px-4 py-3.5">
        <p className="inline-flex h-8 w-fit shrink-0 items-center rounded-2xl bg-[#ddf5ea] px-3 text-xs font-medium leading-[19px] text-[#177049]">建議的安全版本</p>
        <p className="text-[15px] font-medium leading-6 text-[#13221b]">{safeText}</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium tracking-[0.1px] text-white" onClick={onUseSafe} type="button">
          改用安全版本
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-arrow-right.svg" width={20} />
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onEdit} type="button">
          修改問題
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-edit.svg" width={20} />
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onAskElse} type="button">
          先問別的問題
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-chevron-right.svg" width={20} />
        </button>
      </div>
      <button className="self-start text-xs text-[#8a968f] underline" onClick={onDemoApprove} type="button">
        示範：家長已確認
      </button>
    </section>
  );
}

export function ParentApprovedCard({ safeText, onContinue, onEdit, onAskElse }: { safeText: string; onContinue: () => void; onEdit: () => void; onAskElse: () => void }) {
  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <p className="rounded-full bg-[#ddf5ea] px-4 py-2 text-sm text-[#177049]">✓ 家長確認好了</p>
      </div>
      <div className="ml-auto max-w-[520px] rounded-[24px] bg-[#eee6ff] px-5 py-4">
        <ProtectedBadge />
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
