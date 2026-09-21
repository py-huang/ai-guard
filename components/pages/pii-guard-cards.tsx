"use client";

import { inspectPii, type PiiPreview } from "@/lib/pii-preview";

type Props = {
  original: string;
  preview: PiiPreview;
  onRewrite: () => void;
  onAskParent: () => void;
  onEditSelf: () => void;
};

export function PiiDetectedCard({ original, preview, onRewrite, onAskParent, onEditSelf }: Props) {
  const kinds = [...new Set(preview.hits.map((hit) => hit.kind))];

  return (
    <section className="rounded-[28px] bg-[#fff0ee] p-6 sm:p-8">
      <p className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-medium text-[#c02d32]">送出前安全檢查</p>
      <p className="mt-4 text-sm text-[#c02d32]">我注意到</p>
      <h2 className="mt-1 text-[22px] font-bold leading-8">找到 {preview.hits.length} 個可以先藏起來的資料</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {kinds.map((kind) => (
          <span className="rounded-full bg-white px-3 py-1 text-sm text-[#c02d32]" key={kind}>
            {kind}
          </span>
        ))}
      </div>

      <div className="mt-5 rounded-[22px] bg-[#ecf9f3] p-4">
        <p className="text-xs font-medium text-[#177049]">你原本寫的是</p>
        <p className="mt-2 text-[17px] leading-8">
          {preview.highlighted.map((part, index) =>
            part.sensitive ? (
              <mark className="bg-transparent font-bold text-[#c02d32]" key={`${part.text}-${index}`}>
                {part.text}
              </mark>
            ) : (
              <span key={`${part.text}-${index}`}>{part.text}</span>
            )
          )}
        </p>
      </div>
      <p className="mt-3 text-sm text-[#c02d32]">我會拿掉姓名和學校，只保留你真正想問的內容。</p>

      <div className="mt-4 rounded-[22px] bg-[#ddf5ea] p-4">
        <p className="text-xs font-medium text-[#177049]">可以這樣問</p>
        <p className="mt-2 text-[17px] leading-8">{preview.safeText || original}</p>
      </div>

      <div className="mt-5 flex flex-wrap gap-3">
        <button className="h-12 rounded-full bg-[#d63a37] px-5 text-[15px] font-medium text-white" onClick={onRewrite} type="button">
          幫我改安全一點
        </button>
        <button className="h-12 rounded-full border border-[#d63a37] px-5 text-[15px] font-medium text-[#d63a37]" onClick={onAskParent} type="button">
          送給家長看
        </button>
        <button className="h-12 text-[15px] font-medium text-[#d63a37]" onClick={onEditSelf} type="button">
          我自己改
        </button>
      </div>
      <p className="mt-3 text-sm text-[#8a968f]">現在還沒有送出去。</p>
    </section>
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
    <section className="rounded-[28px] bg-[#ecf9f3] p-6 sm:p-8">
      <p className="inline-flex rounded-full bg-white px-3 py-1 text-xs font-medium text-[#177049]">送出前安全檢查</p>
      <h2 className="mt-4 text-[22px] font-bold leading-8">家長確認前，這段內容不會送給 AI。</h2>
      <p className="mt-2 text-sm text-[#506058]">你可以改用安全版本、修改問題，或先去問別的問題。</p>
      <div className="mt-5 rounded-[22px] bg-white p-4">
        <p className="text-xs font-medium text-[#177049]">建議的安全版本</p>
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
      <p className="mt-3 text-sm text-[#c02d32]">等待中的原問題不會送出；你仍可繼續探索其他內容。</p>
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
        <p className="inline-flex rounded-full bg-[#177049] px-3 py-1 text-xs text-white">已保護</p>
        <p className="mt-2 text-[17px] leading-8">{safeText}</p>
      </div>
      <div className="flex gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-full bg-[#fff0ee] text-lg">✦</span>
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
