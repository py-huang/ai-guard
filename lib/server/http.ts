import "server-only";

import { getConfig, SESSION_ID_PATTERN, type ServerConfig } from "@/lib/server/config";
import { consume } from "@/lib/server/rate-limit";

export class PayloadTooLargeError extends Error {
  constructor() {
    super("payload too large");
    this.name = "PayloadTooLargeError";
  }
}

/**
 * Reads a JSON body without trusting Content-Length: the stream is cut off as soon as it
 * passes `maxBytes`. Returns `null` for anything that is not valid JSON.
 */
export async function readJsonBody<T = unknown>(request: Request, maxBytes: number): Promise<T | null> {
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declared) && declared > maxBytes) {
    throw new PayloadTooLargeError();
  }

  const reader = request.body?.getReader();
  if (!reader) {
    return null;
  }

  const chunks: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    total += value.byteLength;
    if (total > maxBytes) {
      await reader.cancel().catch(() => undefined);
      throw new PayloadTooLargeError();
    }
    chunks.push(value);
  }

  try {
    return JSON.parse(new TextDecoder().decode(Buffer.concat(chunks))) as T;
  } catch {
    return null;
  }
}

export function jsonError(error: string, status: number, extra: Record<string, unknown> = {}) {
  return Response.json({ error, ...extra }, { status, headers: { "Cache-Control": "no-store" } });
}

export function tooLargeResponse() {
  return jsonError("這份資料太大了，請換一個小一點的。", 413);
}

/**
 * Best-effort caller identity for rate limiting.
 *
 * Header trust order matters: the left-most `X-Forwarded-For` entry is whatever the client
 * typed, so rotating it would bypass the limiter. Cloudflare (our tunnel) overwrites
 * `CF-Connecting-IP`, and a proxy appends the real peer as the *right-most* XFF entry, so we
 * prefer those. With no proxy at all (local dev) everyone shares the "local" bucket.
 */
export function clientKey(request: Request) {
  const cf = request.headers.get("cf-connecting-ip")?.trim();
  if (cf) {
    return cf;
  }
  const real = request.headers.get("x-real-ip")?.trim();
  if (real) {
    return real;
  }
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const parts = forwarded.split(",").map((part) => part.trim()).filter(Boolean);
    const last = parts[parts.length - 1];
    if (last) {
      return last.slice(0, 64);
    }
  }
  return "local";
}

export function enforceRateLimit(request: Request, bucket: keyof ServerConfig["rateLimits"]) {
  const result = consume(bucket, clientKey(request), getConfig().rateLimits[bucket]);
  if (result.allowed) {
    return null;
  }
  return Response.json(
    { error: "現在太多人在問，請稍等一下再試。", retryable: true },
    { status: 429, headers: { "Retry-After": String(result.retryAfterSeconds), "Cache-Control": "no-store" } },
  );
}

export function parseSessionId(value: unknown) {
  const id = typeof value === "string" ? value.trim() : "";
  return SESSION_ID_PATTERN.test(id) ? id : "";
}
