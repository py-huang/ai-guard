import "server-only";

import { randomBytes } from "node:crypto";
import { chmodSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import { getConfig } from "@/lib/server/config";

/**
 * The secret that lets parent pages (and the watch) read and write call records.
 *
 * Nobody has to invent one: when PARENT_API_TOKEN is not set the server generates a random
 * secret on first use and keeps it in `parent-token`, next to the database (that folder is
 * git-ignored). It survives restarts, so phones that are already paired keep working. To replace
 * it, delete the file and restart; every device then has to pair again.
 */

const MIN_LENGTH = 16;

export type ParentToken = { token: string; source: "env" | "file" | "generated" };

const globalCache = globalThis as unknown as { __aiGuardParentToken?: { file: string; value: ParentToken } };

export function parentTokenFile() {
  return path.join(path.dirname(path.resolve(process.cwd(), getConfig().voiceRecords.dbPath)), "parent-token");
}

function readExisting(file: string): string | null {
  try {
    const value = readFileSync(file, "utf8").trim();
    return value.length >= MIN_LENGTH ? value : null;
  } catch {
    return null;
  }
}

/** Returns null only when the secret can neither be read nor written (e.g. read-only disk). */
export function resolveParentToken(): ParentToken | null {
  const configured = getConfig().voiceRecords.parentToken;
  if (configured.length >= MIN_LENGTH) {
    return { token: configured, source: "env" };
  }
  if (configured) {
    console.warn(`PARENT_API_TOKEN 太短（至少 ${MIN_LENGTH} 個字元），已改用自動產生的密碼。`);
  }

  const file = parentTokenFile();
  if (globalCache.__aiGuardParentToken?.file === file) {
    return globalCache.__aiGuardParentToken.value;
  }

  const existing = readExisting(file);
  if (existing) {
    return remember(file, { token: existing, source: "file" });
  }

  const token = randomBytes(24).toString("base64url");
  try {
    mkdirSync(path.dirname(file), { recursive: true });
    // "wx" fails if another worker created the file first; then we just read theirs.
    writeFileSync(file, `${token}\n`, { flag: "wx", mode: 0o600 });
    chmodSync(file, 0o600);
    return remember(file, { token, source: "generated" });
  } catch {
    const raced = readExisting(file);
    if (raced) {
      return remember(file, { token: raced, source: "file" });
    }
  }

  // The file exists but holds nothing usable (empty or hand-edited too short): replace it
  // rather than lock everyone out for good.
  try {
    writeFileSync(file, `${token}\n`, { mode: 0o600 });
    chmodSync(file, 0o600);
    return remember(file, { token, source: "generated" });
  } catch {
    return null;
  }
}

function remember(file: string, value: ParentToken) {
  globalCache.__aiGuardParentToken = { file, value };
  return value;
}

/** Empty string means "no secret available", which the routes treat as "refuse everything". */
export function getParentToken() {
  return resolveParentToken()?.token ?? "";
}

/** Test hook. */
export function forgetParentTokenForTests() {
  delete globalCache.__aiGuardParentToken;
}
