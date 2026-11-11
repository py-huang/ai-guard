import { GeminiBusyError, transcribeGeminiAudio } from "@/lib/gemini";
import { getConfig } from "@/lib/server/config";
import { enforceRateLimit, jsonError, PayloadTooLargeError, readJsonBody, tooLargeResponse } from "@/lib/server/http";
import { logError } from "@/lib/server/log";

type TranscribeRequest = {
  mimeType?: unknown;
  data?: unknown;
};

export async function POST(request: Request) {
  const limited = enforceRateLimit(request, "voice");
  if (limited) {
    return limited;
  }

  const { limits } = getConfig();
  let body: TranscribeRequest | null;
  try {
    body = await readJsonBody<TranscribeRequest>(request, limits.audioBodyBytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return tooLargeResponse();
    }
    throw error;
  }

  const data = typeof body?.data === "string" ? body.data.trim() : "";
  const mimeType = typeof body?.mimeType === "string" && body.mimeType.trim() ? body.mimeType.trim().slice(0, 64) : "audio/wav";

  if (!data) {
    return jsonError("沒有收到語音。", 400);
  }
  if (data.length > limits.maxAudioBase64Chars) {
    return tooLargeResponse();
  }

  try {
    const text = await transcribeGeminiAudio({ mimeType, data });
    return Response.json({ text }, { headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    logError("voice_transcribe_failed", error);
    if (error instanceof GeminiBusyError) {
      return jsonError(error.message, 503, { retryable: true });
    }
    return jsonError("現在沒辦法把語音變成文字。", 502);
  }
}
