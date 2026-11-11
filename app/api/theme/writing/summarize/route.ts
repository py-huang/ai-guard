import { getConfig } from "@/lib/server/config";
import { enforceRateLimit, jsonError, PayloadTooLargeError, readJsonBody, tooLargeResponse } from "@/lib/server/http";
import { logError } from "@/lib/server/log";
import {
  ephemeralSessionId,
  forgetSession,
  moderateModelOutput,
  SAFETY_UNAVAILABLE_MESSAGE,
  SafetyUnavailableError,
  sanitizeForModel,
} from "@/lib/server/safety";
import { replaceVaultTokensForChild } from "@/lib/vault-tokens";
import { summarizeWritingStage, type WritingMessage } from "@/lib/writing";

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
  const limited = enforceRateLimit(request, "writing");
  if (limited) {
    return limited;
  }

  const { limits } = getConfig();
  let body: SummarizeRequest | null;
  try {
    body = await readJsonBody<SummarizeRequest>(request, limits.jsonBodyBytes * 4);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return tooLargeResponse();
    }
    throw error;
  }

  const stage = typeof body?.stage === "string" ? body.stage.replace(/\s+/g, " ").trim().slice(0, 60) : "";
  const messages = (Array.isArray(body?.messages) ? body.messages.filter(isWritingMessage) : []).slice(-limits.maxHistoryMessages * 2);
  const hasUserMessage = messages.some((message) => message.role === "user" && message.content.trim());

  if (!stage || !hasUserMessage) {
    return jsonError("請先完成這一步的對話。", 400);
  }
  if (messages.some((message) => message.role === "user" && message.content.length > limits.maxModelUserTextChars)) {
    return jsonError("這句話太長了，請分成幾句再問。", 400);
  }

  const sessionId = ephemeralSessionId();
  try {
    const checked: WritingMessage[] = [];
    for (const message of messages) {
      if (message.role === "assistant") {
        checked.push({ ...message, content: message.content.slice(0, limits.maxAssistantTextChars) });
        continue;
      }
      const verdict = await sanitizeForModel(sessionId, message.content);
      checked.push({ ...message, content: verdict.blocked ? "（略）" : verdict.text });
    }

    const summary = await summarizeWritingStage(stage, checked);
    const moderated = await moderateModelOutput(sessionId, summary.slice(0, 20_000));
    if (moderated.blocked) {
      return jsonError("暫時無法整理這一步。", 502);
    }
    return Response.json({ content: replaceVaultTokensForChild(moderated.text) });
  } catch (error) {
    if (error instanceof SafetyUnavailableError) {
      return jsonError(SAFETY_UNAVAILABLE_MESSAGE, 503, { retryable: true });
    }
    logError("writing_summary_failed", error);
    return jsonError("暫時無法整理這一步。", 502);
  } finally {
    forgetSession(sessionId);
  }
}
