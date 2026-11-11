import "server-only";

import { createHash } from "node:crypto";

/**
 * Remembers which images were produced by the gateway's redactor.
 *
 * The chat endpoint only forwards an image to the model if this process itself handed
 * it out from `/api/safety/redact-image`. That makes "the browser says it was redacted"
 * irrelevant: a client cannot attach an arbitrary photo to a Gemini request.
 *
 * In-process on purpose (single web node today). When the web tier scales out, swap the
 * map for a shared store or return an HMAC-signed handle; the two functions stay the same.
 */

const TTL_MS = 30 * 60 * 1000;
const MAX_ENTRIES = 200;

type Registry = Map<string, number>;

const globalRegistry = globalThis as unknown as { __aiGuardImages?: Registry };

function registry(): Registry {
  globalRegistry.__aiGuardImages ??= new Map();
  return globalRegistry.__aiGuardImages;
}

function digest(base64: string) {
  return createHash("sha256").update(base64.trim()).digest("hex");
}

export function registerRedactedImage(base64: string, now = Date.now()) {
  const map = registry();
  for (const [key, expires] of map) {
    if (expires <= now) {
      map.delete(key);
    }
  }
  map.set(digest(base64), now + TTL_MS);
  while (map.size > MAX_ENTRIES) {
    const oldest = map.keys().next().value;
    if (oldest === undefined) {
      break;
    }
    map.delete(oldest);
  }
}

export function isRegisteredRedactedImage(base64: string, now = Date.now()) {
  const expires = registry().get(digest(base64));
  return expires !== undefined && expires > now;
}
