import { getMockAssistantReply, getWritingSystemPrompt, type WritingMessage } from "@/lib/writing";

type ChatCompletionRequest = {
  theme?: unknown;
  stageIndex?: unknown;
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
  const body = (await request.json().catch(() => null)) as ChatCompletionRequest | null;
  const messages = Array.isArray(body?.messages) ? body.messages.filter(isWritingMessage) : [];
  const stage = typeof body?.stage === "string" ? body.stage.trim() : "";
  const lastUserMessage = messages.findLast((message) => message.role === "user" && message.content.trim());

  if (body?.theme !== "writing" || typeof body?.stageIndex !== "number" || !stage || !lastUserMessage) {
    return Response.json({ error: "對話資料不完整。" }, { status: 400 });
  }

  const content = getMockAssistantReply(lastUserMessage.content, stage);
  getWritingSystemPrompt("chat");

  return Response.json({ message: { role: "assistant", content, stageIndex: body.stageIndex } satisfies WritingMessage });
}