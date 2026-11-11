import { CHILD_LEARNING_PARTNER_PROMPT } from "@/lib/child-llm-prompt";
import { DISASTER_RUMOR_REPLY, isDisasterRumor, needsLiveSearch } from "@/lib/disaster-rumor";
import { GeminiBusyError, generateGeminiText, type GeminiChatMessage } from "@/lib/gemini";
import { getConfig } from "@/lib/server/config";
import { enforceRateLimit, jsonError, parseSessionId, PayloadTooLargeError, readJsonBody, tooLargeResponse } from "@/lib/server/http";
import { isRegisteredRedactedImage } from "@/lib/server/image-registry";
import { logError } from "@/lib/server/log";
import {
  moderateModelOutput,
  SAFETY_REJECTED_MESSAGE,
  SAFETY_UNAVAILABLE_MESSAGE,
  ephemeralSessionId,
  forgetSession,
  SafetyRejectedError,
  SafetyUnavailableError,
  sanitizeForModel,
} from "@/lib/server/safety";
import { replaceVaultTokensForChild } from "@/lib/vault-tokens";
import { getWritingSystemPrompt } from "@/lib/writing-prompts";

/**
 * Chat endpoint for the child chat page and the writing coach.
 *
 * Trust model: the browser is not trusted. The system prompt is chosen here, every user
 * message is re-checked by the safety gateway here (including older turns, which the
 * browser stores in their original, un-tokenized form), an image is only accepted if this
 * server produced it, and the model's reply is moderated here before it is returned.
 */

type Profile = "chat" | "writing";

type ChatCompletionRequest = {
  temperature?: unknown;
  messages?: unknown;
  image?: unknown;
  googleSearch?: unknown;
  sessionId?: unknown;
  profile?: unknown;
  writingStage?: unknown;
};

type TurnMessage = { role: "user" | "assistant"; content: string };

function isTurnMessage(value: unknown): value is TurnMessage {
  if (!value || typeof value !== "object") {
    return false;
  }

  // Note: a client-supplied "system" message is deliberately not accepted.
  const message = value as Partial<TurnMessage>;
  return (message.role === "assistant" || message.role === "user") && typeof message.content === "string" && Boolean(message.content.trim());
}

function systemPromptFor(profile: Profile, writingStage: unknown) {
  if (profile === "writing") {
    const stage = typeof writingStage === "string" ? writingStage.replace(/\s+/g, " ").trim().slice(0, 60) : "";
    return `${getWritingSystemPrompt("chat")}\n目前寫作階段：${stage}\n請直接回覆孩子下一句引導問題，不要加上角色名稱。`;
  }
  return CHILD_LEARNING_PARTNER_PROMPT;
}

function reply(content: string, grounding: { sources: unknown[]; searchQueries: unknown[] } = { sources: [], searchQueries: [] }) {
  return Response.json(
    { choices: [{ message: { role: "assistant", content } }], grounding },
    { headers: { "Cache-Control": "no-store" } },
  );
}

export async function POST(request: Request) {
  const limited = enforceRateLimit(request, "chat");
  if (limited) {
    return limited;
  }

  const config = getConfig();
  const { limits } = config;

  let body: ChatCompletionRequest | null;
  try {
    body = await readJsonBody<ChatCompletionRequest>(request, limits.chatBodyBytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return tooLargeResponse();
    }
    throw error;
  }

  const profile: Profile = body?.profile === "writing" ? "writing" : "chat";
  // Old clients that send no session id still get consistent placeholders within this request.
  const suppliedSessionId = parseSessionId(body?.sessionId);
  const sessionId = suppliedSessionId || ephemeralSessionId();
  const turns = (Array.isArray(body?.messages) ? body.messages.filter(isTurnMessage) : []).slice(-limits.maxHistoryMessages);
  const lastTurn = turns.at(-1);

  if (lastTurn?.role !== "user") {
    return jsonError("對話資料不完整。", 400);
  }
  if (turns.some((turn) => turn.role === "user" && turn.content.length > limits.maxModelUserTextChars)) {
    return jsonError(SAFETY_REJECTED_MESSAGE, 400);
  }

  const temperature = typeof body?.temperature === "number" && body.temperature >= 0 && body.temperature <= 2 ? body.temperature : undefined;
  const imageBody = body?.image && typeof body.image === "object" ? (body.image as { data?: unknown }) : null;
  const imageData = typeof imageBody?.data === "string" ? imageBody.data.trim() : "";

  if (imageData) {
    if (imageData.length > limits.maxImageBase64Chars || !isRegisteredRedactedImage(imageData)) {
      // Not something this server redacted: never forward it to the model.
      return jsonError("請重新選擇這張圖片。", 400);
    }
  }
  const image = imageData ? { mimeType: "image/png", data: imageData } : undefined;

  try {
    // Re-check every user turn. Older turns are stored in the browser as typed (with
    // names, schools...), so only the newest one has been tokenized by the browser's flow.
    const checked = await Promise.all(
      turns.map(async (turn) => {
        if (turn.role === "assistant") {
          return { turn: { role: turn.role, content: turn.content.slice(0, limits.maxAssistantTextChars) }, blocked: false, childMessage: null as string | null };
        }
        const verdict = await sanitizeForModel(sessionId, turn.content);
        return { turn: { role: turn.role, content: verdict.text }, blocked: verdict.blocked, childMessage: verdict.childMessage };
      }),
    );

    const latest = checked.at(-1);
    if (latest?.blocked) {
      return reply(latest.childMessage || "這個問題我們先不要繼續。");
    }

    const messages: GeminiChatMessage[] = [
      { role: "system", content: systemPromptFor(profile, body?.writingStage) },
      // An earlier turn that was blocked is replaced, not forwarded.
      ...checked.map(({ turn, blocked }) => (blocked ? { role: turn.role, content: "（這句話已被擋下）" } : turn)),
    ];

    const lastUserText = lastTurn.content;
    const googleSearch = profile === "chat" && (body?.googleSearch === true || (body?.googleSearch !== false && needsLiveSearch(lastUserText)));
    const { text, sources, searchQueries } = await generateGeminiText({ messages, temperature, image, googleSearch });

    const moderated = await moderateModelOutput(sessionId, text.slice(0, 20_000));
    if (moderated.blocked) {
      return reply(moderated.childMessage || "這個問題我們先不要繼續。");
    }

    return reply(replaceVaultTokensForChild(moderated.text), { sources, searchQueries });
  } catch (error) {
    if (error instanceof SafetyRejectedError) {
      return jsonError(SAFETY_REJECTED_MESSAGE, 400);
    }
    if (error instanceof SafetyUnavailableError) {
      return jsonError(SAFETY_UNAVAILABLE_MESSAGE, 503, { retryable: true });
    }

    logError("chat_completion_failed", error, { profile });
    if (isDisasterRumor(lastTurn.content)) {
      return reply(DISASTER_RUMOR_REPLY);
    }
    if (error instanceof GeminiBusyError) {
      return jsonError(error.message, 503, { retryable: true });
    }
    return jsonError("暫時無法回覆。請再試一次。", 502);
  } finally {
    if (!suppliedSessionId) {
      forgetSession(sessionId);
    }
  }
}
