import "server-only";

/**
 * Single place that reads server-side environment variables.
 *
 * Moving from a laptop to a server should only mean changing the environment, never
 * editing code. Everything here is read lazily so tests and `next build` do not need
 * a full environment.
 */

function readBool(name: string, fallback: boolean) {
  const raw = process.env[name]?.trim().toLowerCase();
  if (!raw) {
    return fallback;
  }
  return ["1", "true", "yes", "on"].includes(raw);
}

function readInt(name: string, fallback: number, min: number) {
  const raw = process.env[name]?.trim();
  if (!raw) {
    return fallback;
  }
  const value = Number(raw);
  return Number.isFinite(value) && value >= min ? Math.floor(value) : fallback;
}

function readList(name: string, fallback: string) {
  return (process.env[name] ?? fallback)
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export type ServerConfig = ReturnType<typeof loadConfig>;

function loadConfig() {
  const production = process.env.NODE_ENV === "production";
  return {
    production,
    gateway: {
      url: (process.env.SAFETY_GATEWAY_URL?.trim() || "http://127.0.0.1:8765").replace(/\/+$/, ""),
      token: process.env.SAFETY_GATEWAY_TOKEN?.trim() ?? "",
      timeoutMs: readInt("GATEWAY_TIMEOUT_MS", 8_000, 500),
      imageTimeoutMs: readInt("GATEWAY_IMAGE_TIMEOUT_MS", 30_000, 1_000),
      /**
       * Dev-only escape hatch: when the gateway is down, fall back to the weak local
       * regex instead of refusing. Never honoured in production builds.
       */
      allowLocalFallback: !production && readBool("SAFETY_ALLOW_LOCAL_FALLBACK", false),
    },
    gemini: {
      apiKey: process.env.GEMINI_API_KEY?.trim() ?? "",
      primaryModel: process.env.GEMINI_MODEL?.trim() ?? "",
      fallbackModels: readList("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-flash-latest"),
      transcribeModel: process.env.GEMINI_TRANSCRIBE_MODEL?.trim() || "gemini-3.5-transcribe",
      timeoutMs: readInt("GEMINI_TIMEOUT_MS", 16_000, 1_000),
      searchTimeoutMs: readInt("GEMINI_SEARCH_TIMEOUT_MS", 8_000, 1_000),
      transcribeTimeoutMs: readInt("GEMINI_TRANSCRIBE_TIMEOUT_MS", 30_000, 1_000),
    },
    limits: {
      /** Matches the gateway's own cap so an over-long message is refused, not bypassed. */
      maxUserTextChars: 4_000,
      /** User text may grow slightly after inspection (Socratic prefix, tokens). */
      maxModelUserTextChars: 4_500,
      maxAssistantTextChars: 8_000,
      maxHistoryMessages: 12,
      maxSessionIdChars: 128,
      maxImageBase64Chars: 7_500_000,
      maxAudioBase64Chars: 10_000_000,
      jsonBodyBytes: 64 * 1024,
      chatBodyBytes: 8 * 1024 * 1024,
      audioBodyBytes: 12 * 1024 * 1024,
    },
    rateLimits: {
      inspect: { max: readInt("RATE_LIMIT_INSPECT_PER_MIN", 90, 1), windowMs: 60_000 },
      image: { max: readInt("RATE_LIMIT_IMAGE_PER_MIN", 10, 1), windowMs: 60_000 },
      chat: { max: readInt("RATE_LIMIT_CHAT_PER_MIN", 30, 1), windowMs: 60_000 },
      voice: { max: readInt("RATE_LIMIT_VOICE_PER_MIN", 20, 1), windowMs: 60_000 },
      writing: { max: readInt("RATE_LIMIT_WRITING_PER_MIN", 30, 1), windowMs: 60_000 },
    },
  };
}

let cached: ServerConfig | null = null;

export function getConfig(): ServerConfig {
  cached ??= loadConfig();
  return cached;
}

/** Session ids are echoed to logs and the gateway: keep them boring. */
export const SESSION_ID_PATTERN = /^[A-Za-z0-9_.:-]{1,128}$/;
