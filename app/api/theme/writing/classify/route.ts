import { getConfig } from "@/lib/server/config";
import { enforceRateLimit, jsonError, PayloadTooLargeError, readJsonBody, tooLargeResponse } from "@/lib/server/http";
import { logError } from "@/lib/server/log";
import { ephemeralSessionId, forgetSession, SafetyUnavailableError, sanitizeForModel, SAFETY_UNAVAILABLE_MESSAGE } from "@/lib/server/safety";
import { classifyWritingIntent } from "@/lib/writing";

type ClassifyRequest = {
  input?: unknown;
};

export async function POST(request: Request) {
  const limited = enforceRateLimit(request, "writing");
  if (limited) {
    return limited;
  }

  const { limits } = getConfig();
  let body: ClassifyRequest | null;
  try {
    body = await readJsonBody<ClassifyRequest>(request, limits.jsonBodyBytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return tooLargeResponse();
    }
    throw error;
  }

  const input = typeof body?.input === "string" ? body.input.trim() : "";

  if (!input) {
    return jsonError("請輸入想問的內容。", 400);
  }
  if (input.length > limits.maxModelUserTextChars) {
    return jsonError("這句話太長了，請分成幾句再問。", 400);
  }

  const sessionId = ephemeralSessionId();
  try {
    const verdict = await sanitizeForModel(sessionId, input);
    if (verdict.blocked) {
      // Not a writing request; the normal chat path will show the child-safe reply.
      return Response.json({ isThemeMode: false });
    }
    return Response.json(await classifyWritingIntent(verdict.text));
  } catch (error) {
    if (error instanceof SafetyUnavailableError) {
      return jsonError(SAFETY_UNAVAILABLE_MESSAGE, 503, { retryable: true });
    }
    logError("writing_classify_failed", error);
    return jsonError("暫時無法判斷主題。", 502);
  } finally {
    forgetSession(sessionId);
  }
}
