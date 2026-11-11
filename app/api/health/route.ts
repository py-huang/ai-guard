/** Liveness: the web process is up. Does not touch any dependency. */
export function GET() {
  return Response.json({ status: "ok" }, { headers: { "Cache-Control": "no-store" } });
}
