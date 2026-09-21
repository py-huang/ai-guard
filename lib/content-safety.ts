const BLOCK_RULES: { category: string; needles: string[] }[] = [
  { category: "substance", needles: ["毒品", "買酒", "香菸", "哪裡買"] },
  { category: "self-harm", needles: ["自殺", "不想活", "傷害自己"] },
  { category: "violence", needles: ["殺人", "怎麼打人", "武器"] },
  { category: "adult", needles: ["色情", "裸"] },
  { category: "hate", needles: ["去死", "歧視"] },
  { category: "gambling", needles: ["賭博", "賭錢"] },
  { category: "deepfake", needles: ["換臉", "證件照", "身分證照片"] },
];

export function classifyUnsafeText(text: string) {
  const normalized = text.toLowerCase();
  return BLOCK_RULES.find((rule) => rule.needles.some((needle) => normalized.includes(needle.toLowerCase()))) ?? null;
}

export const CHILD_BLOCK_REPLY =
  "這個問題我們先不要繼續。如果有不舒服的事，可以跟信任的大人說。我們可以改聊功課、自然或故事。";
