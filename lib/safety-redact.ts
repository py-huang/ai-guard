export type ImageRedactResponse = {
  source: "gateway";
  changed: boolean;
  redactedPngBase64: string;
};

export async function redactImage(sessionId: string, file: File) {
  const body = new FormData();
  body.append("sessionId", sessionId);
  body.append("file", file);

  const response = await fetch("/api/safety/redact-image", {
    method: "POST",
    body,
  });
  const data = (await response.json()) as ImageRedactResponse & { error?: string };
  if (!response.ok) {
    throw new Error(data.error || "現在沒辦法檢查這張圖片。");
  }
  return data;
}

export function pngDataUrl(base64: string) {
  return `data:image/png;base64,${base64}`;
}
