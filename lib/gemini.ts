import "server-only";

import { GoogleGenAI } from "@google/genai";

import { getConfig } from "@/lib/server/config";
import { logError } from "@/lib/server/log";

export const GEMINI_BUSY_MESSAGE = "老師現在有點忙，請稍等再按一次「送出」。過幾秒通常就好了。";

export class GeminiBusyError extends Error {
  constructor() {
    super(GEMINI_BUSY_MESSAGE);
    this.name = "GeminiBusyError";
  }
}

export type GeminiChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

export type GroundingSource = {
  title: string;
  uri: string;
};

export type GenerateGeminiResult = {
  text: string;
  sources: GroundingSource[];
  searchQueries: string[];
};

type GenerateGeminiTextOptions = {
  messages: GeminiChatMessage[];
  responseMimeType?: "application/json";
  temperature?: number;
  image?: { mimeType: string; data: string };
  googleSearch?: boolean;
};

let cachedClient: { apiKey: string; client: GoogleGenAI } | null = null;

function getGeminiClient() {
  const { apiKey } = getConfig().gemini;

  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not configured.");
  }

  if (cachedClient?.apiKey !== apiKey) {
    cachedClient = { apiKey, client: new GoogleGenAI({ apiKey }) };
  }
  return cachedClient.client;
}

function getGeminiModels() {
  const { primaryModel, fallbackModels } = getConfig().gemini;
  const models = [primaryModel, ...fallbackModels].filter((item, index, list): item is string => Boolean(item) && list.indexOf(item) === index);
  if (!models.length) {
    throw new Error("GEMINI_MODEL is not configured.");
  }
  return models;
}

export async function generateGeminiText({ messages, responseMimeType, temperature, image, googleSearch }: GenerateGeminiTextOptions): Promise<GenerateGeminiResult> {
  const systemInstruction = messages
    .filter((message) => message.role === "system")
    .map((message) => message.content)
    .join("\n\n");
  const contents = messages
    .filter((message) => message.role !== "system")
    .map((message, index, list) => {
      const isLastUser = message.role === "user" && index === list.length - 1;
      const parts: Array<{ text: string } | { inlineData: { mimeType: string; data: string } }> = [{ text: message.content }];
      if (isLastUser && image?.data) {
        parts.push({ inlineData: { mimeType: image.mimeType || "image/png", data: image.data } });
      }
      return {
        role: message.role === "assistant" ? "model" : "user",
        parts,
      };
    });

  if (!contents.length) {
    throw new Error("At least one user or assistant message is required.");
  }

  const client = getGeminiClient();
  const models = getGeminiModels();
  const useSearch = Boolean(googleSearch && !responseMimeType);
  let lastError: unknown;

  const { timeoutMs, searchTimeoutMs } = getConfig().gemini;

  const requestOnce = async (model: string, search: boolean, signal: AbortSignal) => {
    const response = await client.models.generateContent({
      model,
      contents,
      config: {
        abortSignal: signal,
        ...(systemInstruction ? { systemInstruction } : {}),
        ...(responseMimeType ? { responseMimeType } : {}),
        ...(temperature === undefined ? {} : { temperature }),
        ...(search ? { tools: [{ googleSearch: {} }] } : {}),
      },
    });
    const text = response.text?.trim();
    if (!text) {
      throw new Error("Gemini returned an empty response.");
    }
    return { text, ...extractGrounding(response) };
  };

  for (const [index, model] of models.entries()) {
    try {
      return await withDeadline(useSearch ? searchTimeoutMs : timeoutMs, (signal) => requestOnce(model, useSearch, signal));
    } catch (error) {
      lastError = error;
      logGeminiFailure(model, useSearch, error);
      if (useSearch) {
        try {
          return await withDeadline(timeoutMs, (signal) => requestOnce(model, false, signal));
        } catch (fallbackError) {
          lastError = fallbackError;
          logGeminiFailure(model, false, fallbackError);
        }
      }
    }

    // Overloaded upstreams recover faster if we do not hammer the next model instantly.
    if (index < models.length - 1 && isRetryableGeminiError(lastError)) {
      await wait(backoffMs(index));
    }
  }

  if (isRetryableGeminiError(lastError)) {
    const busy = new GeminiBusyError();
    busy.cause = lastError;
    throw busy;
  }

  throw lastError instanceof Error ? lastError : new Error("Gemini request failed.");
}

function getTranscribeModel() {
  return getConfig().gemini.transcribeModel;
}

