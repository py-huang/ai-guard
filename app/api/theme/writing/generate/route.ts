import { getMockWritingPlan, getWritingSystemPrompt, type GenerateWritingResponse } from "@/lib/writing";

type GenerateRequest = {
  input?: unknown;
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as GenerateRequest | null;
  const input = typeof body?.input === "string" ? body.input.trim() : "";

  if (!input) {
    return Response.json({ error: "請輸入想寫的主題。" }, { status: 400 });
  }

  const plan = getMockWritingPlan(input);
  const response: GenerateWritingResponse = {
    ...plan,
    theme: "writing",
    theme_id: crypto.randomUUID(),
    init_question: input.includes("暑假")
      ? "暑假裡最想寫哪一件事？一次只做一步。"
      : `關於「${input}」，最想寫哪一件事？一次只做一步。`,
  };

  getWritingSystemPrompt("chat");
  return Response.json(response);
}