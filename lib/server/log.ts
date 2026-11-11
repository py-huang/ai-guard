import "server-only";

/**
 * Structured, PII-free logging.
 *
 * Log facts about a request (route, status, duration, counts). Never log what a child
 * typed, said, or uploaded, and never put it in an Error message you then log.
 */

type Level = "info" | "warn" | "error";
type Fields = Record<string, string | number | boolean | null | undefined>;

function write(level: Level, event: string, fields: Fields) {
  const line = JSON.stringify({
    ts: new Date().toISOString(),
    level,
    service: "web",
    event,
    ...fields,
  });
  if (level === "error") {
    console.error(line);
  } else if (level === "warn") {
    console.warn(line);
  } else {
    console.log(line);
  }
}

export function logInfo(event: string, fields: Fields = {}) {
  write("info", event, fields);
}

export function logWarn(event: string, fields: Fields = {}) {
  write("warn", event, fields);
}

/** Records the error's *kind* (name, status), not its message or stack. */
export function logError(event: string, error: unknown, fields: Fields = {}) {
  const status = error && typeof error === "object" && "status" in error ? Number((error as { status: unknown }).status) : undefined;
  write("error", event, {
    ...fields,
    errorName: error instanceof Error ? error.name : typeof error,
    ...(status && Number.isFinite(status) ? { errorStatus: status } : {}),
  });
}
