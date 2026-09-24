import "server-only";

const DEFAULT_GATEWAY_URL = "http://127.0.0.1:8765";

export function getSafetyGatewayUrl() {
  return process.env.SAFETY_GATEWAY_URL?.trim() || DEFAULT_GATEWAY_URL;
}

export class GatewayUnavailableError extends Error {
  constructor() {
    super("safety gateway unavailable");
    this.name = "GatewayUnavailableError";
  }
}

export type GatewayEntity = {
  entity_type: string;
  original: string;
  token: string;
};

export type GatewayInspectResult = {
  session_id: string;
  blocked: boolean;
  block_category: string | null;
  child_message: string | null;
  processed_text: string;
  entities: GatewayEntity[];
};

export async function inspectWithGateway(sessionId: string, text: string): Promise<GatewayInspectResult> {
  const response = await fetch(`${getSafetyGatewayUrl()}/api/inspect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, text }),
    cache: "no-store",
  }).catch(() => null);

  if (!response) {
    throw new GatewayUnavailableError();
  }

  if (!response.ok) {
    throw new GatewayUnavailableError();
  }

  return (await response.json()) as GatewayInspectResult;
}

export type GatewayImageRedactResult = {
  png: Buffer;
  entities: string[];
  coverage: number;
  blocked: boolean;
  blockReason: string | null;
};

export async function redactImageWithGateway(sessionId: string, file: Blob): Promise<GatewayImageRedactResult> {
  const body = new FormData();
  body.append("file", file, "upload.png");

  const response = await fetch(`${getSafetyGatewayUrl()}/api/redact-image?session_id=${encodeURIComponent(sessionId)}`, {
    method: "POST",
    body,
    cache: "no-store",
  }).catch(() => null);

  if (!response) {
    throw new GatewayUnavailableError();
  }

  if (!response.ok) {
    throw new GatewayUnavailableError();
  }

  const header = response.headers.get("x-detected-entities") ?? "";
  const coverage = Number(response.headers.get("x-redact-coverage") ?? "0");
  const reason = (response.headers.get("x-block-reason") ?? "").trim();
  return {
    png: Buffer.from(await response.arrayBuffer()),
    entities: header
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    coverage: Number.isFinite(coverage) ? coverage : 0,
    blocked: response.headers.get("x-image-blocked") === "1",
    blockReason: reason || null,
  };
}
