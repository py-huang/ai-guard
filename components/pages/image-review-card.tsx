"use client";

import { useState } from "react";

function LoadingDots() {
  return (
    <span className="inline-flex h-[22px] items-center gap-1.5" aria-hidden="true">
      <span className="size-1.5 animate-pulse rounded-full bg-[#c02d32]" />
      <span className="size-1.5 animate-pulse rounded-full bg-[#c02d32] [animation-delay:150ms]" />
      <span className="size-1.5 animate-pulse rounded-full bg-[#c02d32] [animation-delay:300ms]" />
    </span>
  );
}

export function ImageSoftScanPreview() {
  return (
    <section className="mx-auto flex h-[320px] w-full max-w-[520px] flex-col items-center rounded-[28px] border border-solid border-[#dde3df] bg-[#ecf9f3] px-10 pt-[54px] shadow-[0_4px_4px_rgba(0,0,0,0.25)]">
      <div className="relative size-[120px] shrink-0 overflow-hidden">
        <img alt="" aria-hidden="true" className="absolute left-0 top-0 max-w-none origin-top-left scale-[1.25]" height={96} src="/safety/illustration-protected-image.svg" width={96} />
      </div>
      <p className="mt-4 text-center text-lg font-medium leading-7 text-[#13221b]">正在看圖片能不能安全分享</p>
      <div className="mt-5 h-1 w-full max-w-[360px] overflow-hidden rounded-[2px] bg-[#cfe8dc]">
        <div className="ag-soft-scan-line h-full w-full rounded-[2px] bg-[#2ea56f]" />
      </div>
      <p className="mt-5 text-center text-[13px] font-normal leading-[22px] text-[#506058]">圖片還沒有送給 AI</p>
    </section>
  );
}

export function ImageScanningCard() {
  return (
    <section className="rounded-3xl bg-[#fff0ee] px-[22px] pb-8 pt-5">
      <div className="flex h-[42px] items-center gap-3.5">
        <img alt="" aria-hidden="true" className="size-[42px]" src="/discover/safety-shield-clean.svg" />
        <p className="inline-flex h-8 items-center rounded-2xl bg-white px-3 text-lg font-medium text-[#c02d32]">圖片安全檢查</p>
      </div>

      <h2 className="mt-[26px] text-2xl font-bold leading-[34px] text-[#13221b]">圖片裡有資料可以先隱藏</h2>

      <div className="mt-5 flex flex-col gap-3.5">
        {["姓名", "學校"].map((label) => (
          <div className="flex min-h-[54px] flex-wrap items-center gap-x-5 gap-y-2 rounded-[14px] bg-white py-3 pl-4 pr-4" key={label}>
            <p className="w-[90px] shrink-0 text-base font-medium text-[#c02d32]">找到</p>
            <p className="min-w-0 flex-1 text-lg font-bold text-[#13221b]">{label}</p>
            <span className="inline-flex h-8 items-center rounded-2xl bg-[#ecf9f3] px-4 text-lg font-medium text-[#177049]">先保護再分享</span>
          </div>
        ))}
      </div>

      <p className="mt-[30px] flex items-center gap-2.5 text-lg font-medium text-[#c02d32]">
        正在建立遮罩預覽…
        <LoadingDots />
      </p>
      <p className="mt-2 text-base font-normal text-[#506058]">圖片現在還沒有送給 AI。</p>
    </section>
  );
}

type ImageReviewCardProps = {
  originalUrl: string;
  redactedUrl: string;
  changed: boolean;
  fields: string[];
  onUseSafe: () => void;
  onAskParent: () => void;
  onReplace: () => void;
};

const WHY_ITEMS = [
  { n: "1", label: "高度私密的身體影像", highlight: false },
  { n: "2", label: "暴力或血腥內容", highlight: false },
  { n: "3", label: "偷拍或侵犯隱私", highlight: false },
  { n: "4", label: "證件與金融資料", highlight: true },
  { n: "5", label: "其他不適合兒童內容", highlight: false },
];

type ImageBlockedCardProps = {
  onReplace: () => void;
};

