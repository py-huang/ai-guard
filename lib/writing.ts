import "server-only";

import { generateGeminiText } from "@/lib/gemini";
import { getWritingSystemPrompt } from "./writing-prompts";

export type WritingMessageRole = "assistant" | "user";

export type WritingMessage = {
  role: WritingMessageRole;
  content: string;
  stageIndex: number;
};

export type WritingOutlineItem = {
  stage: string;
  content: string;
  summarizedUserMessageCount?: number;
};

export type WritingDraft = {
  id: string;
  subject: string;
  updatedAt: number;
  steps: string[];
  outline: WritingOutlineItem[];
  chat_history: WritingMessage[];
  currentStageIndex: number;
};

export type GenerateWritingResponse = {
  steps: string[];
  outline: WritingOutlineItem[];
  theme: "writing";
  theme_id: string;
  init_question: string;
};

export type WritingIntent = {
  isThemeMode: boolean;
};

export async function classifyWritingIntent(input: string): Promise<WritingIntent> {
  const text = await generateGeminiText({
    messages: [
      { role: "system", content: getWritingSystemPrompt("classify") },
      { role: "user", content: input },
    ],
    responseMimeType: "application/json",
    temperature: 0,
  });
  const result = JSON.parse(text) as Partial<WritingIntent>;

  if (typeof result.isThemeMode !== "boolean") {
    throw new Error("Gemini returned an invalid writing intent.");
  }

  return { isThemeMode: result.isThemeMode };
}

export async function generateWritingPlan(subject: string) {
  const text = await generateGeminiText({
    messages: [
      { role: "system", content: getWritingSystemPrompt("chat") },
      { role: "user", content: `為題目「${subject}」建立引導寫作計畫。只回傳 JSON：{"steps":[string,string,string,string,string],"outline":[{"stage":string,"content":""},{"stage":string,"content":""},{"stage":string,"content":""},{"stage":string,"content":""},{"stage":string,"content":""}],"init_question":string}。請依題目為五個 stage 取具體、簡短且彼此不同的名稱；五步依序引導孩子決定寫作焦點、交代情境、描述事件或畫面、說出感受或想法、完成結尾。不要直接使用「主題、地點、細節、想法、結尾」當作 stage 名稱；init_question 只能問一個問題。` },
    ],
    responseMimeType: "application/json",
  });
  const result = JSON.parse(text) as Partial<Pick<GenerateWritingResponse, "steps" | "outline" | "init_question">>;

  if (!Array.isArray(result.steps) || result.steps.length !== 5 || !result.steps.every((step) => typeof step === "string") || !Array.isArray(result.outline) || result.outline.length !== 5 || !result.outline.every((item) => typeof item?.stage === "string") || typeof result.init_question !== "string") {
    throw new Error("Gemini returned an invalid writing plan.");
  }

  return { steps: result.steps, outline: result.outline.map((item) => ({ stage: item.stage, content: "" })), init_question: result.init_question };
}

export async function summarizeWritingStage(stage: string, messages: WritingMessage[]) {
  return generateGeminiText({
    messages: [
      { role: "system", content: getWritingSystemPrompt("summarize") },
      ...messages.map((message) => ({ role: message.role, content: message.content })),
      { role: "user", content: `目前階段：${stage}。只輸出摘要內容，不要加標題、引號或說明。` },
    ],
  });
}