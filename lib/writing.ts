export type WritingMessageRole = "assistant" | "user";

export type WritingMessage = {
  role: WritingMessageRole;
  content: string;
  stageIndex: number;
};

export type WritingOutlineItem = {
  stage: string;
  content: string;
};

export type WritingDraft = {
  id: string;
  subject: string;
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

export function getWritingSystemPrompt(mode: "chat" | "summarize") {
  if (mode === "summarize") {
    return "你是低年級孩子的寫作小幫手。根據本階段對話，用繁體中文寫出一句具體、精簡的作文重點。";
  }

  return "你是低年級孩子的寫作小幫手。一次只問一個簡單問題，用繁體中文鼓勵孩子說出自己的經驗，不代寫整篇作文。";
}

export function getMockWritingPlan(subject: string) {
  return {
    steps: [`選一件${subject}`, "說出地點", "補充細節", "分享想法", "寫下結尾"],
    outline: ["開頭", "經過", "細節", "想法", "結尾"].map((stage) => ({ stage, content: "" })),
  };
}

export function getMockAssistantReply(userMessage: string, stage: string) {
  const trimmedMessage = userMessage.trim();
  return `你說「${trimmedMessage}」很棒！關於「${stage}」，還想補充一個小細節嗎？`;
}

export function getMockStageSummary(messages: WritingMessage[]) {
  const userMessages = messages.filter((message) => message.role === "user" && message.content.trim());
  const latestMessage = userMessages.at(-1)?.content.trim();
  return latestMessage ? latestMessage.slice(0, 60) : "還沒有寫下這一段的內容。";
}