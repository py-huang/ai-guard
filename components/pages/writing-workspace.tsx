"use client";

import { type FormEvent, useState } from "react";
import Link from "next/link";
import { ArrowRight, Send } from "lucide-react";

import { MarkdownMessage } from "@/components/markdown-message";
import { useWritingStore } from "@/store/writing-store";
import { getWritingSystemPrompt } from "../../lib/writing-prompts";
import type { WritingMessage } from "@/lib/writing";

type WritingWorkspaceProps = {
  themeId: string;
};

export function WritingWorkspace({ themeId }: WritingWorkspaceProps) {
  const { drafts, appendMessage, summarizeStage, advanceStage } = useWritingStore();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const draft = drafts.find((item) => item.id === themeId);

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
  const isLastStage = stageIndex === activeDraft.steps.length - 1;
  const pendingOutlineLabels = ["等待選擇主題", "等待地點", "等待畫面", "等待感受", "等待結尾"];

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = message.trim();

    if (!content || isSending) {
      return;
    }

    const userMessage: WritingMessage = { role: "user", content, stageIndex };
    const requestMessages = [...stageMessages, userMessage];
    appendMessage(activeDraft.id, userMessage);
    setMessage("");
    setError("");
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

  async function continueToNextStage() {
    const hasUserMessage = stageMessages.some((item) => item.role === "user" && item.content.trim());
    if (!hasUserMessage || isSummarizing) {
      setError("先寫下一句自己的想法，再繼續下一步。 ");
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

      summarizeStage(activeDraft.id, stageIndex, data.content);
      if (!isLastStage) {
        appendMessage(activeDraft.id, {
          role: "assistant",
          content: `下一步是「${activeDraft.steps[stageIndex + 1]}」。你想先說什麼？`,
          stageIndex: stageIndex + 1,
        });
        advanceStage(activeDraft.id);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "暫時無法整理這一步。 ");
    } finally {
      setIsSummarizing(false);
    }
  }

  return (
    <section className="px-5 py-8 sm:px-8 lg:px-12 xl:pl-[120px] xl:pt-9">
      <h1 className="text-[22px] leading-8 font-bold">第 {stageIndex + 1} 步：{activeDraft.steps[stageIndex]}</h1>
      <p className="mt-2 inline-flex h-8 items-center rounded-2xl bg-[#ffe7d7] px-3 text-xs font-medium text-[#a35a2d]">✎ 寫作靈感</p>

      <div className="mt-6 grid max-w-[920px] gap-6 lg:grid-cols-[620px_274px]">
        <div className="flex min-h-[626px] flex-col rounded-[22px] border border-[#dde3df] bg-white p-[19px]">
          <div className="space-y-4">
            {stageMessages.map((item, index) => (
              <div className={item.role === "user" ? "ml-auto w-full max-w-[260px] rounded-2xl bg-[#eae1ff] px-[14px] py-2.5" : "w-full max-w-[500px] rounded-2xl bg-[#ecf9f3] px-[14px] py-2.5"} key={`${item.role}-${index}-${item.content}`}>
                <p className={item.role === "user" ? "text-[11px] leading-[17px] font-bold text-[#6650a4]" : "text-[11px] leading-[17px] font-bold text-[#177049]"}>{item.role === "user" ? "小宇" : "AI"}</p>
                {item.role === "assistant" ? (
                  <MarkdownMessage compact>{item.content}</MarkdownMessage>
                ) : (
                  <p className="text-sm leading-6">{item.content}</p>
                )}
              </div>
            ))}
          </div>

          <form className="mt-auto pt-6" onSubmit={submitMessage}>
            <label className="sr-only" htmlFor="writing-message">寫下你的想法</label>
            <div className="flex h-16 items-center gap-2 rounded-[20px] border border-[#dde3df] py-2 pl-[18px] pr-4">
              <input id="writing-message" className="min-w-0 flex-1 text-[18px] outline-none placeholder:text-[#8a968f]" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="例如：日本、花蓮或阿嬤家…" disabled={isSending || isSummarizing} />
              <button aria-label="送出想法" className="grid size-12 shrink-0 place-items-center rounded-full bg-[#d63a37] text-white hover:bg-[#bd2e2c] disabled:opacity-50" disabled={!message.trim() || isSending || isSummarizing} title="送出想法" type="submit">
                <Send size={20} aria-hidden="true" />
              </button>
            </div>
          </form>
          {error ? <p className="mt-2 text-sm text-[#c02d32]">{error}</p> : null}
        </div>

        <aside className="min-h-[626px] rounded-[22px] bg-[#fff8d9] p-5">
          <p className="inline-flex h-8 items-center rounded-2xl bg-white px-3 text-xs font-medium text-[#8a6400]">你的作文大綱</p>
          <h2 className="mt-3 text-[22px] leading-8 font-bold">正在收集想法</h2>
          <ol className="mt-5 space-y-5">
            {activeDraft.outline.map((item, index) => (
              <li className="grid grid-cols-[28px_1fr] gap-3" key={item.stage}>
                <p className="pt-0.5 text-[11px] leading-[18px] font-bold text-[#a35a2d]">{String(index + 1).padStart(2, "0")}</p>
                <div>
                  <p className="text-sm leading-[22px] font-bold">{item.stage}</p>
                  <p className="mt-1 text-xs leading-[19px] text-[#506058]">{item.content || pendingOutlineLabels[index]}</p>
                </div>
              </li>
            ))}
          </ol>
          <button className="mt-6 inline-flex h-12 items-center justify-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] font-medium text-white hover:bg-[#bd2e2c] disabled:opacity-50" disabled={isSummarizing || Boolean(stage.content && isLastStage)} onClick={() => void continueToNextStage()} type="button">
            {isSummarizing ? "整理中" : isLastStage && stage.content ? "完成了" : "繼續下一步"}
            {!isLastStage || !stage.content ? <ArrowRight size={20} aria-hidden="true" /> : null}
          </button>
        </aside>
      </div>
      <p className="mt-5 max-w-[700px] text-xs leading-[19px] font-medium text-[#177049]">AI 用提問幫你整理想法，不會直接代寫整篇作文。</p>
    </section>
  );
}