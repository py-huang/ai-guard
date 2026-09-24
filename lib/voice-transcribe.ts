export async function transcribeVoice(audio: Blob, signal?: AbortSignal) {
  const data = await blobToBase64(audio);
  const response = await fetch("/api/voice/transcribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mimeType: "audio/wav", data }),
    signal,
  });
  const payload = (await response.json()) as { text?: string; error?: string };

  if (!response.ok) {
    throw new Error(payload.error || "現在沒辦法把語音變成文字。");
  }

  return payload.text?.trim() ?? "";
}

function blobToBase64(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = () => reject(new Error("語音讀取失敗。"));
    reader.readAsDataURL(blob);
  });
}
