import { GatewayRejectedError, GatewayUnavailableError, redactImageWithGateway } from "@/lib/gateway";
import { labelsForImageEntities, MAX_IMAGE_BYTES } from "@/lib/safety-redact";
import { enforceRateLimit, jsonError, parseSessionId } from "@/lib/server/http";
import { registerRedactedImage } from "@/lib/server/image-registry";
import { logError, logWarn } from "@/lib/server/log";

const IMAGE_UNAVAILABLE = "現在沒辦法檢查這張圖片，請稍後再試。";

export async function POST(request: Request) {
  const limited = enforceRateLimit(request, "image");
  if (limited) {
    return limited;
  }

  // Refuse before buffering a huge multipart body. File size is re-checked below.
  const declared = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(declared) && declared > MAX_IMAGE_BYTES + 256 * 1024) {
    return jsonError("這張圖片太大了，請換一張小一點的。", 413);
  }

  const form = await request.formData().catch(() => null);
  const sessionId = parseSessionId(form?.get("sessionId"));
  const file = form?.get("file");

  if (!sessionId || !(file instanceof File) || file.size < 1) {
    return jsonError("請先選擇一張圖片。", 400);
  }

  if (file.size > MAX_IMAGE_BYTES) {
    return jsonError("這張圖片太大了，請換一張小一點的。", 400);
  }

  try {
    const redacted = await redactImageWithGateway(sessionId, file);
    const changed = redacted.coverage > 0.002 || redacted.entities.length > 0;

    const allowedReasons = new Set(["coverage", "sensitive", "document", "body", "violence", "voyeur", "other", "face"]);
    const blockReason = redacted.blockReason && allowedReasons.has(redacted.blockReason) ? redacted.blockReason : null;

    const redactedPngBase64 = redacted.blocked ? "" : redacted.png.toString("base64");
    if (redactedPngBase64) {
      // Only images the gateway produced may later be attached to a model request.
      registerRedactedImage(redactedPngBase64);
    }

    return Response.json(
      {
        source: "gateway",
        changed,
        redactedPngBase64,
        fields: labelsForImageEntities(redacted.entities),
        coverage: redacted.coverage,
        blocked: redacted.blocked,
        blockReason,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    if (error instanceof GatewayUnavailableError) {
      logWarn("redact_image_unavailable", { reason: error.reason });
    } else if (!(error instanceof GatewayRejectedError)) {
      logError("redact_image_failed", error);
    }
    return jsonError(IMAGE_UNAVAILABLE, 503, { retryable: !(error instanceof GatewayRejectedError) });
  }
}
