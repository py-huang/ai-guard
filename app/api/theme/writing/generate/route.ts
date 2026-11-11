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
import { generateWritingPlan, type GenerateWritingResponse } from "@/lib/writing";

type GenerateRequest = {
  input?: unknown;
};

export async function POST(request: Request) {
  const limited = enforceRateLimit(request, "writing");
  if (limited) {
    return limited;
  }

  const { limits } = getConfig();
  let body: GenerateRequest | null;
  try {
    body = await readJsonBody<GenerateRequest>(request, limits.jsonBodyBytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return tooLargeResponse();
    }
    throw error;
  }

  const input = typeof body?.input === "string" ? body.input.trim() : "";

  if (!input) {
    return jsonError("請輸入想寫的主題。", 400);
  }
  if (input.length > limits.maxModelUserTextChars) {
    return jsonError("這句話太長了，請分成幾句再問。", 400);
  }

  const sessionId = ephemeralSessionId();
  try {
    const verdict = await sanitizeForModel(sessionId, input);
    if (verdict.blocked) {
      return jsonError(verdict.childMessage || "這個題目我們先不要寫。", 400);
    }

    const plan = await generateWritingPlan(verdict.text);
    const moderated = await moderateModelOutput(sessionId, [plan.init_question, ...plan.steps, ...plan.outline.map((item) => item.stage)].join("\n"));
    if (moderated.blocked) {
      return jsonError("暫時無法建立寫作計畫。", 502);
    }

    const response: GenerateWritingResponse = {
      ...plan,
      init_question: replaceVaultTokensForChild(plan.init_question),
      theme: "writing",
      theme_id: crypto.randomUUID(),
    };

    return Response.json(response);
  } catch (error) {
    if (error instanceof SafetyUnavailableError) {
      return jsonError(SAFETY_UNAVAILABLE_MESSAGE, 503, { retryable: true });
    }
    logError("writing_plan_failed", error);
    return jsonError("暫時無法建立寫作計畫。", 502);
  } finally {
    forgetSession(sessionId);
  }
}
