import type { PiiHit, PiiPreview } from "@/lib/pii-preview";

export type SafetyInspectResponse = {
  source: "gateway" | "local";
  blocked: boolean;
  childMessage: string | null;
  processedText: string;
  hits: PiiHit[];
  safeText: string;
};

function highlight(text: string, values: string[]): PiiPreview["highlighted"] {
  if (values.length === 0) {
    return [{ text, sensitive: false }];
  }

  const escaped = values.map((value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const splitter = new RegExp(`(${escaped.join("|")})`, "g");
  return text.split(splitter).filter(Boolean).map((part) => ({
    text: part,
    sensitive: values.includes(part),
  }));
}

export function toPiiPreview(text: string, result: SafetyInspectResponse): PiiPreview {
  return {
    hits: result.hits,
    safeText: result.safeText,
    highlighted: highlight(text, result.hits.map((hit) => hit.value)),
  };
}

export function maskPiiOriginal(text: string, hits: PiiHit[]): string | undefined {
  if (!text || hits.length === 0 || hits.some((hit) => !hit.value || !text.includes(hit.value))) {
    return undefined;
  }

  const spans: { start: number; end: number }[] = [];
  for (const { value } of hits) {
    let start = text.indexOf(value);
    while (start !== -1) {
      spans.push({ start, end: start + value.length });
      start = text.indexOf(value, start + 1);
    }
  }
  spans.sort((a, b) => a.start - b.start || b.end - a.end);

  let masked = "";
  let position = 0;
  for (let index = 0; index < spans.length; index++) {
    const span = spans[index];
    let end = span.end;
    while (index + 1 < spans.length && spans[index + 1].start <= end) {
      end = Math.max(end, spans[++index].end);
    }
    masked += `${text.slice(position, span.start)}[已遮蔽]`;
    position = end;
  }
  return masked + text.slice(position);
}

export async function inspectSafety(sessionId: string, text: string) {
  const response = await fetch("/api/safety/inspect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sessionId, text }),
  });
  const data = (await response.json()) as SafetyInspectResponse & { error?: string };
  if (!response.ok) {
    throw new Error(data.error || "現在沒辦法檢查這句話。");
  }
  return data;
}
