import "server-only";

import { GoogleGenAI } from "@google/genai";

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

type GenerateGeminiTextOptions = {
  messages: GeminiChatMessage[];
  responseMimeType?: "application/json";
  temperature?: number;
  image?: { mimeType: string; data: string };
};

function getGeminiClient() {
  const apiKey = process.env.GEMINI_API_KEY;

  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not configured.");
  }

  return new GoogleGenAI({ apiKey });
}

function getGeminiModel() {
  const model = process.env.GEMINI_MODEL;

  if (!model) {
    throw new Error("GEMINI_MODEL is not configured.");
  }

  return model;
}

export async function generateGeminiText({ messages, responseMimeType, temperature, image }: GenerateGeminiTextOptions) {
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
  const model = getGeminiModel();
  const maxAttempts = 3;
  let lastError: unknown;

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const response = await client.models.generateContent({
        model,
        contents,
        config: {
          ...(systemInstruction ? { systemInstruction } : {}),
          ...(responseMimeType ? { responseMimeType } : {}),
          ...(temperature === undefined ? {} : { temperature }),
        },
      });
      const text = response.text?.trim();

      if (!text) {
        throw new Error("Gemini returned an empty response.");
      }

      return text;
    } catch (error) {
      lastError = error;
      if (!isRetryableGeminiError(error) || attempt === maxAttempts - 1) {
        break;
      }
      await wait(600 * 2 ** attempt);
    }
  }

  if (isRetryableGeminiError(lastError)) {
    throw new GeminiBusyError();
  }

  throw lastError instanceof Error ? lastError : new Error("Gemini request failed.");
}

function wait(ms: number) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function isRetryableGeminiError(error: unknown) {
  const status = error && typeof error === "object" && "status" in error ? Number((error as { status: unknown }).status) : 0;
  const blob = error instanceof Error ? `${error.message} ${error.name}` : String(error);
  return status === 429 || status === 503 || status === 504 || /unavailable|high demand|overloaded|resource.?exhausted|try again later|timeout|deadline exceeded/i.test(blob);
}