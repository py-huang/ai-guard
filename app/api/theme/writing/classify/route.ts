import { classifyWritingIntent } from "@/lib/writing";

type ClassifyRequest = {
  input?: unknown;
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as ClassifyRequest | null;
  const input = typeof body?.input === "string" ? body.input.trim() : "";

  if (!input) {
    return Response.json({ error: "請輸入想問的內容。" }, { status: 400 });
  }

  try {
    return Response.json(await classifyWritingIntent(input));
  } catch (error) {
    console.error("Writing intent classification failed", error);
    return Response.json({ error: "暫時無法判斷主題。" }, { status: 502 });
  }
}