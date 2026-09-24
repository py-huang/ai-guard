"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { CHILD_LEARNING_PARTNER_PROMPT } from "@/lib/child-llm-prompt";
import { CHILD_BLOCK_REPLY, classifyUnsafeText } from "@/lib/content-safety";
import { inspectSafety, toPiiPreview } from "@/lib/safety-inspect";
import { applyOutboundSocraticHint, stripSocraticInboundPrefix } from "@/lib/socratic";
import { replaceVaultTokensForChild } from "@/lib/vault-tokens";
import type { PiiPreview } from "@/lib/pii-preview";
import { useConversationStore } from "@/store/conversation-store";
import { useWritingStore } from "@/store/writing-store";
import type { GenerateWritingResponse } from "@/lib/writing";
import type { ConversationMessage } from "@/types/conversation";
import { ChatAiAvatar } from "@/components/chat-ai-avatar";
import { MarkdownMessage } from "@/components/markdown-message";
import { ComposerAttach } from "@/components/composer-attach";
import { ProtectedBadge } from "@/components/protected-badge";
import { takePendingUpload } from "@/lib/pending-upload";
import { ImageBlockedCard, ImageParentApprovedCard, ImageParentDeclinedCard, ImageParentPendingCard, ImageReviewCard, ImageSoftScanPreview } from "@/components/pages/image-review-card";
import {
  ParentApprovedCard,
  ParentDeclinedCard,
  ParentPendingCard,
  ParentRevisionCard,
  PiiDetectedCard,
  PiiRewriteCard,
} from "@/components/pages/pii-guard-cards";
import { pngDataUrl, redactImage } from "@/lib/safety-redact";

type GuardState = "none" | "detected" | "rewritten" | "parent-pending" | "parent-approved" | "parent-revision" | "parent-declined" | "image-review" | "image-blocked";

type ChatProps = {
  conversationId?: string;
};

