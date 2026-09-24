"use client";

import { useEffect, useId, useRef, useState } from "react";

type Props = {
  disabled?: boolean;
  onPickFile: (file: File) => void;
  onUnsupported?: (message: string) => void;
};

const OPTIONS = [
  { id: "camera", label: "拍照", sub: "使用相機", accept: "image/*", capture: "environment" as const, highlight: false },
  { id: "image", label: "選擇圖片", sub: "從裝置上傳", accept: "image/*", highlight: true },
  { id: "file", label: "選擇檔案", sub: "PDF 或作業", accept: "image/*,.pdf,application/pdf", highlight: false },
] as const;

export function ComposerAttach({ disabled, onPickFile, onUnsupported }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) {
      return;
    }

    function onPointer(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function handleChange(file: File | undefined) {
    setOpen(false);
    if (!file) {
      return;
    }
    if (!file.type.startsWith("image/")) {
      onUnsupported?.("現在只能先檢查圖片，作業檔之後再一起看。");
      return;
    }
    onPickFile(file);
  }

  function pick(id: (typeof OPTIONS)[number]["id"]) {
    if (id === "camera") {
      cameraRef.current?.click();
      return;
    }
    if (id === "image") {
      imageRef.current?.click();
      return;
    }
    fileRef.current?.click();
  }

  return (
    <div className="relative" ref={rootRef}>
      <input ref={cameraRef} accept="image/*" capture="environment" className="hidden" type="file" onChange={(event) => handleChange(event.target.files?.[0])} />
      <input ref={imageRef} accept="image/*" className="hidden" type="file" onChange={(event) => handleChange(event.target.files?.[0])} />
      <input ref={fileRef} accept="image/*,.pdf,application/pdf" className="hidden" type="file" onChange={(event) => handleChange(event.target.files?.[0])} />
      <button
        aria-controls={menuId}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="新增內容"
        className="grid size-12 place-items-center rounded-full text-[#c02d32] hover:bg-[#fff0ee] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d63a37] active:bg-[#ffe4df] disabled:opacity-40"
        disabled={disabled}
        onClick={() => setOpen((value) => !value)}
        title="新增內容"
        type="button"
      >
        <img alt="" aria-hidden="true" className="size-5" height={20} src="/discover/composer-plus.svg" width={20} />
      </button>
      {open ? (
        <div
          className="absolute bottom-[calc(100%+10px)] left-0 z-20 w-[284px] rounded-[22px] border border-solid border-[#dde3df] bg-white px-4 pb-4 pt-[18px] shadow-[0px_10px_28px_-8px_rgba(20,33,26,0.1)]"
          id={menuId}
          role="menu"
        >
          <p className="text-base font-bold leading-6 text-[#13221b]">新增內容</p>
          <div className="mt-4 flex flex-col gap-1.5">
            {OPTIONS.map((option) => (
              <button
                className={`flex h-12 w-full items-center rounded-xl px-3.5 text-left ${option.highlight ? "bg-[#ecf9f3]" : "bg-white hover:bg-[#f7f8f7]"}`}
                key={option.id}
                onClick={() => pick(option.id)}
                role="menuitem"
                type="button"
              >
                <span className="w-[100px] text-[13px] font-bold leading-5 text-[#13221b]">{option.label}</span>
                <span className="text-[11px] font-normal leading-[18px] text-[#506058]">{option.sub}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
