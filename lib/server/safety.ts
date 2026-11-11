import "server-only";

import { CHILD_BLOCK_REPLY, classifyUnsafeText } from "@/lib/content-safety";
import {
  GatewayRejectedError,
  GatewayUnavailableError,
  moderateOutputWithGateway,
  resetGatewaySession,
  sanitizeWithGateway,
  type GatewayInspectResult,
} from "@/lib/gateway";
import { inspectPii } from "@/lib/pii-preview";
import { getConfig } from "@/lib/server/config";
import { logWarn } from "@/lib/server/log";

/**
 * Server-side enforcement of the safety gateway.
 *
 * The browser is not a trust boundary. Every route that sends text to a model calls
 * these helpers itself, so skipping the browser's own inspect step gains an attacker
 * nothing. If the gateway cannot answer, the request is refused (fail closed) unless
 * `SAFETY_ALLOW_LOCAL_FALLBACK` is set, which is ignored in production builds.
 */

/** No verdict could be obtained. The caller must not forward the text to a model. */
export class SafetyUnavailableError extends Error {
  constructor() {
    super("safety check unavailable");
    this.name = "SafetyUnavailableError";
  }
}

/** The text itself is unacceptable (e.g. longer than the gateway accepts). */
export class SafetyRejectedError extends Error {
  constructor() {
    super("text rejected by safety check");
    this.name = "SafetyRejectedError";
  }
}

export type SafetyVerdict = {
  blocked: boolean;
  /** Child-safe sentence to show when `blocked`. */
  childMessage: string | null;
  /** Text that is safe to send to the model (PII replaced by placeholders). */
  text: string;
  /** Number of sensitive items the gateway replaced. */
  protectedCount: number;
};

function toVerdict(result: GatewayInspectResult, fallbackText: string): SafetyVerdict {
  return {
    blocked: result.blocked,
    childMessage: result.child_message,
    text: result.processed_text.trim() || fallbackText,
    protectedCount: result.entities.length,
  };
}

function failure(error: unknown): never {
  if (error instanceof GatewayRejectedError) {
    throw new SafetyRejectedError();
  }
  if (error instanceof GatewayUnavailableError) {
    logWarn("safety_unavailable", { reason: error.reason });
  }
  throw new SafetyUnavailableError();
}

/** Tokenize PII and check content before `text` is allowed anywhere near a model. */
export async function sanitizeForModel(sessionId: string, text: string): Promise<SafetyVerdict> {
  try {
    return toVerdict(await sanitizeWithGateway(sessionId, text), text);
  } catch (error) {
    if (error instanceof GatewayUnavailableError && getConfig().gateway.allowLocalFallback) {
      const local = inspectPii(text);
      const unsafe = classifyUnsafeText(local.safeText);
      return {
        blocked: Boolean(unsafe),
        childMessage: unsafe ? CHILD_BLOCK_REPLY : null,
        text: local.safeText || text,
        protectedCount: local.hits.length,
      };
    }
    return failure(error);
  }
}

/** Check a model reply before a child can see it. Never rewrites ordinary words. */
export async function moderateModelOutput(sessionId: string, text: string): Promise<SafetyVerdict> {
  try {
    return toVerdict(await moderateOutputWithGateway(sessionId, text), text);
  } catch (error) {
    if (error instanceof GatewayUnavailableError && getConfig().gateway.allowLocalFallback) {
      const unsafe = classifyUnsafeText(text);
      return { blocked: Boolean(unsafe), childMessage: unsafe ? CHILD_BLOCK_REPLY : null, text, protectedCount: 0 };
    }
    return failure(error);
  }
}

export const SAFETY_UNAVAILABLE_MESSAGE = "現在沒辦法檢查這句話，請稍後再試。";
export const SAFETY_REJECTED_MESSAGE = "這句話太長了，請分成幾句再問。";

/** A throwaway session for requests that have no stable conversation id. */
export function ephemeralSessionId() {
  return `req-${crypto.randomUUID()}`;
}

/** Best-effort: drop a throwaway session's PII mappings as soon as the request is done. */
export function forgetSession(sessionId: string) {
  void resetGatewaySession(sessionId).catch(() => undefined);
}
