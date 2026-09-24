import { GeminiBusyError, transcribeGeminiAudio } from "@/lib/gemini";

type TranscribeRequest = {
  mimeType?: unknown;
  data?: unknown;
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as TranscribeRequest | null;
  const data = typeof body?.data === "string" ? body.data.trim() : "";
  const mimeType = typeof body?.mimeType === "string" && body.mimeType.trim() ? body.mimeType.trim() : "audio/wav";

  if (!data) {
    return Response.json({ error: "沒有收到語音。" }, { status: 400 });
  }

  try {
    const text = await transcribeGeminiAudio({ mimeType, data });
    return Response.json({ text });
  } catch (error) {
    console.error("Voice transcribe failed", error);
    if (error instanceof GeminiBusyError) {
      return Response.json({ error: error.message, retryable: true }, { status: 503 });
    }
    return Response.json({ error: "現在沒辦法把語音變成文字。" }, { status: 502 });
  }
}
