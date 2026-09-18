import { generateWritingPlan, type GenerateWritingResponse } from "@/lib/writing";

type GenerateRequest = {
  input?: unknown;
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as GenerateRequest | null;
  const input = typeof body?.input === "string" ? body.input.trim() : "";

  if (!input) {
    return Response.json({ error: "請輸入想寫的主題。" }, { status: 400 });
  }

  try {
    const plan = await generateWritingPlan(input);
    const response: GenerateWritingResponse = {
      ...plan,
      theme: "writing",
      theme_id: crypto.randomUUID(),
    };

    return Response.json(response);
  } catch (error) {
    console.error("Writing plan generation failed", error);
    return Response.json({ error: "暫時無法建立寫作計畫。" }, { status: 502 });
  }
}