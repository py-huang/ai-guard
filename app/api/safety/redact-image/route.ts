import { GatewayUnavailableError, redactImageWithGateway } from "@/lib/gateway";
import { labelsForImageEntities, MAX_IMAGE_BYTES } from "@/lib/safety-redact";

export async function POST(request: Request) {
  const form = await request.formData().catch(() => null);
  const sessionId = typeof form?.get("sessionId") === "string" ? form.get("sessionId")!.toString().trim() : "";
  const file = form?.get("file");

  if (!sessionId || !(file instanceof File) || file.size < 1) {
    return Response.json({ error: "請先選擇一張圖片。" }, { status: 400 });
  }

  if (file.size > MAX_IMAGE_BYTES) {
    return Response.json({ error: "這張圖片太大了，請換一張小一點的。" }, { status: 400 });
  }

  try {
    const redacted = await redactImageWithGateway(sessionId, file);
    const changed = redacted.coverage > 0.002 || redacted.entities.length > 0;

    const allowedReasons = new Set(["coverage", "sensitive", "document", "body", "violence", "voyeur", "other", "face"]);
    const blockReason = redacted.blockReason && allowedReasons.has(redacted.blockReason) ? redacted.blockReason : null;

    return Response.json({
      source: "gateway",
      changed,
      redactedPngBase64: redacted.blocked ? "" : redacted.png.toString("base64"),
      fields: labelsForImageEntities(redacted.entities),
      coverage: redacted.coverage,
      blocked: redacted.blocked,
      blockReason,
    });
  } catch (error) {
    if (!(error instanceof GatewayUnavailableError)) {
      console.error("Safety image redact failed", error);
    }
    return Response.json({ error: "現在沒辦法檢查這張圖片，請稍後再試。" }, { status: 503 });
  }
}
