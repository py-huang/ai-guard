import { GatewayUnavailableError, inspectWithGateway } from "@/lib/gateway";
import { inspectPii, type PiiKind } from "@/lib/pii-preview";
import { stripSocraticInboundPrefix } from "@/lib/socratic";

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
  SCHOOL_CLASS: "班級",
  STUDENT_ID: "學號",
  IG_HANDLE: "IG帳號",
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
    const hits = result.entities.map((entity) => ({
      kind: ENTITY_KIND[entity.entity_type] ?? ("其他" as PiiKind),
      value: entity.original,
    }));

    const safeText = stripSocraticInboundPrefix(result.processed_text)
      .replace(/<PERSON_\d+>/g, "一位小朋友")
      .replace(/<SCHOOL_\d+>/g, "學校")
      .replace(/<PHONE_NUMBER_\d+>/g, "")
      .replace(/<LOCATION_\d+>/g, "這個城市")
      .replace(/<EMAIL_ADDRESS_\d+>/g, "")
      .replace(/<TW_ID_\d+>/g, "")
      .replace(/<SCHOOL_CLASS_\d+>/g, "班級")
      .replace(/<STUDENT_ID_\d+>/g, "")
      .replace(/<IG_HANDLE_\d+>/g, "")
      .replace(/<[A-Z][A-Z0-9_]*_\d+>/g, "")
      .replace(/\s{2,}/g, " ")
      .trim();

    return Response.json({
      source: "gateway",
      blocked: result.blocked,
      childMessage: result.child_message,
      processedText: result.processed_text,
      hits,
      safeText: safeText || text,
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
