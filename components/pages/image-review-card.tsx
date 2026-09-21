type ImageReviewCardProps = {
  originalUrl: string;
  redactedUrl: string;
  changed: boolean;
  onUseSafe: () => void;
  onAskParent: () => void;
  onReplace: () => void;
};

export function ImageReviewCard({ originalUrl, redactedUrl, changed, onUseSafe, onAskParent, onReplace }: ImageReviewCardProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-[0_8px_30px_rgba(20,33,26,0.04)]">
      <h2 className="text-[22px] font-bold leading-8">這張圖片裡有一些可以先藏起來的資料</h2>
      <p className="mt-2 text-[15px] leading-6 text-[#506058]">這張圖片可以使用，但會先移除不需要提供給 AI 的欄位。</p>

      <div className="mt-5 rounded-[24px] border border-[#dde3df] p-4">
        <div className="grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start">
          <figure>
            <div className="mb-3 flex items-center gap-2">
              <p className="text-sm font-bold">原始圖片</p>
              <span className="rounded-full bg-[#fff0ee] px-3 py-1 text-xs text-[#c02d32]">不會送出</span>
            </div>
            <img alt="原始圖片，不會送給 AI" className="h-[220px] w-full rounded-[16px] border border-[#dde3df] object-contain bg-white" src={originalUrl} />
          </figure>
          <p className="hidden self-center text-center text-[#8a968f] md:block">→</p>
          <figure>
            <div className="mb-3 flex items-center gap-2">
              <p className="text-sm font-bold">安全版本</p>
              <span className="rounded-full bg-[#ddf5ea] px-3 py-1 text-xs text-[#177049]">可送出</span>
            </div>
            <img alt="已遮罩的安全版本" className="h-[220px] w-full rounded-[16px] border border-[#dde3df] object-contain bg-white" src={redactedUrl} />
          </figure>
        </div>
      </div>

      <div className="mt-4 rounded-[18px] bg-[#ecf9f3] p-4">
        <p className="font-bold">{changed ? "已先把臉和文字個資塗黑" : "這張圖沒有找到需要藏起來的資料"}</p>
        {changed ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {["人臉", "文字個資"].map((label) => (
              <span className="rounded-full bg-white px-3 py-1 text-xs text-[#177049]" key={label}>
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
        <p className="text-xs text-[#c02d32] md:ml-auto">你決定前，圖片還沒有送給 AI。</p>
      </div>
    </section>
  );
}
