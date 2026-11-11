import { isGatewayReady } from "@/lib/gateway";
import { getConfig } from "@/lib/server/config";

/** Readiness: the web tier can actually serve a child (gateway reachable, model key set). */
export async function GET() {
  const config = getConfig();
  const gateway = await isGatewayReady();
  const model = Boolean(config.gemini.apiKey && config.gemini.primaryModel);
  const ready = gateway && model;

  return Response.json(
    { status: ready ? "ready" : "not_ready", checks: { gateway, model } },
    { status: ready ? 200 : 503, headers: { "Cache-Control": "no-store" } },
  );
}
