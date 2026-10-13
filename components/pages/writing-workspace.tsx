"use client";

import { type FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, LoaderCircle, Send } from "lucide-react";

import { ComposerAttach } from "@/components/composer-attach";
import { MarkdownMessage } from "@/components/markdown-message";
import { VoiceAsk } from "@/components/pages/voice-ask";
import { ImageBlockedCard, ImageParentApprovedCard, ImageParentDeclinedCard, ImageParentPendingCard, ImageReviewCard, ImageSoftScanPreview } from "@/components/pages/image-review-card";
import { SpeakButton } from "@/components/speak-button";
import { pngDataUrl, redactImage } from "@/lib/safety-redact";
import { useWritingStore } from "@/store/writing-store";
import { getWritingSystemPrompt } from "../../lib/writing-prompts";
import type { WritingMessage } from "@/lib/writing";

type ImageStatus = "none" | "scanning" | "review" | "blocked" | "parent-pending" | "parent-approved" | "parent-declined";

type WritingWorkspaceProps = {
  themeId: string;
};

export function WritingWorkspace({ themeId }: WritingWorkspaceProps) {
  const { ready, drafts, appendMessage, summarizeStage, selectStage, advanceStage } = useWritingStore();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [imageStatus, setImageStatus] = useState<ImageStatus>("none");
  const [originalImageUrl, setOriginalImageUrl] = useState("");
  const [redactedImageUrl, setRedactedImageUrl] = useState("");
  const [redactedImageBase64, setRedactedImageBase64] = useState("");
  const [imageChanged, setImageChanged] = useState(false);
  const [imageFields, setImageFields] = useState<string[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);
  const imageUrlRef = useRef("");
  const draft = drafts.find((item) => item.id === themeId);

  useEffect(() => () => {
    if (imageUrlRef.current) {
      URL.revokeObjectURL(imageUrlRef.current);
    }
  }, []);

  if (!ready) {
    return <p className="px-5 py-12 text-[#8a968f] sm:px-8 lg:px-12">載入寫作筆記中…</p>;
  }

  if (!draft) {
    return (
      <section className="px-5 py-12 sm:px-8 lg:px-12">
        <div className="max-w-xl rounded-[22px] bg-[#fff0ee] p-6">
          <h1 className="text-2xl font-bold">這份寫作筆記不在這裡</h1>
          <p className="mt-2 leading-7 text-[#506058]">重新選一個題目，我們會一步一步陪你寫。</p>
          <Link className="mt-5 inline-flex h-11 items-center rounded-xl bg-[#d63a37] px-4 font-medium text-white hover:bg-[#bd2e2c]" href="/theme">回到探索主題</Link>
        </div>
      </section>
    );
  }

  const activeDraft = draft;
  const stageIndex = activeDraft.currentStageIndex;
  const stage = activeDraft.outline[stageIndex];
  const stageMessages = activeDraft.chat_history.filter((item) => item.stageIndex === stageIndex);
  const userMessageCount = stageMessages.filter((item) => item.role === "user" && item.content.trim()).length;
  const baselineUserMessageCount = stage.summarizedUserMessageCount ?? 0;
  const canUpdateOutline = userMessageCount > baselineUserMessageCount;
  const isLastStage = stageIndex === activeDraft.steps.length - 1;
  const pendingOutlineLabel = "等待中";

  function clearAttachedImage() {
    if (imageUrlRef.current) {
      URL.revokeObjectURL(imageUrlRef.current);
      imageUrlRef.current = "";
    }
    setOriginalImageUrl("");
    setRedactedImageUrl("");
    setRedactedImageBase64("");
    setImageChanged(false);
    setImageFields([]);
    setImageStatus("none");
    if (fileRef.current) {
      fileRef.current.value = "";
    }
  }

  function replaceImage() {
    clearAttachedImage();
    fileRef.current?.click();
  }

  async function onPickImage(file: File | undefined) {
    if (!file) {
      return;
    }

    clearAttachedImage();
    const previewUrl = URL.createObjectURL(file);
    imageUrlRef.current = previewUrl;
    setOriginalImageUrl(previewUrl);
    setImageStatus("scanning");
    setError("");

    try {
      const result = await redactImage(activeDraft.id, file);
      if (result.blocked) {
        URL.revokeObjectURL(previewUrl);
        imageUrlRef.current = "";
        setOriginalImageUrl("");
        setImageFields(result.fields);
        setImageStatus("blocked");
        return;
      }

      setRedactedImageBase64(result.redactedPngBase64);
      setRedactedImageUrl(pngDataUrl(result.redactedPngBase64));
      setImageChanged(result.changed);
      setImageFields(result.fields);
      setImageStatus("review");
    } catch (imageError) {
      URL.revokeObjectURL(previewUrl);
      imageUrlRef.current = "";
      setOriginalImageUrl("");
      setError(imageError instanceof Error ? imageError.message : "現在沒辦法檢查這張圖片。");
      setImageStatus("none");
    }
  }

  async function sendMessage(content: string, imageBase64?: string) {
    const trimmedContent = content.trim();
    if (!trimmedContent || isSending || isSummarizing) {
      return;
    }

    const userMessage: WritingMessage = { role: "user", content: trimmedContent, stageIndex };
    const requestMessages = [...stageMessages, userMessage];
    appendMessage(activeDraft.id, userMessage);
    setMessage("");
    setError("");
    if (imageBase64) {
      clearAttachedImage();
    }
    setIsSending(true);

    try {
      const response = await fetch("/api/chat/completions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            { role: "system", content: `${getWritingSystemPrompt("chat")}\n目前寫作階段：${stage.stage}\n請直接回覆孩子下一句引導問題，不要加上角色名稱。` },
            ...requestMessages.map(({ role, content: messageContent }) => ({ role, content: messageContent })),
          ],
          ...(imageBase64 ? { image: { mimeType: "image/png", data: imageBase64 } } : {}),
        }),
      });
      const data = (await response.json()) as { choices?: Array<{ message?: { content?: string } }>; error?: string };
      const assistantContent = data.choices?.[0]?.message?.content;

      if (!response.ok || !assistantContent) {
        throw new Error(data.error ?? "暫時無法回覆。 ");
      }

      appendMessage(activeDraft.id, { role: "assistant", content: assistantContent, stageIndex });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "暫時無法回覆。 ");
    } finally {
      setIsSending(false);
    }
  }

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(message);
  }

  function sendReviewedImage() {
    const content = message.trim() || `請根據這張已遮罩的圖片，問我一個能幫助我完成「${stage.stage}」的問題。`;
    void sendMessage(content, redactedImageBase64);
  }

  async function continueToNextStage() {
    if (!canUpdateOutline || isSummarizing) {
      setError(stage.content ? "先補充新的想法，再更新大綱。 " : "先寫下一句自己的想法，再更新大綱。 ");
      return;
    }

    setError("");
    setIsSummarizing(true);

    try {
      const response = await fetch("/api/theme/writing/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stage: stage.stage, messages: stageMessages }),
      });
      const data = (await response.json()) as { content?: string; error?: string };

      if (!response.ok || !data.content) {
        throw new Error(data.error ?? "暫時無法整理這一步。 ");
      }

      summarizeStage(activeDraft.id, stageIndex, data.content, userMessageCount);
      if (!isLastStage) {
        const nextStageIndex = stageIndex + 1;
        const nextStageHasMessages = activeDraft.chat_history.some((item) => item.stageIndex === nextStageIndex);
        if (!nextStageHasMessages) {
          appendMessage(activeDraft.id, {
            role: "assistant",
            content: `下一步是「${activeDraft.steps[nextStageIndex]}」。你想先說什麼？`,
            stageIndex: nextStageIndex,
          });
        }
        advanceStage(activeDraft.id);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "暫時無法整理這一步。 ");
    } finally {
      setIsSummarizing(false);
    }
  }

  const composerLocked = imageStatus !== "none";

  if (voiceOpen) {
    return (
      <VoiceAsk
        onConfirm={(text) => {
          setVoiceOpen(false);
          void sendMessage(text);
        }}
        onUseText={() => setVoiceOpen(false)}
      />
    );
  }

  return (
    <section className="px-3 py-8 sm:px-8 lg:px-12 xl:pl-[120px] xl:pt-9">
      <h1 className="text-[22px] leading-8 font-bold">第 {stageIndex + 1} 步：{activeDraft.steps[stageIndex]}</h1>
      <p className="mt-2 inline-flex h-8 items-center rounded-2xl bg-[#ffe7d7] px-3 text-xs font-medium text-[#a35a2d]">✎ 寫作靈感</p>

      <nav aria-label="寫作步驟" className="mt-5 flex max-w-[920px] flex-wrap gap-2">
        {activeDraft.steps.map((step, index) => (
          <button
            aria-current={stageIndex === index ? "step" : undefined}
            className={stageIndex === index ? "h-9 rounded-full bg-[#177049] px-3 text-sm font-medium text-white" : "h-9 rounded-full border border-[#dde3df] bg-white px-3 text-sm font-medium text-[#506058] hover:border-[#a8cfb7]"}
            key={step}
            onClick={() => {
              setError("");
              selectStage(activeDraft.id, index);
            }}
            type="button"
          >
            第 {index + 1} 步
          </button>
        ))}
      </nav>

      <div className="mt-6 grid w-full min-w-0 max-w-[920px] gap-6 lg:grid-cols-[620px_274px]">
        <div className="flex min-w-0 h-[626px] flex-col rounded-[22px] border border-[#dde3df] bg-white p-3 sm:p-[19px]">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto">
            {stageMessages.map((item, index) => (
              <div className={item.role === "user" ? "ml-auto w-full max-w-[260px] rounded-2xl bg-[#eae1ff] px-[14px] py-2.5" : "w-full max-w-[500px] rounded-2xl bg-[#ecf9f3] px-[14px] py-2.5"} key={`${item.role}-${index}-${item.content}`}>
                <p className={item.role === "user" ? "text-[11px] leading-[17px] font-bold text-[#6650a4]" : "text-[11px] leading-[17px] font-bold text-[#177049]"}>{item.role === "user" ? "小宇" : "AI"}</p>
                {item.role === "assistant" ? (
                  <>
                    <MarkdownMessage compact>{item.content}</MarkdownMessage>
                    <SpeakButton text={item.content} />
                  </>
                ) : (
                  <p className="text-sm leading-6">{item.content}</p>
                )}
              </div>
            ))}
            {isSending ? (
              <div className="w-full max-w-[500px] rounded-2xl bg-[#ecf9f3] px-[14px] py-2.5">
                <p className="text-[11px] leading-[17px] font-bold text-[#177049]">AI</p>
                <div className="mt-1 flex items-center gap-2 text-sm text-[#177049]">
                  <span>思考中</span>
                  <LoaderCircle className="animate-spin" size={20} aria-label="AI 正在回覆" />
                </div>
              </div>
            ) : null}
            {imageStatus === "scanning" ? <ImageSoftScanPreview /> : null}
            {imageStatus === "blocked" ? <ImageBlockedCard onReplace={replaceImage} /> : null}
            {imageStatus === "review" && originalImageUrl && redactedImageUrl ? (
              <ImageReviewCard
                originalUrl={originalImageUrl}
                redactedUrl={redactedImageUrl}
                changed={imageChanged}
                fields={imageFields}
                onUseSafe={sendReviewedImage}
                onAskParent={() => setImageStatus("parent-pending")}
                onReplace={replaceImage}
              />
            ) : null}
            {imageStatus === "parent-pending" ? (
              <ImageParentPendingCard
                fields={imageFields}
                onUseSafe={sendReviewedImage}
                onReplace={replaceImage}
                onAskElse={() => {
                  clearAttachedImage();
                  setMessage("");
                }}
                onDemoApprove={() => setImageStatus("parent-approved")}
                onDemoDecline={() => setImageStatus("parent-declined")}
              />
            ) : null}
            {imageStatus === "parent-approved" ? (
              <ImageParentApprovedCard fields={imageFields} question={message.trim() || undefined} onContinue={sendReviewedImage} />
            ) : null}
            {imageStatus === "parent-declined" ? (
              <ImageParentDeclinedCard
                question={message.trim() || undefined}
                onReplace={replaceImage}
                onUseText={() => clearAttachedImage()}
              />
            ) : null}
          </div>

          <form className="mt-auto w-full min-w-0 pt-6" onSubmit={submitMessage}>
            <label className="sr-only" htmlFor="writing-message">寫下你的想法</label>
            <div className="flex h-16 items-center gap-1 rounded-full border border-[#dde3df] bg-white py-2 pl-1 pr-1 sm:gap-2 sm:pl-2 sm:pr-[10px]">
              <input ref={fileRef} accept="image/*" className="hidden" type="file" onChange={(event) => void onPickImage(event.target.files?.[0])} />
              <div className="shrink-0">
                <ComposerAttach disabled={composerLocked || isSending || isSummarizing} onPickFile={(file) => void onPickImage(file)} onUnsupported={setError} />
              </div>
              <input id="writing-message" className="min-w-0 flex-1 bg-transparent text-[18px] outline-none placeholder:text-[#8a968f]" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="例如：日本、花蓮或阿嬤家…" autoComplete="off" disabled={composerLocked || isSending || isSummarizing} />
              <button aria-label="用聲音輸入" className="grid size-12 shrink-0 place-items-center rounded-full text-[#c02d32] hover:bg-[#fff0ee] disabled:opacity-40" disabled={composerLocked || isSending || isSummarizing} onClick={() => setVoiceOpen(true)} title="用聲音輸入" type="button">
                <img alt="" aria-hidden="true" className="size-6" src="/discover/composer-microphone.svg" />
              </button>
              <button aria-label="送出想法" className="grid size-12 shrink-0 place-items-center rounded-full bg-[#d63a37] text-white hover:bg-[#bd2e2c] disabled:opacity-50" disabled={!message.trim() || composerLocked || isSending || isSummarizing} title="送出想法" type="submit">
                <Send size={20} aria-hidden="true" />
              </button>
            </div>
          </form>
          {error ? <p className="mt-2 text-sm text-[#c02d32]">{error}</p> : null}
        </div>

        <aside className="h-[626px] overflow-y-auto rounded-[22px] bg-[#fff8d9] p-5">
          <p className="inline-flex h-8 items-center rounded-2xl bg-white px-3 text-xs font-medium text-[#8a6400]">你的作文大綱</p>
          <h2 className="mt-3 text-[22px] leading-8 font-bold">正在收集想法</h2>
          <ol className="mt-5 space-y-5">
            {activeDraft.outline.map((item, index) => (
              <li className="grid grid-cols-[28px_1fr] gap-3" key={item.stage}>
                <p className="pt-0.5 text-[11px] leading-[18px] font-bold text-[#a35a2d]">{String(index + 1).padStart(2, "0")}</p>
                <div>
                  <p className="text-sm leading-[22px] font-bold">{item.stage}</p>
                  <p className="mt-1 text-xs leading-[19px] text-[#506058]">{item.content || pendingOutlineLabel}</p>
                </div>
              </li>
            ))}
          </ol>
          <button className="mt-6 inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium text-white hover:bg-[#bd2e2c] disabled:opacity-50" disabled={isSummarizing || !canUpdateOutline} onClick={() => void continueToNextStage()} type="button">
            {isSummarizing ? "整理中" : "更新大綱"}
            {isSummarizing ? <LoaderCircle className="animate-spin" size={20} aria-hidden="true" /> : !isLastStage || !stage.content ? <ArrowRight size={20} aria-hidden="true" /> : null}
          </button>
        </aside>
      </div>
      <p className="mt-5 max-w-[700px] text-xs leading-[19px] font-medium text-[#177049]">AI 用提問幫你整理想法，不會直接代寫整篇作文。</p>
    </section>
  );
}