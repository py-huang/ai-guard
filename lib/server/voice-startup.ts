import "server-only";

import { networkInterfaces } from "node:os";

import { getConfig } from "@/lib/server/config";
import { resolveParentToken } from "@/lib/server/parent-token";
import { startVoiceRetentionTimer } from "@/lib/server/voice-store";

/**
 * Runs once when the server starts (see instrumentation.ts), and only for VOICE_RECORD_STORE=sqlite:
 *   - starts the clean-up that deletes calls older than VOICE_RECORD_RETENTION_DAYS;
 *   - makes sure a parent secret exists and prints the pairing link and a QR code for it.
 */
export async function startVoiceRecordServices() {
  const { store, retentionDays, pairBaseUrl, printPairing } = getConfig().voiceRecords;
  if (store !== "sqlite") {
    return;
  }

  try {
    startVoiceRetentionTimer();
  } catch (error) {
    console.warn("無法啟動通話紀錄的自動清理：", error instanceof Error ? error.message : error);
  }

  const parent = resolveParentToken();
  if (!parent) {
    console.warn("無法建立家長端密碼（資料夾不可寫入？），通話紀錄功能會拒絕所有請求。");
    return;
  }
  if (!printPairing) {
    return;
  }

  const base = pairBaseUrl || `http://${lanAddress() ?? "localhost"}:${process.env.PORT ?? 3000}`;
  // After "#", so the browser never sends the secret to the server, a proxy, or a Referer header.
  const parentUrl = `${base}/mobile/history#token=${parent.token}`;
  const watchUrl = `${base}/watch#token=${parent.token}`;

  const lines = [
    "",
    "── 家長端配對 ──────────────────────────────────────────────",
    parent.source === "generated" ? "已自動產生家長端密碼（不用自己設定）。" : "家長端密碼已就緒。",
    "家長用手機掃描下面的 QR code（或把網址傳過去），只要做一次：",
    `  家長頁面 ${parentUrl}`,
    `  手錶頁面 ${watchUrl}`,
    retentionDays > 0 ? `通話紀錄保存 ${retentionDays} 天後自動刪除。` : "通話紀錄不會自動過期（VOICE_RECORD_RETENTION_DAYS=0）。",
    "這串網址等於密碼，請不要貼到公開的地方。要換掉密碼：刪除資料庫旁的 parent-token 檔後重啟。",
  ];
  console.log(lines.join("\n"));

  try {
    const { default: qrcode } = await import("qrcode-terminal");
    qrcode.generate(parentUrl, { small: true }, (code: string) => console.log(`${code}\n`));
  } catch {
    // The link above is enough; the QR code is a convenience.
  }
}

function lanAddress(): string | undefined {
  for (const addresses of Object.values(networkInterfaces())) {
    for (const address of addresses ?? []) {
      if (address.family === "IPv4" && !address.internal) {
        return address.address;
      }
    }
  }
  return undefined;
}
