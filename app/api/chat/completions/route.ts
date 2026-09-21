import { GeminiBusyError, generateGeminiText, type GeminiChatMessage } from "@/lib/gemini";

type ChatCompletionRequest = {
  temperature?: unknown;
  messages?: unknown;
  image?: unknown;
};

function isChatMessage(value: unknown): value is GeminiChatMessage {
  if (!value || typeof value !== "object") {
    return false;
  }

  const message = value as Partial<GeminiChatMessage>;
  return (message.role === "system" || message.role === "assistant" || message.role === "user") && typeof message.content === "string" && Boolean(message.content.trim());
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as ChatCompletionRequest | null;
  const messages = Array.isArray(body?.messages) ? body.messages.filter(isChatMessage) : [];
  const hasUserMessage = messages.some((message) => message.role === "user");
  const temperature = typeof body?.temperature === "number" && body.temperature >= 0 && body.temperature <= 2 ? body.temperature : undefined;
  const imageBody = body?.image && typeof body.image === "object" ? (body.image as { mimeType?: unknown; data?: unknown }) : null;
  const image =
    typeof imageBody?.data === "string" && imageBody.data.trim()
      ? { mimeType: typeof imageBody.mimeType === "string" && imageBody.mimeType.trim() ? imageBody.mimeType : "image/png", data: imageBody.data.trim() }
      : undefined;

  if (!hasUserMessage) {
    return Response.json({ error: "對話資料不完整。" }, { status: 400 });
  }

  try {
    const content = await generateGeminiText({ messages, temperature, image });

    return Response.json({ choices: [{ message: { role: "assistant", content } }] });
  } catch (error) {
    console.error("Chat completion failed", error);
    if (error instanceof GeminiBusyError) {
      return Response.json({ error: error.message, retryable: true }, { status: 503 });
    }
    return Response.json({ error: "暫時無法回覆。請再試一次。" }, { status: 502 });
  }
}
