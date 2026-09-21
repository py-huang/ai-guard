"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { CHILD_BLOCK_REPLY, classifyUnsafeText } from "@/lib/content-safety";
import { inspectPii, type PiiPreview } from "@/lib/pii-preview";
import { useConversationStore } from "@/store/conversation-store";
import type { ConversationMessage } from "@/types/conversation";
import {
  ParentApprovedCard,
  ParentPendingCard,
  PiiDetectedCard,
  PiiRewriteCard,
} from "@/components/pages/pii-guard-cards";

type GuardState = "none" | "detected" | "rewritten" | "parent-pending" | "parent-approved" | "image-review";

type ChatProps = {
  conversationId?: string;
};

export function Chat({ conversationId }: ChatProps) {
  const router = useRouter();
  const { ready, createConversation, getConversation, appendMessage, renameConversation } = useConversationStore();
  const conversation = conversationId ? getConversation(conversationId) : undefined;
  const fileRef = useRef<HTMLInputElement>(null);

  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [guard, setGuard] = useState<GuardState>("none");
  const [preview, setPreview] = useState<PiiPreview | null>(null);
  const [rawDraft, setRawDraft] = useState("");
  const [imageName, setImageName] = useState("");
  const [imageScanning, setImageScanning] = useState(false);

  const started = useRef(false);

  useEffect(() => {
    if (!ready || conversationId || started.current || typeof window === "undefined") {
      return;
    }

    started.current = true;
    const created = createConversation("新對話");
    router.replace(`/chat/${created.id}`);
  }, [conversationId, createConversation, ready, router]);

  useEffect(() => {
    if (!ready || !conversation || typeof window === "undefined") {
      return;
    }

    const pending = sessionStorage.getItem("ai-guard-pending");
    if (!pending) {
      return;
    }

    sessionStorage.removeItem("ai-guard-pending");
    setDraft(pending);
    startGuard(pending);
  }, [conversation?.id, ready]);

  async function sendSafeText(text: string, options?: { protected?: boolean; hasImage?: boolean }) {
    if (!conversation) {
      return;
    }

    const userMessage: ConversationMessage = {
      role: "user",
      content: text,
      protected: options?.protected,
      hasImage: options?.hasImage,
    };
    appendMessage(conversation.id, userMessage);
    if (conversation.title === "新對話") {
      renameConversation(conversation.id, text.slice(0, 24));
    }
    setDraft("");
    setGuard("none");
    setPreview(null);
    setRawDraft("");
    setBusy(true);
    setError("");

    const blocked = classifyUnsafeText(text);
    if (blocked) {
      appendMessage(conversation.id, { role: "assistant", content: CHILD_BLOCK_REPLY, blocked: true });
      setBusy(false);
      return;
    }

    try {
      const history = [...conversation.messages, userMessage]
        .filter((message) => message.role === "user" || message.role === "assistant")
        .map((message) => ({ role: message.role, content: message.content }));

      const response = await fetch("/api/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            {
              role: "system",
              content: "你是台灣國小兒童的學習夥伴。用繁體中文、短句回答。不要要求姓名、電話、地址或學校全名。",
            },
            ...history,
          ],
        }),
      });
      const data = (await response.json()) as { choices?: { message?: { content?: string } }[]; error?: string };
      const content = data.choices?.[0]?.message?.content?.trim();
      if (!response.ok || !content) {
        throw new Error(data.error || "暫時無法回覆。");
      }
      appendMessage(conversation.id, { role: "assistant", content });
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "暫時無法回覆。");
    } finally {
      setBusy(false);
    }
  }

  function startGuard(text: string) {
    const next = inspectPii(text);
    if (next.hits.length === 0) {
      void sendSafeText(text, { hasImage: Boolean(imageName) });
      return;
    }

    setRawDraft(text);
    setPreview(next);
    setGuard("detected");
  }

  function submitComposer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy || !conversation) {
      return;
    }
    startGuard(text);
  }

  function onPickImage(file: File | undefined) {
    if (!file) {
      return;
    }
    setImageName(file.name);
    setImageScanning(true);
    window.setTimeout(() => {
      setImageScanning(false);
      setGuard("image-review");
    }, 900);
  }

  if (!ready || !conversation) {
    return <p className="px-8 py-10 text-[#8a968f]">正在開始新對話…</p>;
  }

  const composerLocked = guard === "detected" || guard === "rewritten" || guard === "parent-pending" || guard === "image-review";

  return (
    <section className="flex min-h-[calc(100dvh-72px)] flex-col px-5 py-6 sm:px-10 lg:px-16">
      <div className="mx-auto flex w-full max-w-[860px] flex-1 flex-col">
        {conversation.messages.length === 0 && guard === "none" && !imageScanning ? (
          <div className="pt-6">
            <h1 className="text-[28px] font-bold">想問什麼都可以先打字</h1>
            <p className="mt-2 text-[#506058]">送出前會先檢查個人資料。紀錄裡只會留下安全版本。</p>
          </div>
        ) : null}

        <div className="mt-6 flex-1 space-y-5">
          {conversation.messages.map((message, index) =>
            message.role === "user" ? (
              <div className="ml-auto max-w-[520px] rounded-[24px] bg-[#eee6ff] px-5 py-4" key={`${message.content}-${index}`}>
                {message.protected ? <p className="mb-2 inline-flex rounded-full bg-[#177049] px-3 py-1 text-xs text-white">已保護</p> : null}
                <p className="text-[17px] leading-8">{message.content}</p>
              </div>
            ) : (
              <div className="flex max-w-[640px] gap-3" key={`${message.content}-${index}`}>
                <span className="grid size-10 shrink-0 place-items-center rounded-full bg-[#fff0ee]">✦</span>
                <div>
                  <p className="text-[17px] leading-8">{message.content}</p>
                  {message.blocked ? <p className="mt-2 text-sm text-[#c02d32]">這個問題沒有送給 AI。</p> : null}
                </div>
              </div>
            )
          )}

          {imageScanning ? <p className="rounded-[24px] bg-[#fff7e8] px-5 py-4">正在檢查圖片裡的臉與文字…原始圖片不會存進對話紀錄。</p> : null}

          {guard === "image-review" ? (
            <section className="rounded-[28px] bg-white p-6 shadow-[0_8px_30px_rgba(20,33,26,0.04)]">
              <h2 className="text-[22px] font-bold">這張圖片裡有一些可以先藏起來的資料</h2>
              <p className="mt-2 text-sm text-[#506058]">這張圖片可以使用，但會先移除不需要提供給 AI 的欄位。</p>
              <div className="mt-5 grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
                <div className="rounded-[22px] border border-[#dde3df] p-4">
                  <p className="text-sm text-[#c02d32]">原始圖片 · 不會送出</p>
                  <p className="mt-3 font-bold">已選擇：{imageName || "圖片"}</p>
                  <p className="mt-2 text-sm text-[#8a968f]">姓名、電話、學校會先塗黑。</p>
                </div>
                <p className="text-center text-[#8a968f]">→</p>
                <div className="rounded-[22px] border border-[#dde3df] bg-[#ecf9f3] p-4">
                  <p className="text-sm text-[#177049]">安全版本 · 可送出</p>
                  <div className="mt-4 space-y-2">
                    <p className="h-8 rounded-lg bg-[#cfe8da]" />
                    <p className="h-8 w-2/3 rounded-lg bg-[#cfe8da]" />
                    <p className="h-8 w-1/2 rounded-lg bg-[#cfe8da]" />
                  </div>
                </div>
              </div>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  className="h-12 rounded-full bg-[#d63a37] px-5 text-white"
                  onClick={() => {
                    const text = draft.trim() || "請看這張已遮罩的圖片，幫我看看可以怎麼問。";
                    void sendSafeText(text, { protected: true, hasImage: true });
                    setImageName("");
                  }}
                  type="button"
                >
                  使用安全圖片
                </button>
                <button className="h-12 rounded-full border border-[#d63a37] px-5 text-[#d63a37]" onClick={() => setGuard("parent-pending")} type="button">
                  送給家長看
                </button>
                <button
                  className="h-12 rounded-full border border-[#d63a37] px-5 text-[#d63a37]"
                  onClick={() => {
                    setImageName("");
                    setGuard("none");
                    fileRef.current?.click();
                  }}
                  type="button"
                >
                  換一張圖片
                </button>
              </div>
              <p className="mt-3 text-sm text-[#c02d32]">你決定前，圖片還沒有送給 AI。完整人臉／OCR 遮罩在 Python Gateway。</p>
            </section>
          ) : null}

          {guard === "detected" && preview ? (
            <PiiDetectedCard
              original={rawDraft}
              preview={preview}
              onRewrite={() => setGuard("rewritten")}
              onAskParent={() => setGuard("parent-pending")}
              onEditSelf={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
            />
          ) : null}

          {guard === "rewritten" && preview ? (
            <PiiRewriteCard
              preview={preview}
              onPutBack={() => {
                setDraft(preview.safeText);
                setGuard("none");
              }}
              onAskParent={() => setGuard("parent-pending")}
              onEditSelf={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
            />
          ) : null}

          {guard === "parent-pending" && preview ? (
            <ParentPendingCard
              safeText={preview.safeText}
              onUseSafe={() => {
                setDraft(preview.safeText);
                setGuard("none");
              }}
              onEdit={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
              onAskElse={() => {
                setDraft("");
                setGuard("none");
                setPreview(null);
              }}
              onDemoApprove={() => setGuard("parent-approved")}
            />
          ) : null}

          {guard === "parent-approved" && preview ? (
            <ParentApprovedCard
              safeText={preview.safeText}
              onContinue={() => void sendSafeText(preview.safeText, { protected: true, hasImage: Boolean(imageName) })}
              onEdit={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
              onAskElse={() => {
                setDraft("");
                setGuard("none");
                setPreview(null);
              }}
            />
          ) : null}

          {busy ? <p className="text-[#8a968f]">AI 正在想…</p> : null}
          {error ? <p className="text-[#c02d32]">{error}</p> : null}
        </div>

        <form className="sticky bottom-4 mt-8 flex h-[66px] items-center gap-2 rounded-full border border-[#dde3df] bg-white py-[9px] pl-2 pr-[10px]" onSubmit={submitComposer}>
          <input
            ref={fileRef}
            className="hidden"
            type="file"
            accept="image/*"
            onChange={(event) => onPickImage(event.target.files?.[0])}
          />
          <button className="grid size-12 place-items-center rounded-full text-[#d63a37]" onClick={() => fileRef.current?.click()} type="button" aria-label="新增附件">
            <img className="size-8" src="/discover/composer-plus.svg" alt="" />
          </button>
          <input
            className="min-w-0 flex-1 bg-transparent text-[18px] outline-none placeholder:text-[#8a968f]"
            value={draft}
            disabled={composerLocked || busy}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={composerLocked ? "這裡有你的名字和學校，先不要送出" : "想知道什麼？可以打字或用說的"}
          />
          <button className="grid size-12 place-items-center rounded-full bg-[#d63a37] text-white disabled:bg-[#d7ddd9]" disabled={composerLocked || busy || !draft.trim()} type="submit" aria-label="送出問題">
            <img className="size-6 brightness-0 invert" src="/discover/composer-send.svg" alt="" />
          </button>
        </form>
        <p className="mt-1 pl-1 text-[11px] font-medium text-[#177049]">分享前會先保護你的個人資料；對話紀錄不保存原始姓名與照片。</p>
      </div>
    </section>
  );
}
