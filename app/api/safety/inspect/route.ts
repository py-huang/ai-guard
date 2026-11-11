import { GatewayRejectedError, GatewayUnavailableError, inspectWithGateway } from "@/lib/gateway";
import { inspectPii, type PiiKind } from "@/lib/pii-preview";
import { getConfig } from "@/lib/server/config";
import { enforceRateLimit, jsonError, parseSessionId, PayloadTooLargeError, readJsonBody, tooLargeResponse } from "@/lib/server/http";
import { logError, logWarn } from "@/lib/server/log";
import { SAFETY_REJECTED_MESSAGE, SAFETY_UNAVAILABLE_MESSAGE } from "@/lib/server/safety";
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
  LINE_ID: "帳號",
  TW_PASSPORT: "護照",
  TW_DRIVER_LICENSE: "駕照",
  TW_BANK_ACCOUNT: "帳號",
  TW_HOUSEHOLD_NO: "戶號",
  DATE_TIME: "生日",
  CREDIT_CARD: "卡號",
};

export async function POST(request: Request) {
  const limited = enforceRateLimit(request, "inspect");
  if (limited) {
    return limited;
  }

  const config = getConfig();
  let body: InspectBody | null;
  try {
    body = await readJsonBody<InspectBody>(request, config.limits.jsonBodyBytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return tooLargeResponse();
    }
    throw error;
  }

  const sessionId = parseSessionId(body?.sessionId);
  const text = typeof body?.text === "string" ? body.text.trim() : "";

  if (!sessionId || !text) {
    return jsonError("請先輸入問題。", 400);
  }

  if (text.length > config.limits.maxUserTextChars) {
    return jsonError(SAFETY_REJECTED_MESSAGE, 400);
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

    return Response.json(
      {
        source: "gateway",
        blocked: result.blocked,
        childMessage: result.child_message,
        processedText: result.processed_text,
        hits,
        safeText: safeText || (hits.length ? "個人資料已隱藏" : text),
      },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch (error) {
    if (error instanceof GatewayRejectedError) {
      return jsonError(SAFETY_REJECTED_MESSAGE, 400);
    }

    if (error instanceof GatewayUnavailableError && config.gateway.allowLocalFallback) {
      // Development convenience only (never honoured in production): weak local rules.
      logWarn("inspect_local_fallback", { reason: error.reason });
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

    if (!(error instanceof GatewayUnavailableError)) {
      logError("inspect_failed", error);
    } else {
      logWarn("inspect_unavailable", { reason: error.reason });
    }
    // Fail closed: without a verdict the text must not be treated as safe.
    return jsonError(SAFETY_UNAVAILABLE_MESSAGE, 503, { retryable: true });
  }
}
