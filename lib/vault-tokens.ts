const CHILD_TOKEN_LABEL: Record<string, string> = {
  PERSON: "這位小朋友",
  SCHOOL: "學校",
  SCHOOL_CLASS: "班級",
  STUDENT_ID: "學號",
  IG_HANDLE: "這個帳號",
  PHONE_NUMBER: "電話",
  LOCATION: "這個城市",
  EMAIL_ADDRESS: "信箱",
  EMAIL: "信箱",
  TW_ID: "證件",
  TW_PASSPORT: "護照",
  TW_DRIVER_LICENSE: "駕照",
  TW_BANK_ACCOUNT: "帳號",
  ORGANIZATION: "機構",
  FACE: "人臉",
};

const TOKEN_RE = /<([A-Z][A-Z0-9]*)_\d+>/g;

export function replaceVaultTokensForChild(text: string) {
  return text
    .replace(TOKEN_RE, (_match, entityType: string) => CHILD_TOKEN_LABEL[entityType] ?? "這筆資料")
    .replace(/\s{2,}/g, " ")
    .trim();
}
