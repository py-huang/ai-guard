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
