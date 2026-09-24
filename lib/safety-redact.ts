export type ImageBlockReason = "coverage" | "sensitive";

export type ImageRedactResponse = {
  source: "gateway";
  changed: boolean;
  redactedPngBase64: string;
  fields: string[];
  coverage: number;
  blocked: boolean;
  blockReason: ImageBlockReason | null;
};

const IMAGE_FIELD_LABEL: Record<string, string> = {
  PERSON: "姓名",
  SCHOOL: "學校",
  PHONE_NUMBER: "電話",
  LOCATION: "地址",
  EMAIL_ADDRESS: "Email",
  EMAIL: "Email",
  TW_ID: "身分證",
  SCHOOL_CLASS: "班級",
  STUDENT_ID: "學號",
  IG_HANDLE: "IG帳號",
  TW_PASSPORT: "護照",
  TW_DRIVER_LICENSE: "駕照",
  TW_BANK_ACCOUNT: "銀行帳號",
  ORGANIZATION: "機構",
  FACE: "人臉",
};

export function labelsForImageEntities(entities: string[]) {
  const labels: string[] = [];
  const seen = new Set<string>();
  for (const entity of entities) {
    const label = IMAGE_FIELD_LABEL[entity] ?? "其他";
    if (seen.has(label)) {
      continue;
    }
    seen.add(label);
    labels.push(label);
  }
  return labels;
}

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