export function ImageBlockedCard({ onReplace }: ImageBlockedCardProps) {
  const [whyOpen, setWhyOpen] = useState(false);

  return (
    <section className="w-full">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        <div className="flex w-full max-w-[720px] flex-col gap-4 rounded-3xl bg-[#fff0ee] px-8 py-10 sm:px-16">
          <div>
            <h2 className="text-[22px] font-bold leading-8 text-[#13221b]">這張圖片不適合分享</h2>
            <p className="mt-2 text-[15px] font-normal leading-6 text-[#506058]">我在送出前先幫你擋下來了。</p>
          </div>
          <div className="relative h-[340px] w-full overflow-hidden rounded-[18px] bg-[#dde3df]">
            <div className="absolute left-9 top-11 h-[72px] w-[360px] max-w-[calc(100%-72px)] rounded-[22px] bg-[#c4cec8]" />
            <div className="absolute left-[86px] top-[138px] h-[88px] w-[260px] max-w-[calc(100%-120px)] rounded-[30px] bg-[#b5c0ba]" />
            <div className="absolute inset-0 rounded-[18px] bg-[#213129]/[0.72]" />
            <div className="absolute left-1/2 top-1/2 size-[84px] -translate-x-1/2 -translate-y-1/2 rounded-[28px] bg-white" />
            <div className="absolute left-1/2 top-1/2 grid size-[120px] -translate-x-1/2 -translate-y-1/2 place-items-center drop-shadow-[0_2px_3px_rgba(20,33,26,0.06)]">
              <img alt="" aria-hidden="true" height={96} src="/safety/illustration-shield-blocked.svg" width={96} />
            </div>
          </div>
          <p className="inline-flex h-8 w-fit items-center rounded-2xl bg-white px-3 text-xs font-medium leading-[19px] text-[#c02d32]">已安全攔截</p>
          <p className="text-xl font-bold leading-[30px] text-[#13221b]">請換一張其他圖片</p>
          <p className="text-sm font-normal leading-[22px] text-[#506058]">如果你不確定原因，可以先看看安全說明。</p>
          <div className="flex flex-wrap gap-3">
            <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium tracking-[0.1px] text-white" onClick={onReplace} type="button">
              換一張圖片
              <img alt="" aria-hidden="true" height={20} src="/safety/icon-refresh.svg" width={20} />
            </button>
            <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={() => setWhyOpen((open) => !open)} type="button">
              看看為什麼
              <img alt="" aria-hidden="true" height={20} src="/safety/icon-chevron-right.svg" width={20} />
            </button>
          </div>
        </div>

        {whyOpen ? (
          <aside className="w-full max-w-[288px] rounded-3xl border border-solid border-[#dde3df] bg-white px-5 py-[22px]">
            <p className="text-lg font-bold leading-7 text-[#13221b]">哪些圖片不應上傳？</p>
            <p className="mt-3.5 text-xs font-normal leading-[19px] text-[#506058]">我會用簡單的方式告訴你原因。</p>
            <ol className="mt-3.5 flex flex-col gap-3.5">
              {WHY_ITEMS.map((item) => (
                <li className="flex items-center gap-3.5" key={item.n}>
                  <span className={`grid size-9 shrink-0 place-items-center rounded-xl text-[11px] font-bold ${item.highlight ? "bg-[#fff8d9] text-[#8a6400]" : "bg-[#f7f8f7] text-[#506058]"}`}>{item.n}</span>
                  <span className="text-[13px] font-medium leading-[21px] text-[#13221b]">{item.label}</span>
                </li>
              ))}
            </ol>
          </aside>
        ) : null}
      </div>

      <p className="mt-5 text-xs font-medium leading-[19px] text-[#c02d32]">圖片未送出 AI，也不會出現在對話紀錄中。</p>
    </section>
  );
}

export function ImageReviewCard({ originalUrl, redactedUrl, changed, fields, onUseSafe, onAskParent, onReplace }: ImageReviewCardProps) {
  const detectedTitle = fields.length > 0 ? `已遮罩 ${fields.length} 個欄位` : changed ? "已先把需要藏的資料塗黑" : "這張圖沒有找到需要藏起來的資料";

  return (
    <section className="w-full rounded-[28px] bg-white">
      <div className="rounded-3xl border border-solid border-[#dde3df] bg-white p-6">
        <h2 className="text-[22px] font-bold leading-8 text-[#13221b]">這張圖片裡有一些可以先藏起來的資料</h2>
        <p className="mt-2 text-[15px] font-normal leading-6 text-[#506058]">這張圖片可以使用，但會先移除不需要提供給 AI 的內容。</p>

        <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start">
          <figure>
            <div className="mb-3.5 flex flex-wrap items-center gap-2">
              <p className="text-sm font-bold leading-[22px] text-[#13221b]">原始圖片</p>
              <span className="inline-flex h-8 w-fit items-center rounded-2xl bg-[#fff0ee] px-3 text-xs font-medium leading-[19px] text-[#c02d32]">不會送出</span>
            </div>
            <img alt="原始圖片，不會送給 AI" className="h-[220px] w-full rounded-2xl border border-solid border-[#dde3df] bg-white object-contain" src={originalUrl} />
          </figure>
          <p className="hidden self-center text-[#8a968f] md:block" aria-hidden="true">
            →
          </p>
          <figure>
            <div className="mb-3.5 flex flex-wrap items-center gap-2">
              <p className="text-sm font-bold leading-[22px] text-[#13221b]">安全版本</p>
              <span className="inline-flex h-8 w-fit items-center rounded-2xl bg-[#ddf5ea] px-3 text-xs font-medium leading-[19px] text-[#177049]">可送出</span>
            </div>
            <img alt="已遮罩的安全版本" className="h-[220px] w-full rounded-2xl border border-solid border-[#dde3df] bg-white object-contain" src={redactedUrl} />
          </figure>
        </div>
      </div>

      <div className="mt-4 rounded-[18px] bg-[#ecf9f3] px-[18px] py-3.5">
        <p className="text-[15px] font-bold leading-[23px] text-[#13221b]">{detectedTitle}</p>
        {fields.length > 0 ? (
          <div className="mt-3 flex flex-wrap gap-2">
            {fields.map((label) => (
              <span className="inline-flex h-8 w-fit items-center rounded-2xl bg-white px-3 text-xs font-medium leading-[19px] text-[#177049]" key={label}>
                {label}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium tracking-[0.1px] text-white" onClick={onUseSafe} type="button">
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-shield-check.svg" width={20} />
          使用安全圖片
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onAskParent} type="button">
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-parent-review.svg" width={20} />
          送給家長看
        </button>
        <button className="inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32]" onClick={onReplace} type="button">
          <img alt="" aria-hidden="true" height={20} src="/safety/icon-image.svg" width={20} />
          換一張圖片
        </button>
        <p className="text-xs font-medium leading-[19px] text-[#c02d32] md:ml-auto">你決定前，圖片還沒有送給 AI。</p>
      </div>
    </section>
  );
}
