import type { Conversation, ConversationMessage, SafetyEvent } from "@/types/conversation";

/**
 * Client side of watch call records.
 *
 * The server decides where records live (VOICE_RECORD_STORE): "local" means this browser's own
 * conversation store, "sqlite" means a file on the server that parent pages on other devices
 * poll. Either way only masked text is recorded.
 */

export type WatchTurnStatus = "safe" | "protected" | "critical";

export type WatchTurnRecord = {
  /** Masked for parents, e.g. 「我叫［姓名已隱藏］」. Kept for blocked sentences too, for parents only. */
  user: string;
  /** Child-friendly masked wording, used as the "safe version" shown to parents. */
  safeUser: string;
  assistant: string;
  status: WatchTurnStatus;
  at: number;
};

const TOKEN_KEY = "ai-guard-parent-token";

/** What child-facing screens show instead of a sentence the safety check stopped. */
export const BLOCKED_USER_PLACEHOLDER = "（這句話已被安全機制攔下）";

/**
 * The shared secret for the sqlite store. The server prints a link (and QR code) such as
 * `/mobile/history#token=...`; opening it once is enough. The secret is kept in this browser and
 * removed from the address bar right away, so it does not stay in the visible URL or be shared by
 * accident. `#` (rather than `?`) means the browser never sends it to the server or a proxy.
 * The older `?token=` form still works.
 */
export function parentToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  try {
    const url = new URL(window.location.href);
    const hash = new URLSearchParams(url.hash.replace(/^#/, ""));
    const fromUrl = (hash.get("token") ?? url.searchParams.get("token") ?? "").trim();
    if (fromUrl) {
      window.localStorage.setItem(TOKEN_KEY, fromUrl);
      hash.delete("token");
      url.searchParams.delete("token");
      url.hash = hash.toString();
      window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
      return fromUrl;
    }
    return window.localStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

/** Calls older than this are also dropped from the copies kept in this browser. */
export function isExpiredRecord(updatedAt: number, retentionDays: number, now = Date.now()) {
  return retentionDays > 0 && updatedAt < now - retentionDays * 24 * 60 * 60 * 1000;
}

function tokenHeaders(): Record<string, string> {
  const token = parentToken();
  return token ? { "x-parent-token": token } : {};
}

/** Turns the turns of one finished call into the same shape the parent pages already read. */
export function buildWatchConversation(options: {
  sessionId: string;
  startedAt: number;
  endedAt: number;
  turns: WatchTurnRecord[];
}): Conversation | null {
  const { sessionId, startedAt, endedAt, turns } = options;
  if (turns.length === 0) {
    return null;
  }

  const messages: ConversationMessage[] = [];
  const safetyEvents: SafetyEvent[] = [];

  turns.forEach((turn, index) => {
    const critical = turn.status === "critical";
    messages.push({
      role: "user",
      content: critical && !turn.user ? BLOCKED_USER_PLACEHOLDER : turn.user,
      ...(turn.status === "protected" ? { protected: true } : {}),
      ...(critical ? { blocked: true } : {}),
    });
    messages.push({ role: "assistant", content: turn.assistant, ...(critical ? { blocked: true } : {}) });

    if (turn.status !== "safe") {
      safetyEvents.push({
        id: `${sessionId}-${index + 1}`,
        type: turn.status,
        createdAt: turn.at,
        category: "voice",
        ...(turn.status === "protected" ? { maskedOriginal: turn.user, safeText: turn.safeUser } : {}),
        ...(critical && turn.user ? { maskedOriginal: turn.user } : {}),
        read: false,
        acknowledged: false,
      });
    }
  });

  const firstSafe = turns.find((turn) => turn.status === "safe" && turn.user);
  return {
    id: sessionId,
    title: firstSafe ? firstSafe.user.slice(0, 24) : "手錶語音通話",
    updatedAt: endedAt,
    category: "voice",
    channel: "watch",
    durationSec: Math.max(0, Math.round((endedAt - startedAt) / 1000)),
    messages,
    safetyEvents,
  };
}

export type SaveResult = "sqlite" | "local" | "failed";

/**
 * Asks the server where to keep a finished call. Returns "local" when the caller should keep it
 * in this browser (the default, or when the server could not be reached or refused).
 */
export async function submitWatchConversation(conversation: Conversation): Promise<SaveResult> {
  try {
    const response = await fetch("/api/voice-sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...tokenHeaders() },
      body: JSON.stringify({ conversation }),
    });
    if (response.ok) {
      const payload = (await response.json()) as { store?: string };
      return payload.store === "sqlite" ? "sqlite" : "local";
    }
    // Refused (wrong or missing token) or server error: do not lose the record.
    return "failed";
  } catch {
    return "failed";
  }
}

export type RemoteSessions =
  | { kind: "local"; retentionDays: number }
  | { kind: "sessions"; conversations: Conversation[]; retentionDays: number }
  | { kind: "denied" }
  | { kind: "error" };

/** What the parent pages poll. "local" and "denied" tell the caller to stop asking. */
export async function fetchRemoteSessions(signal?: AbortSignal): Promise<RemoteSessions> {
  try {
    const response = await fetch("/api/voice-sessions", { headers: tokenHeaders(), cache: "no-store", signal });
    if (response.status === 401 || response.status === 503) {
      return { kind: "denied" };
    }
    if (!response.ok) {
      return { kind: "error" };
    }
    const payload = (await response.json()) as { store?: string; sessions?: Conversation[]; retentionDays?: number };
    const retentionDays = typeof payload.retentionDays === "number" && payload.retentionDays > 0 ? payload.retentionDays : 0;
    if (payload.store !== "sqlite") {
      return { kind: "local", retentionDays };
    }
    return { kind: "sessions", conversations: Array.isArray(payload.sessions) ? payload.sessions : [], retentionDays };
  } catch {
    return { kind: "error" };
  }
}
