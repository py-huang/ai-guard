import "server-only";

import { mkdirSync } from "node:fs";
import path from "node:path";

import { getConfig } from "@/lib/server/config";
import type { Conversation } from "@/types/conversation";

/**
 * File-backed store for watch call records (VOICE_RECORD_STORE=sqlite).
 *
 * Uses Node's built-in `node:sqlite`, so there is no native module to compile. It is still
 * flagged experimental in Node 22, which is fine for a single-machine demo; swap this file for
 * Postgres (same three functions) when the product needs more than one server.
 *
 * Only already-masked text is ever stored: the caller builds the record from the gateway's
 * output, and `sanitizeConversation` in the route drops everything it does not recognise.
 */

type Statement = {
  run(...params: unknown[]): unknown;
  all(...params: unknown[]): Array<Record<string, unknown>>;
};

type Database = {
  exec(sql: string): void;
  prepare(sql: string): Statement;
};

type SqliteModule = { DatabaseSync: new (file: string) => Database };

type Handle = { db: Database; file: string };

const globalHandle = globalThis as unknown as { __aiGuardVoiceDb?: Handle };

function loadSqlite(): SqliteModule {
  // getBuiltinModule keeps the bundler from trying to resolve a built-in it does not know yet.
  const loaded = process.getBuiltinModule?.("node:sqlite") as SqliteModule | undefined;
  if (!loaded?.DatabaseSync) {
    throw new Error("node:sqlite is not available; use Node 22.5 or newer, or set VOICE_RECORD_STORE=local");
  }
  return loaded;
}

function open(): Database {
  const file = path.resolve(process.cwd(), getConfig().voiceRecords.dbPath);
  if (globalHandle.__aiGuardVoiceDb?.file === file) {
    return globalHandle.__aiGuardVoiceDb.db;
  }

  mkdirSync(path.dirname(file), { recursive: true });
  const db = new (loadSqlite().DatabaseSync)(file);
  db.exec("PRAGMA journal_mode = WAL");
  db.exec(
    `CREATE TABLE IF NOT EXISTS voice_sessions (
       id TEXT PRIMARY KEY,
       updated_at INTEGER NOT NULL,
       payload TEXT NOT NULL
     )`,
  );
  db.exec("CREATE INDEX IF NOT EXISTS voice_sessions_updated ON voice_sessions (updated_at DESC)");
  globalHandle.__aiGuardVoiceDb = { db, file };
  return db;
}

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * Deletes calls older than VOICE_RECORD_RETENTION_DAYS (0 = keep). `updated_at` is safe to use:
 * the route clamps it to within a day of the server clock, so a device cannot make a record
 * immortal by sending a far-future time.
 */
export function purgeExpiredVoiceSessions(now = Date.now()): number {
  const days = getConfig().voiceRecords.retentionDays;
  if (days <= 0) {
    return 0;
  }
  const result = open()
    .prepare("DELETE FROM voice_sessions WHERE updated_at < ?")
    .run(now - days * DAY_MS) as { changes?: number | bigint } | undefined;
  return Number(result?.changes ?? 0);
}

/** Periodic clean-up so old calls are deleted even when nobody is reading or writing. */
export function startVoiceRetentionTimer(everyMs = 60 * 60 * 1000) {
  const globalTimer = globalThis as unknown as { __aiGuardVoicePurge?: ReturnType<typeof setInterval> };
  if (globalTimer.__aiGuardVoicePurge) {
    return;
  }
  const run = () => {
    try {
      purgeExpiredVoiceSessions();
    } catch {
      // Next time; the read/write paths purge as well.
    }
  };
  run();
  globalTimer.__aiGuardVoicePurge = setInterval(run, everyMs);
  globalTimer.__aiGuardVoicePurge.unref?.();
}

export function saveVoiceSession(conversation: Conversation) {
  const db = open();
  purgeExpiredVoiceSessions();
  db.prepare(
    `INSERT INTO voice_sessions (id, updated_at, payload) VALUES (?, ?, ?)
     ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at, payload = excluded.payload`,
  ).run(conversation.id, conversation.updatedAt, JSON.stringify(conversation));

  // Keep the newest N so the file cannot grow without bound.
  db.prepare(
    `DELETE FROM voice_sessions WHERE id NOT IN (
       SELECT id FROM voice_sessions ORDER BY updated_at DESC LIMIT ?
     )`,
  ).run(getConfig().voiceRecords.maxSessions);
}

export function listVoiceSessions(limit = 100): Conversation[] {
  // Expired calls must never be served, even if the hourly clean-up has not run yet.
  purgeExpiredVoiceSessions();
  const rows = open()
    .prepare("SELECT payload FROM voice_sessions ORDER BY updated_at DESC LIMIT ?")
    .all(limit);

  const sessions: Conversation[] = [];
  for (const row of rows) {
    try {
      sessions.push(JSON.parse(String(row.payload)) as Conversation);
    } catch {
      // A damaged row must not take the whole list down.
    }
  }
  return sessions;
}

/** Test hook: forget the open handle so a different VOICE_RECORD_DB_PATH can be used. */
export function closeVoiceStoreForTests() {
  delete globalHandle.__aiGuardVoiceDb;
}
