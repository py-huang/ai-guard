import { GatewayUnavailableError, inspectWithGateway } from "@/lib/gateway";
import { inspectPii, type PiiKind } from "@/lib/pii-preview";

type InspectBody = {
  sessionId?: unknown;
  text?: unknown;
};

const ENTITY_KIND: Record<string, PiiKind> = {
  PERSON: "姓名",
  SCHOOL: "學校",
  PHONE_NUMBER: "電話",
  LOCATION: "地址",
  EMAIL_ADDRESS: "Email",
  EMAIL: "Email",
  TW_ID: "身分證",
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as InspectBody | null;
  const sessionId = typeof body?.sessionId === "string" ? body.sessionId.trim() : "";
  const text = typeof body?.text === "string" ? body.text.trim() : "";

  if (!sessionId || !text) {
    return Response.json({ error: "請先輸入問題。" }, { status: 400 });
  }

  try {
    const result = await inspectWithGateway(sessionId, text);
    const hits = result.entities
      .map((entity) => {
        const kind = ENTITY_KIND[entity.entity_type];
        if (!kind) {
          return null;
        }
        return { kind, value: entity.original };
      })
      .filter((hit): hit is { kind: PiiKind; value: string } => Boolean(hit));

    const local = inspectPii(text);
    const safeText =
      result.entities.length > 0
        ? result.processed_text
            .replace(/<PERSON_\d+>/g, "一位小朋友")
            .replace(/<SCHOOL_\d+>/g, "學校")
            .replace(/<PHONE_NUMBER_\d+>/g, "")
            .replace(/<LOCATION_\d+>/g, "這個城市")
            .replace(/<EMAIL_ADDRESS_\d+>/g, "")
            .replace(/<TW_ID_\d+>/g, "")
            .replace(/\s{2,}/g, " ")
            .trim()
        : local.safeText;

    return Response.json({
      source: "gateway",
      blocked: result.blocked,
      childMessage: result.child_message,
      processedText: result.processed_text,
      hits: hits.length > 0 ? hits : local.hits,
      safeText: safeText || local.safeText,
    });
  } catch (error) {
    if (!(error instanceof GatewayUnavailableError)) {
      console.error("Safety inspect failed", error);
    }

    const local = inspectPii(text);
    return Response.json({
      source: "local",
      blocked: false,
      childMessage: null,
      processedText: local.safeText,
      hits: local.hits,
      safeText: local.safeText,
    });
  }
}
