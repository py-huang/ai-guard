// Checks the parts of the watch-call store that need a clock or a file system, using the real
// TypeScript modules (same loader as route-host.mjs):
//
//   node scripts/check-voice-store.mjs <retentionDays>
//
// Prints one "PASS"/"FAIL" line per check and exits 1 if any failed. scripts/smoke_e2e.py runs it.
import { existsSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { register } from "node:module";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

register("./ts-loader.mjs", import.meta.url);

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const days = Number(process.argv[2] ?? "2");
const dir = mkdtempSync(path.join(tmpdir(), "voice-check-"));
process.env.VOICE_RECORD_STORE = "sqlite";
process.env.VOICE_RECORD_DB_PATH = path.join(dir, "nested", "voice.db");
process.env.VOICE_RECORD_RETENTION_DAYS = String(days);
delete process.env.PARENT_API_TOKEN;

const load = (file) => import(pathToFileURL(path.join(root, file)).href);
const store = await load("lib/server/voice-store.ts");
const tokens = await load("lib/server/parent-token.ts");

let failed = 0;
function check(ok, label) {
  console.log(`${ok ? "PASS" : "FAIL"}  ${label}`);
  if (!ok) {
    failed += 1;
  }
}

const DAY = 24 * 60 * 60 * 1000;
const record = (id, updatedAt) => ({
  id, title: id, updatedAt, category: "voice", channel: "watch", durationSec: 5,
  messages: [{ role: "user", content: "hi" }], safetyEvents: [],
});
const ids = () => store.listVoiceSessions().map((session) => session.id).sort();

try {
  const now = Date.now();
  store.saveVoiceSession(record("fresh", now));
  store.saveVoiceSession(record("old", now - 3 * DAY));

  if (days > 0) {
    check(ids().join() === "fresh", `retention ${days}d: a 3-day-old call is not served`);
    store.saveVoiceSession(record("old2", now - 5 * DAY));
    check(store.purgeExpiredVoiceSessions() === 1, "retention: the purge reports what it deleted");
    check(store.purgeExpiredVoiceSessions(now + (days + 1) * DAY) === 1 && ids().length === 0, "retention: a call expires once its age passes the limit");
  } else {
    check(ids().join() === "fresh,old", "retention 0: nothing is deleted by age");
    check(store.purgeExpiredVoiceSessions(now + 400 * DAY) === 0 && ids().length === 2, "retention 0: not even a year later");
  }

  // Parent secret: generated once, private, stable, and replaceable by a long enough env value.
  const first = tokens.resolveParentToken();
  const file = tokens.parentTokenFile();
  check(first?.source === "generated" && first.token.length >= 24, "token: one is generated when none is configured");
  check(existsSync(file) && (statSync(file).mode & 0o077) === 0, "token: the file is readable by the owner only");
  tokens.forgetParentTokenForTests();
  const again = tokens.resolveParentToken();
  check(again?.token === first?.token && again?.source === "file", "token: it survives a restart (same value read back)");
  writeFileSync(file, "short\n");
  tokens.forgetParentTokenForTests();
  const regenerated = tokens.resolveParentToken();
  check(
    regenerated?.source === "generated" && regenerated.token.length >= 24 && readFileSync(file, "utf8").trim() === regenerated.token,
    "token: a damaged (too short) file is replaced, never accepted and never a permanent lock-out",
  );
} finally {
  rmSync(dir, { recursive: true, force: true });
}

process.exit(failed ? 1 : 0);
