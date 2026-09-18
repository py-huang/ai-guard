import "server-only";

import { GoogleGenAI } from "@google/genai";

export type GeminiChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

type GenerateGeminiTextOptions = {
  messages: GeminiChatMessage[];
  responseMimeType?: "application/json";
  temperature?: number;
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

export async function generateGeminiText({ messages, responseMimeType, temperature }: GenerateGeminiTextOptions) {
  const systemInstruction = messages
    .filter((message) => message.role === "system")
    .map((message) => message.content)
    .join("\n\n");
  const contents = messages
    .filter((message) => message.role !== "system")
    .map((message) => ({
      role: message.role === "assistant" ? "model" : "user",
      parts: [{ text: message.content }],
    }));

  if (!contents.length) {
    throw new Error("At least one user or assistant message is required.");
  }

  const response = await getGeminiClient().models.generateContent({
    model: getGeminiModel(),
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
}