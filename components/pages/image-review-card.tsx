import { SafetyCardShell } from "@/components/pages/pii-guard-cards";

type ImageReviewCardProps = {
  originalUrl: string;
  redactedUrl: string;
  changed: boolean;
  onUseSafe: () => void;
  onAskParent: () => void;
  onReplace: () => void;
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

export function ImagePiiScanningCard({ labels }: { labels?: string[] }) {
  const found = labels && labels.length > 0 ? labels : ["姓名", "學校"];

  return (
    <SafetyCardShell badge="圖片安全檢查" footer="圖片現在還沒有送給 AI。" title="圖片裡有資料可以先隱藏">
      <div className="flex flex-col gap-3.5">
        {found.map((label) => (
          <div className="flex min-h-[54px] flex-wrap items-center gap-x-5 gap-y-2 rounded-[14px] bg-white py-3 pl-4 pr-4" key={label}>
            <p className="w-[90px] shrink-0 text-base font-medium text-[#c02d32]">找到</p>
            <p className="min-w-0 flex-1 text-lg font-bold text-[#13221b]">{label}</p>
            <span className="inline-flex h-8 items-center rounded-2xl bg-[#ecf9f3] px-4 text-base font-medium text-[#177049]">先保護再分享</span>
          </div>
        ))}
      </div>
      <p className="mt-[30px] flex items-center gap-2.5 text-lg font-medium text-[#c02d32]">
        正在建立遮罩預覽…
        <LoadingDots />
      </p>
    </SafetyCardShell>
  );
}

export function ImageReviewCard({ originalUrl, redactedUrl, changed, onUseSafe, onAskParent, onReplace }: ImageReviewCardProps) {
  return (
    <SafetyCardShell badge="圖片安全檢查" footer="你決定前，圖片還沒有送給 AI。" title="圖片裡有資料可以先隱藏">
      <div className="rounded-[16px] bg-white p-4">
        <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start">
          <figure>
            <div className="mb-3 flex items-center gap-2">
              <p className="text-sm font-bold">原始圖片</p>
              <span className="rounded-full bg-[#fff0ee] px-3 py-1 text-xs text-[#c02d32]">不會送出</span>
            </div>
            <img alt="原始圖片，不會送給 AI" className="h-[220px] w-full rounded-[16px] border border-[#dde3df] bg-white object-contain" src={originalUrl} />
          </figure>
          <p className="hidden self-center text-center text-[#8a968f] md:block">→</p>
          <figure>
            <div className="mb-3 flex items-center gap-2">
              <p className="text-sm font-bold">安全版本</p>
              <span className="rounded-full bg-[#ddf5ea] px-3 py-1 text-xs text-[#177049]">可送出</span>
            </div>
            <img alt="已遮罩的安全版本" className="h-[220px] w-full rounded-[16px] border border-[#dde3df] bg-white object-contain" src={redactedUrl} />
          </figure>
        </div>
      </div>

      <div className="mt-4 rounded-[14px] bg-white p-4">
        <p className="font-bold">{changed ? "已先把臉和文字個資塗黑" : "這張圖沒有找到需要藏起來的資料"}</p>
        {changed ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {["人臉", "文字個資"].map((label) => (
              <span className="rounded-full bg-[#ecf9f3] px-3 py-1 text-xs text-[#177049]" key={label}>
                {label}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button className="h-12 rounded-full bg-[#d63a37] px-5 text-[15px] font-medium text-white" onClick={onUseSafe} type="button">
          使用安全圖片
        </button>
        <button className="h-12 rounded-full border border-[#d63a37] px-5 text-[15px] font-medium text-[#d63a37]" onClick={onAskParent} type="button">
          送給家長看
        </button>
        <button className="h-12 rounded-full border border-[#d63a37] px-5 text-[15px] font-medium text-[#d63a37]" onClick={onReplace} type="button">
          換一張圖片
        </button>
      </div>
    </SafetyCardShell>
  );
}
