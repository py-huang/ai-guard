import "server-only";

/**
 * Small in-process sliding-window limiter.
 *
 * Good enough to stop a runaway client or a leaked tunnel URL from burning the Gemini
 * quota or the gateway's CPU. It is per server process: when the web tier is scaled out
 * behind a load balancer, move this to the edge or to Redis (same `consume` shape).
 */

type Window = { max: number; windowMs: number };

const MAX_TRACKED_KEYS = 5_000;

type Store = Map<string, number[]>;

const globalStore = globalThis as unknown as { __aiGuardRateLimit?: Store };

function store(): Store {
  globalStore.__aiGuardRateLimit ??= new Map();
  return globalStore.__aiGuardRateLimit;
}

export type RateLimitResult = { allowed: true } | { allowed: false; retryAfterSeconds: number };

export function consume(bucket: string, key: string, limit: Window, now = Date.now()): RateLimitResult {
  const map = store();
  const id = `${bucket}:${key}`;
  const recent = (map.get(id) ?? []).filter((stamp) => now - stamp < limit.windowMs);

  if (recent.length >= limit.max) {
    map.set(id, recent);
    return { allowed: false, retryAfterSeconds: Math.max(1, Math.ceil((recent[0] + limit.windowMs - now) / 1000)) };
  }

  recent.push(now);
  map.delete(id); // re-insert so Map iteration order is least-recently-used first
  map.set(id, recent);

  while (map.size > MAX_TRACKED_KEYS) {
    const oldest = map.keys().next().value;
    if (oldest === undefined) {
      break;
    }
    map.delete(oldest);
  }
  return { allowed: true };
}

export function resetRateLimits() {
  store().clear();
}
