import { getMockStageSummary, getWritingSystemPrompt, type WritingMessage } from "@/lib/writing";

type SummarizeRequest = {
  stage?: unknown;
  messages?: unknown;
};

function isWritingMessage(value: unknown): value is WritingMessage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const message = value as Partial<WritingMessage>;
  return (message.role === "assistant" || message.role === "user") && typeof message.content === "string" && typeof message.stageIndex === "number";
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as SummarizeRequest | null;
  const stage = typeof body?.stage === "string" ? body.stage.trim() : "";
  const messages = Array.isArray(body?.messages) ? body.messages.filter(isWritingMessage) : [];
  const hasUserMessage = messages.some((message) => message.role === "user" && message.content.trim());

  if (!stage || !hasUserMessage) {
    return Response.json({ error: "請先完成這一步的對話。" }, { status: 400 });
  }

  getWritingSystemPrompt("summarize");
  return Response.json({ content: getMockStageSummary(messages) });
}