import "server-only";

import { getConfig } from "@/lib/server/config";
import { logWarn } from "@/lib/server/log";

export function getSafetyGatewayUrl() {
  return getConfig().gateway.url;
}

/** The gateway could not give us a verdict (down, slow, overloaded, misconfigured). */
export class GatewayUnavailableError extends Error {
  constructor(readonly reason: string = "unavailable") {
    super("safety gateway unavailable");
    this.name = "GatewayUnavailableError";
  }
}

/** The gateway understood the request and refused it (bad or oversized input). */
export class GatewayRejectedError extends Error {
  constructor(readonly status: number) {
    super("safety gateway rejected the request");
    this.name = "GatewayRejectedError";
  }
}

export type GatewayEntity = {
  entity_type: string;
  original: string;
  token: string;
};

export type GatewayInspectResult = {
  session_id: string;
  blocked: boolean;
  block_category: string | null;
  child_message: string | null;
  processed_text: string;
  entities: GatewayEntity[];
};

type GatewayRequest = {
  path: string;
  method?: "GET" | "POST";
  body?: BodyInit;
  headers?: Record<string, string>;
  timeoutMs?: number;
  /** Safe to repeat: one extra attempt on a dropped connection or a 502/503/504. */
  idempotent?: boolean;
};

const TRANSIENT_STATUS = new Set([502, 503, 504]);

async function gatewayFetch({ path, method = "POST", body, headers = {}, timeoutMs, idempotent = false }: GatewayRequest) {
  const { url, token, timeoutMs: defaultTimeout } = getConfig().gateway;
  const attempts = idempotent ? 2 : 1;

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    let response: Response;
    try {
      response = await fetch(`${url}${path}`, {
        method,
        body,
        headers: { ...(token ? { "x-gateway-token": token } : {}), ...headers },
        cache: "no-store",
        signal: AbortSignal.timeout(timeoutMs ?? defaultTimeout),
      });
    } catch (error) {
      const timedOut = error instanceof DOMException && (error.name === "TimeoutError" || error.name === "AbortError");
      if (!timedOut && attempt < attempts) {
        continue;
      }
      throw new GatewayUnavailableError(timedOut ? "timeout" : "network");
    }

    if (response.ok) {
      return response;
    }

    if (TRANSIENT_STATUS.has(response.status) && attempt < attempts) {
      await response.body?.cancel().catch(() => undefined);
      continue;
    }

    await response.body?.cancel().catch(() => undefined);
    if (response.status === 401 || response.status === 403) {
      // Our own misconfiguration (token mismatch). Make it loud in the logs, quiet to the child.
      logWarn("gateway_auth_rejected", { status: response.status });
      throw new GatewayUnavailableError("auth");
    }
    if (response.status === 400 || response.status === 413 || response.status === 422) {
      throw new GatewayRejectedError(response.status);
    }
    throw new GatewayUnavailableError(`status_${response.status}`);
  }

  throw new GatewayUnavailableError("exhausted");
}

async function postText(path: string, sessionId: string, text: string): Promise<GatewayInspectResult> {
  const response = await gatewayFetch({
    path,
    body: JSON.stringify({ session_id: sessionId, text }),
    headers: { "Content-Type": "application/json" },
    idempotent: true,
  });
  return (await response.json()) as GatewayInspectResult;
}

/** Full inbound pipeline for a brand-new child message (PII, safety, Socratic, audit). */
export function inspectWithGateway(sessionId: string, text: string) {
  return postText("/api/inspect", sessionId, text);
}

/** Idempotent re-check of text about to be sent to the model (history, retries). */
export function sanitizeWithGateway(sessionId: string, text: string) {
  return postText("/api/sanitize", sessionId, text);
}

/** Content-safety check on a model reply. Never rewrites ordinary words. */
export function moderateOutputWithGateway(sessionId: string, text: string) {
  return postText("/api/moderate-output", sessionId, text);
}

export async function resetGatewaySession(sessionId: string) {
  await gatewayFetch({
    path: "/api/session/reset",
    body: JSON.stringify({ session_id: sessionId }),
    headers: { "Content-Type": "application/json" },
    idempotent: true,
  });
}

export async function isGatewayReady() {
  try {
    await gatewayFetch({ path: "/readyz", method: "GET", timeoutMs: 2_000 });
    return true;
  } catch {
    return false;
  }
}

export type GatewayImageRedactResult = {
  png: Buffer;
  entities: string[];
  coverage: number;
  blocked: boolean;
  blockReason: string | null;
};

export async function redactImageWithGateway(sessionId: string, file: Blob): Promise<GatewayImageRedactResult> {
  const body = new FormData();
  body.append("file", file, "upload.png");

  const response = await gatewayFetch({
    path: `/api/redact-image?session_id=${encodeURIComponent(sessionId)}`,
    body,
    timeoutMs: getConfig().gateway.imageTimeoutMs,
  });

  const header = response.headers.get("x-detected-entities") ?? "";
  const coverage = Number(response.headers.get("x-redact-coverage") ?? "0");
  const reason = (response.headers.get("x-block-reason") ?? "").trim();
  return {
    png: Buffer.from(await response.arrayBuffer()),
    entities: header
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    coverage: Number.isFinite(coverage) ? coverage : 0,
    blocked: response.headers.get("x-image-blocked") === "1",
    blockReason: reason || null,
  };
}
