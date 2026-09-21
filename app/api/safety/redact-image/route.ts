import { GatewayUnavailableError, redactImageWithGateway } from "@/lib/gateway";

const MAX_BYTES = 4 * 1024 * 1024;

export async function POST(request: Request) {
  const form = await request.formData().catch(() => null);
  const sessionId = typeof form?.get("sessionId") === "string" ? form.get("sessionId")!.toString().trim() : "";
  const file = form?.get("file");

  if (!sessionId || !(file instanceof File) || file.size < 1) {
    return Response.json({ error: "請先選擇一張圖片。" }, { status: 400 });
  }

  if (file.size > MAX_BYTES) {
    return Response.json({ error: "這張圖片太大了，請換一張小一點的。" }, { status: 400 });
  }

  try {
    const original = Buffer.from(await file.arrayBuffer());
    const redacted = await redactImageWithGateway(sessionId, file);
    const changed = redacted.length !== original.length || !redacted.equals(original);

    return Response.json({
      source: "gateway",
      changed,
      redactedPngBase64: redacted.toString("base64"),
    });
  } catch (error) {
    if (!(error instanceof GatewayUnavailableError)) {
      console.error("Safety image redact failed", error);
    }
    return Response.json({ error: "現在沒辦法檢查這張圖片，請稍後再試。" }, { status: 503 });
  }
}