function geminiAudioMime(mimeType: string) {
  const base = mimeType.split(";")[0]?.trim().toLowerCase() || "audio/wav";
  if (base === "audio/wav" || base === "audio/mpeg" || base === "audio/mp3" || base === "audio/mp4" || base === "audio/aac" || base === "audio/ogg" || base === "audio/flac") {
    return base;
  }
  return "audio/wav";
}

export async function transcribeGeminiAudio(audio: { mimeType: string; data: string }) {
  const client = getGeminiClient();
  const model = getTranscribeModel();
  const maxAttempts = 3;
  let lastError: unknown;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      return await withDeadline(getConfig().gemini.transcribeTimeoutMs, async (signal) => {
        const response = await client.models.generateContent({
          model,
          contents: [
            {
              role: "user",
              parts: [{ inlineData: { mimeType: geminiAudioMime(audio.mimeType), data: audio.data } }],
            },
          ],
          config: {
            abortSignal: signal,
            temperature: 0,
            audioTranscriptionConfig: {
              languageCodes: ["zh-TW"],
              mode: "SMART",
            },
          } as Record<string, unknown>,
        });
        return readTranscript(response);
      });
    } catch (error) {
      lastError = error;
      logGeminiFailure(model, false, error);
      if (!isRetryableGeminiError(error) || attempt === maxAttempts - 1) {
        break;
      }
      await wait(backoffMs(attempt));
    }
  }

  if (isRetryableGeminiError(lastError)) {
    throw new GeminiBusyError();
  }

  throw lastError instanceof Error ? lastError : new Error("Gemini request failed.");
}

function readTranscript(response: {
  text?: string;
  candidates?: Array<{
    content?: {
      parts?: Array<{ text?: string; thought?: boolean; audioTranscription?: { text?: string } }>;
    };
  }>;
}) {
  const parts = response.candidates?.[0]?.content?.parts ?? [];
  const spoken = parts
    .map((part) => part.audioTranscription?.text?.trim() ?? "")
    .filter(Boolean)
    .join("");
  if (spoken) {
    return spoken.trim();
  }
  const written = parts
    .filter((part) => part.thought !== true)
    .map((part) => part.text?.trim() ?? "")
    .filter(Boolean)
    .join("");
  return written.trim() || response.text?.trim() || "";
}

function extractGrounding(response: {
  candidates?: Array<{
    groundingMetadata?: {
      webSearchQueries?: string[];
      groundingChunks?: Array<{ web?: { uri?: string; title?: string } }>;
    };
  }>;
}): { sources: GroundingSource[]; searchQueries: string[] } {
  const meta = response.candidates?.[0]?.groundingMetadata;
  const seen = new Set<string>();
  const sources: GroundingSource[] = [];
  for (const chunk of meta?.groundingChunks ?? []) {
    const uri = chunk.web?.uri?.trim();
    if (!uri || seen.has(uri)) {
      continue;
    }
    seen.add(uri);
    const title = chunk.web?.title?.trim() || safeHostTitle(uri);
    sources.push({ title, uri });
  }
  return {
    sources,
    searchQueries: (meta?.webSearchQueries ?? []).filter((query) => typeof query === "string" && query.trim()),
  };
}

function safeHostTitle(uri: string) {
  try {
    return new URL(uri).hostname.replace(/^www\./, "");
  } catch {
    return "網路資料";
  }
}

/**
 * Runs `run` with a deadline that actually cancels the HTTP request, so a slow model
 * does not keep burning a socket (and quota) after we have already given up on it.
 */
async function withDeadline<T>(ms: number, run: (signal: AbortSignal) => Promise<T>) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error("timeout")), ms);
  try {
    return await run(controller.signal);
  } finally {
    clearTimeout(timer);
  }
}

/** 250ms, 500ms, 1s ... capped at 2s, with up to 20% jitter. */
function backoffMs(attempt: number) {
  const base = Math.min(250 * 2 ** attempt, 2_000);
  return Math.round(base * (1 + Math.random() * 0.2));
}

function wait(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function logGeminiFailure(model: string, googleSearch: boolean, error: unknown) {
  const status = error && typeof error === "object" && "status" in error ? Number((error as { status: unknown }).status) : 0;
  logError("gemini_generate_failed", error, { model, googleSearch, status });
}

function isRetryableGeminiError(error: unknown) {
  const status = error && typeof error === "object" && "status" in error ? Number((error as { status: unknown }).status) : 0;
  const blob = error instanceof Error ? `${error.message} ${error.name}` : String(error);
  return status === 429 || status === 503 || status === 504 || /unavailable|high demand|overloaded|resource.?exhausted|try again later|timeout|aborted|abort|deadline exceeded|did not match the expected pattern/i.test(blob);
}