export function Chat({ conversationId }: ChatProps) {
  const router = useRouter();
  const { ready, createConversation, getConversation, appendMessage, renameConversation, removeConversation } = useConversationStore();
  const { addDraft } = useWritingStore();
  const [demoConversationId, setDemoConversationId] = useState(conversationId ?? "");
  const activeConversationId = conversationId || demoConversationId;
  const conversation = activeConversationId ? getConversation(activeConversationId) : undefined;
  const fileRef = useRef<HTMLInputElement>(null);

  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [guard, setGuard] = useState<GuardState>("none");
  const [preview, setPreview] = useState<PiiPreview | null>(null);
  const [rawDraft, setRawDraft] = useState("");
  const [imageScanning, setImageScanning] = useState(false);
  const [llmPrompt, setLlmPrompt] = useState("");
  const [originalImageUrl, setOriginalImageUrl] = useState("");
  const [redactedImageUrl, setRedactedImageUrl] = useState("");
  const [redactedImageBase64, setRedactedImageBase64] = useState("");
  const [imageChanged, setImageChanged] = useState(false);
  const [imageFields, setImageFields] = useState<string[]>([]);
  const [safetyTouched, setSafetyTouched] = useState(false);

  const started = useRef(false);

  function clearImage() {
    if (originalImageUrl) {
      URL.revokeObjectURL(originalImageUrl);
    }
    setOriginalImageUrl("");
    setRedactedImageUrl("");
    setRedactedImageBase64("");
    setImageChanged(false);
    setImageFields([]);
    if (fileRef.current) {
      fileRef.current.value = "";
    }
  }

  useEffect(() => {
    if (!ready || conversationId || started.current || typeof window === "undefined") {
      return;
    }

    started.current = true;
    const created = createConversation("新對話");
    setDemoConversationId(created.id);
  }, [conversationId, createConversation, ready]);

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
    void startGuard(pending);
  }, [conversation?.id, ready]);

  useEffect(() => {
    if (!ready || !conversation) {
      return;
    }
    const pendingFile = takePendingUpload();
    if (pendingFile) {
      void onPickImage(pendingFile);
    }
  }, [conversation?.id, ready]);

  async function sendSafeText(
    text: string,
    options?: { protected?: boolean; hasImage?: boolean; llmText?: string; imageBase64?: string; imagePreview?: string },
  ) {
    if (!conversation) {
      return;
    }

    const promptForModel = options?.llmText?.trim() || llmPrompt.trim() || text;
    const imageBase64 = options?.imageBase64 || redactedImageBase64;
    const visibleText = stripSocraticInboundPrefix(text);
    const userMessage: ConversationMessage = {
      role: "user",
      content: visibleText,
      protected: Boolean(options?.protected || safetyTouched || imageBase64),
      hasImage: options?.hasImage || Boolean(imageBase64),
      imagePreview: options?.imagePreview || (imageBase64 ? pngDataUrl(imageBase64) : undefined),
    };
    appendMessage(conversation.id, userMessage);
    if (conversation.title === "新對話") {
      renameConversation(conversation.id, visibleText.slice(0, 24));
    }
    setDraft("");
    setGuard("none");
    setPreview(null);
    setRawDraft("");
    setLlmPrompt("");
    setSafetyTouched(false);
    clearImage();
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
      history[history.length - 1] = { role: "user", content: promptForModel };

      const response = await fetch("/api/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            {
              role: "system",
              content: CHILD_LEARNING_PARTNER_PROMPT,
            },
            ...history,
          ],
          ...(imageBase64 ? { image: { mimeType: "image/png", data: imageBase64 } } : {}),
        }),
      });
      const data = (await response.json()) as { choices?: { message?: { content?: string } }[]; error?: string };
      const content = data.choices?.[0]?.message?.content?.trim();
      if (!response.ok || !content) {
        throw new Error(data.error || "暫時無法回覆。");
      }
      appendMessage(conversation.id, {
        role: "assistant",
        content: replaceVaultTokensForChild(applyOutboundSocraticHint(content, promptForModel)),
      });
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "暫時無法回覆。");
    } finally {
      setBusy(false);
    }
  }

  async function startGuard(text: string) {
    if (!conversation) {
      return;
    }

    setBusy(true);
    setError("");
    try {
      const result = await inspectSafety(conversation.id, text);
      if (result.blocked) {
        appendMessage(conversation.id, { role: "user", content: result.safeText || "這個問題先不要繼續。" });
        appendMessage(conversation.id, {
          role: "assistant",
          content: result.childMessage || CHILD_BLOCK_REPLY,
          blocked: true,
        });
        setDraft("");
        return;
      }

      if (result.hits.length === 0) {
        const isFirstTextMessage = conversation.messages.length === 0 && !redactedImageBase64;
        if (isFirstTextMessage) {
          let isThemeMode = false;
          try {
            const classifyResponse = await fetch("/api/theme/writing/classify", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ input: result.processedText }),
            });
            const classification = (await classifyResponse.json()) as { isThemeMode?: boolean };

            isThemeMode = classifyResponse.ok && classification.isThemeMode === true;
          } catch (classificationError) {
            console.error("Writing intent classification failed", classificationError);
          }

          if (isThemeMode) {
            try {
              const writingResponse = await fetch("/api/theme/writing/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ input: result.processedText }),
              });
              const writingDraft = (await writingResponse.json()) as GenerateWritingResponse | { error?: string };

              if (!writingResponse.ok || !("theme_id" in writingDraft)) {
                throw new Error("error" in writingDraft ? writingDraft.error : "暫時無法開始寫作。 ");
              }

              addDraft(writingDraft, text);
              removeConversation(conversation.id);
              router.push(`/theme/writing/${writingDraft.theme_id}`);
              return;
            } catch (writingError) {
              setError(writingError instanceof Error ? writingError.message : "暫時無法開始寫作。 ");
              return;
            }
          }
        }

        await sendSafeText(text, {
          hasImage: Boolean(redactedImageBase64),
          llmText: result.processedText,
          imageBase64: redactedImageBase64 || undefined,
        });
        return;
      }

      setRawDraft(text);
      setPreview(toPiiPreview(text, result));
      setLlmPrompt(result.processedText);
      setSafetyTouched(true);
      setGuard("detected");
    } catch (inspectError) {
      setError(inspectError instanceof Error ? inspectError.message : "現在沒辦法檢查這句話。");
    } finally {
      setBusy(false);
    }
  }

  function submitComposer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy || !conversation) {
      return;
    }
    void startGuard(text);
  }

  async function onPickImage(file: File | undefined) {
    if (!file || !conversation) {
      return;
    }

    if (originalImageUrl) {
      URL.revokeObjectURL(originalImageUrl);
    }

    const previewUrl = URL.createObjectURL(file);
    setOriginalImageUrl(previewUrl);
    setSafetyTouched(true);
    setImageScanning(true);
    setError("");
    const startedAt = Date.now();
    try {
      const result = await redactImage(conversation.id, file);
      const remaining = Math.max(0, 5000 - (Date.now() - startedAt));
      if (remaining > 0) {
        await new Promise((resolve) => window.setTimeout(resolve, remaining));
      }
      if (result.blocked) {
        URL.revokeObjectURL(previewUrl);
        setOriginalImageUrl("");
        setRedactedImageUrl("");
        setRedactedImageBase64("");
        setImageChanged(false);
        setImageFields(result.fields);
        setGuard("image-blocked");
        return;
      }
      setRedactedImageBase64(result.redactedPngBase64);
      setRedactedImageUrl(pngDataUrl(result.redactedPngBase64));
      setImageChanged(result.changed);
      setImageFields(result.fields);
      setGuard("image-review");
    } catch (redactError) {
      URL.revokeObjectURL(previewUrl);
      setOriginalImageUrl("");
      setError(redactError instanceof Error ? redactError.message : "現在沒辦法檢查這張圖片。");
    } finally {
      setImageScanning(false);
    }
  }

  if (!ready || !conversation) {
    return <p className="px-8 py-10 text-[#8a968f]">正在開始新對話…</p>;
  }

  const composerLocked = guard === "detected" || guard === "rewritten" || guard === "parent-pending" || guard === "parent-revision" || guard === "parent-declined" || guard === "image-review" || guard === "image-blocked";

  return (
    <section className="flex min-h-[calc(100dvh-72px)] flex-col px-5 py-6 sm:px-10 lg:px-16">
      <div className="mx-auto flex w-full max-w-[860px] flex-1 flex-col">
        {conversation.messages.length === 0 && guard === "none" && !imageScanning ? (
          <div className="pt-6">
            <h1 className="text-[28px] font-bold">想問什麼都可以先打字</h1>
            <p className="mt-2 text-[16px] font-normal leading-[26px] text-[#506058]">送出前會先檢查個人資料。紀錄裡只會留下安全版本。</p>
          </div>
        ) : null}

        {guard === "parent-pending" ? <h1 className="pt-2 text-xl font-bold leading-[30px] text-[#13221b]">已經問家長囉</h1> : null}
        {guard === "rewritten" ? <h1 className="pt-2 text-xl font-bold leading-[30px] text-[#13221b]">安全版本已準備好</h1> : null}

        <div className={`mt-6 flex-1 space-y-5 ${guard === "image-review" || guard === "image-blocked" ? "pb-44" : "pb-28"}`}>
          {conversation.messages.map((message, index) =>
            message.role === "user" ? (
              <div className="ml-auto max-w-[520px] rounded-[24px] bg-[#eee6ff] px-5 py-4" key={`${message.content}-${index}`}>
                {message.protected ? (
                  <div className="mb-2">
                    <ProtectedBadge />
                  </div>
                ) : null}
                {message.imagePreview ? (
                  <img alt="" className="mb-3 max-h-40 w-full rounded-[16px] object-contain" src={message.imagePreview} />
                ) : message.hasImage ? (
                  <p className="mb-2 rounded-[16px] bg-white/70 px-3 py-2 text-sm text-[#177049]">已用安全圖片（紀錄不保存原圖）</p>
                ) : null}
                <p className="text-[17px] leading-8">{stripSocraticInboundPrefix(message.content)}</p>
              </div>
            ) : (
              <div className="flex max-w-[640px] gap-3" key={`${message.content}-${index}`}>
                <ChatAiAvatar />
                <div>
                  {message.blocked ? (
                    <p className="text-[17px] leading-8">{replaceVaultTokensForChild(stripSocraticInboundPrefix(message.content))}</p>
                  ) : (
                    <MarkdownMessage>{replaceVaultTokensForChild(stripSocraticInboundPrefix(message.content))}</MarkdownMessage>
                  )}
                  {message.blocked ? <p className="mt-2 text-sm text-[#c02d32]">這個問題沒有送給 AI。</p> : null}
                </div>
              </div>
            )
          )}

          {imageScanning ? <ImageSoftScanPreview /> : null}

          {guard === "image-blocked" ? (
            <ImageBlockedCard
              onReplace={() => {
                clearImage();
                setGuard("none");
                fileRef.current?.click();
              }}
            />
          ) : null}

          {guard === "image-review" && originalImageUrl && redactedImageUrl ? (
            <ImageReviewCard
              originalUrl={originalImageUrl}
              redactedUrl={redactedImageUrl}
              changed={imageChanged}
              fields={imageFields}
              onUseSafe={() => {
                const text = draft.trim() || "請看這張已遮罩的圖片，幫我看看可以怎麼問。";
                void sendSafeText(text, { protected: true, hasImage: true, imageBase64: redactedImageBase64 });
              }}
              onAskParent={() => setGuard("parent-pending")}
              onReplace={() => {
                clearImage();
                setGuard("none");
                fileRef.current?.click();
              }}
            />
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

          {guard === "parent-pending" && redactedImageUrl ? (
            <ImageParentPendingCard
              fields={imageFields}
              onUseSafe={() => {
                const text = draft.trim() || "請看這張已遮罩的圖片，幫我看看可以怎麼問。";
                void sendSafeText(text, { protected: true, hasImage: true, imageBase64: redactedImageBase64 });
              }}
              onReplace={() => {
                clearImage();
                setGuard("none");
                fileRef.current?.click();
              }}
              onAskElse={() => {
                setDraft("");
                setGuard("none");
                setPreview(null);
                setSafetyTouched(false);
                clearImage();
              }}
              onDemoApprove={() => setGuard("parent-approved")}
              onDemoDecline={() => setGuard("parent-declined")}
            />
          ) : null}

          {guard === "parent-pending" && preview && !redactedImageUrl ? (
            <ParentPendingCard
              safeText={preview.safeText}
              onUseSafe={() => setGuard("rewritten")}
              onEdit={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
              onAskElse={() => {
                setDraft("");
                setGuard("none");
                setPreview(null);
                setSafetyTouched(false);
              }}
              onDemoApprove={() => setGuard("parent-approved")}
              onDemoRevise={() => setGuard("parent-revision")}
              onDemoDecline={() => setGuard("parent-declined")}
            />
          ) : null}

          {guard === "parent-approved" && redactedImageUrl ? (
            <ImageParentApprovedCard
              fields={imageFields}
              question={draft.trim() || undefined}
              onContinue={() => {
                const text = draft.trim() || "請看這張已遮罩的圖片，幫我看看可以怎麼問。";
                void sendSafeText(text, { protected: true, hasImage: true, imageBase64: redactedImageBase64 });
              }}
            />
          ) : null}

          {guard === "parent-approved" && preview && !redactedImageUrl ? (
            <ParentApprovedCard
              safeText={preview.safeText}
              onContinue={() => void sendSafeText(preview.safeText, { protected: true })}
              onEdit={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
              onAskElse={() => {
                setDraft("");
                setGuard("none");
                setPreview(null);
                setSafetyTouched(false);
              }}
            />
          ) : null}

          {guard === "parent-revision" && preview && !redactedImageUrl ? (
            <ParentRevisionCard
              safeText={preview.safeText}
              onEdit={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
              onUseSafe={() => setGuard("rewritten")}
            />
          ) : null}

          {guard === "parent-declined" && preview && !redactedImageUrl ? (
            <ParentDeclinedCard
              safeText={preview.safeText}
              onEdit={() => {
                setDraft(rawDraft);
                setGuard("none");
              }}
              onAskElse={() => {
                setDraft("");
                setGuard("none");
                setPreview(null);
                setSafetyTouched(false);
              }}
            />
          ) : null}

          {guard === "parent-declined" && redactedImageUrl ? (
            <ImageParentDeclinedCard
              question={draft.trim() || undefined}
              onReplace={() => {
                clearImage();
                setGuard("none");
                fileRef.current?.click();
              }}
              onUseText={() => {
                clearImage();
                setGuard("none");
              }}
            />
          ) : null}

          {busy ? <p className="whitespace-nowrap text-[#8a968f]">AI 正在想…</p> : null}
          {error ? <p className="text-[#c02d32]">{error}</p> : null}
        </div>

        {guard === "parent-pending" ? (
          <p className="mt-8 text-xs font-medium leading-[19px] text-[#c02d32]">等待中的原問題不會送出；你仍可繼續探索其他內容。</p>
        ) : (
          <>
            <form className="sticky bottom-4 mt-8 flex h-[66px] items-center gap-2 rounded-full border border-[#dde3df] bg-white py-[9px] pl-2 pr-[10px]" onSubmit={submitComposer}>
              <input
                ref={fileRef}
                className="hidden"
                type="file"
                accept="image/*"
                onChange={(event) => onPickImage(event.target.files?.[0])}
              />
              <ComposerAttach
                disabled={composerLocked || busy}
                onPickFile={(file) => void onPickImage(file)}
                onUnsupported={setError}
              />
              <input
                className="min-w-0 flex-1 bg-transparent text-[18px] outline-none placeholder:text-[#8a968f]"
                value={draft}
                disabled={composerLocked || busy}
                onChange={(event) => setDraft(event.target.value)}
                placeholder={
                  imageScanning || guard === "image-review" || guard === "parent-approved"
                    ? "圖片已加入，送出前我會先幫你檢查"
                    : guard === "image-blocked"
                      ? "這張圖片沒有送出，可以換一張再問"
                      : guard === "parent-revision"
                        ? "這裡有你的名字和學校，先不要送出"
                      : guard === "parent-declined"
                        ? "還不能送出，先完成上一步"
                    : composerLocked
                      ? "這裡有你的名字和學校，先不要送出"
                      : "想知道什麼？可以打字或用說的"
                }
                autoComplete="off"
              />
              <button className="grid size-12 place-items-center rounded-full bg-[#d63a37] text-white disabled:bg-[#d7ddd9]" disabled={composerLocked || busy || !draft.trim()} type="submit" aria-label="送出問題">
                <img className="size-6 brightness-0 invert" src="/discover/composer-send.svg" alt="" />
              </button>
            </form>
            <p className="mt-1 pl-1 text-[11px] font-medium text-[#177049]">分享前會先保護你的個人資料；對話紀錄不保存原始姓名與照片。</p>
          </>
        )}
      </div>
    </section>
  );
}
