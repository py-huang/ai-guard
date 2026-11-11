import { CHILD_BLOCK_REPLY, classifyUnsafeText } from "@/lib/content-safety";
import { CHILD_LEARNING_PARTNER_PROMPT } from "@/lib/child-llm-prompt";
import { GeminiBusyError, generateGeminiText, type GeminiChatMessage } from "@/lib/gemini";
import { GatewayRejectedError, GatewayUnavailableError, inspectWithGateway } from "@/lib/gateway";
import { inspectPii } from "@/lib/pii-preview";
import { getConfig } from "@/lib/server/config";
import { enforceRateLimit, jsonError, parseSessionId, PayloadTooLargeError, readJsonBody, tooLargeResponse } from "@/lib/server/http";
import { logError, logWarn } from "@/lib/server/log";
import {
  moderateModelOutput,
  SAFETY_REJECTED_MESSAGE,
  SAFETY_UNAVAILABLE_MESSAGE,
  SafetyRejectedError,
  SafetyUnavailableError,
  sanitizeForModel,
} from "@/lib/server/safety";
import { toSpokenLine } from "@/lib/speak-text";
import { replaceVaultTokensForChild } from "@/lib/vault-tokens";

type RememberTurn = {
  role: "user" | "assistant";
  content: string;
};

type TurnBody = {
  sessionId?: unknown;
  text?: unknown;
  history?: unknown;
};

const VOICE_PROMPT = `這是兒童手錶上的語音通話。
- 用兩到四句口語，適合直接念出來。
- 不要用項目符號、編號、星號、表格或網址。
- 不要複述小朋友剛說的姓名、學校、電話、地址或其他個資。`;

export async function POST(request: Request) {
  const limited = enforceRateLimit(request, "chat");
  if (limited) {
    return limited;
  }

  const config = getConfig();
  let body: TurnBody | null;
  try {
    body = await readJsonBody<TurnBody>(request, config.limits.jsonBodyBytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return tooLargeResponse();
    }
    throw error;
  }

  const sessionId = parseSessionId(body?.sessionId);
  const text = typeof body?.text === "string" ? body.text.trim() : "";
  const history = sanitizeHistory(body?.history);

  if (!sessionId || !text) {
    return jsonError("沒有收到這句話。", 400);
  }
  if (text.length > config.limits.maxUserTextChars) {
    return jsonError(SAFETY_REJECTED_MESSAGE, 400);
  }

  try {
    const inbound = await inspectInbound(sessionId, text);
    if (inbound.blocked || classifyUnsafeText(inbound.processedText)) {
      const speak = toSpokenLine(inbound.childMessage || CHILD_BLOCK_REPLY);
      return Response.json({
        speak,
        blocked: true,
        protected: inbound.protected,
        remember: null,
      });
    }

    // History comes from the browser, so it gets the same check as a fresh message.
    const checkedHistory: RememberTurn[] = [];
    for (const turn of history) {
      if (turn.role === "assistant") {
        checkedHistory.push(turn);
        continue;
      }
      const verdict = await sanitizeForModel(sessionId, turn.content);
      checkedHistory.push({ role: "user", content: verdict.blocked ? "（略）" : verdict.text });
    }

    const messages: GeminiChatMessage[] = [
      { role: "system", content: `${CHILD_LEARNING_PARTNER_PROMPT}\n\n${VOICE_PROMPT}` },
      ...checkedHistory,
      { role: "user", content: inbound.processedText },
    ];
    const generated = await generateGeminiText({ messages, temperature: 0.5, googleSearch: false });
    const outbound = await moderateModelOutput(sessionId, generated.text.slice(0, 20_000));
    const unsafe = outbound.blocked || Boolean(classifyUnsafeText(outbound.text));
    const modelReply = unsafe ? outbound.childMessage || CHILD_BLOCK_REPLY : outbound.text;
    const speak = toSpokenLine(replaceVaultTokensForChild(modelReply)) || "我在，可以再說一次嗎？";

    return Response.json({
      speak,
      blocked: unsafe,
      protected: inbound.protected,
      remember: {
        user: inbound.processedText,
        assistant: modelReply,
      },
    });
  } catch (error) {
    if (error instanceof SafetyRejectedError) {
      return jsonError(SAFETY_REJECTED_MESSAGE, 400);
    }
    if (error instanceof SafetyUnavailableError) {
      return jsonError(SAFETY_UNAVAILABLE_MESSAGE, 503, { retryable: true });
    }
    logError("watch_turn_failed", error);
    if (error instanceof GeminiBusyError) {
      return jsonError(error.message, 503, { retryable: true });
    }
    return jsonError("暫時無法回答。可以再試一次。", 502);
  }
}

/**
 * Full inbound pipeline for the child's new sentence (PII tokens, content safety,
 * Socratic framing, parent-audit event). Fails closed when the gateway cannot answer.
 */
async function inspectInbound(sessionId: string, text: string) {
  try {
    const result = await inspectWithGateway(sessionId, text);
    return {
      blocked: result.blocked,
      childMessage: result.child_message,
      processedText: result.processed_text.trim() || text,
      protected: result.entities.length > 0,
    };
  } catch (error) {
    if (error instanceof GatewayRejectedError) {
      throw new SafetyRejectedError();
    }
    if (error instanceof GatewayUnavailableError && getConfig().gateway.allowLocalFallback) {
      logWarn("watch_inspect_local_fallback", { reason: error.reason });
      const local = inspectPii(text);
      return {
        blocked: false,
        childMessage: null,
        processedText: local.safeText || text,
        protected: local.hits.length > 0,
      };
    }
    if (error instanceof GatewayUnavailableError) {
      logWarn("watch_inspect_unavailable", { reason: error.reason });
    }
    throw new SafetyUnavailableError();
  }
}

function sanitizeHistory(value: unknown): RememberTurn[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .filter((item): item is RememberTurn => {
      if (!item || typeof item !== "object") {
        return false;
      }
      const turn = item as Partial<RememberTurn>;
      return (turn.role === "user" || turn.role === "assistant") && typeof turn.content === "string" && Boolean(turn.content.trim());
    })
    .slice(-8)
    .map((turn) => ({ role: turn.role, content: turn.content.trim().slice(0, 2000) }));
}
