import { pinyin } from "pinyin-pro";

const TONE_MARKS = { 0: "˙", 2: "ˊ", 3: "ˇ", 4: "ˋ" } as const;

const INITIALS: Record<string, string> = {
  b: "ㄅ",
  p: "ㄆ",
  m: "ㄇ",
  f: "ㄈ",
  d: "ㄉ",
  t: "ㄊ",
  n: "ㄋ",
  l: "ㄌ",
  g: "ㄍ",
  k: "ㄎ",
  h: "ㄏ",
  j: "ㄐ",
  q: "ㄑ",
  x: "ㄒ",
  zh: "ㄓ",
  ch: "ㄔ",
  sh: "ㄕ",
  r: "ㄖ",
  z: "ㄗ",
  c: "ㄘ",
  s: "ㄙ",
};

const FINALS: Record<string, string> = {
  a: "ㄚ",
  o: "ㄛ",
  e: "ㄜ",
  ei: "ㄟ",
  ai: "ㄞ",
  ao: "ㄠ",
  ou: "ㄡ",
  an: "ㄢ",
  en: "ㄣ",
  ang: "ㄤ",
  eng: "ㄥ",
  er: "ㄦ",
  i: "ㄧ",
  ia: "ㄧㄚ",
  ie: "ㄧㄝ",
  iao: "ㄧㄠ",
  iu: "ㄧㄡ",
  ian: "ㄧㄢ",
  in: "ㄧㄣ",
  iang: "ㄧㄤ",
  ing: "ㄧㄥ",
  u: "ㄨ",
  ua: "ㄨㄚ",
  uo: "ㄨㄛ",
  uai: "ㄨㄞ",
  ui: "ㄨㄟ",
  uan: "ㄨㄢ",
  un: "ㄨㄣ",
  uang: "ㄨㄤ",
  ong: "ㄨㄥ",
  v: "ㄩ",
  ve: "ㄩㄝ",
  ue: "ㄩㄝ",
  van: "ㄩㄢ",
  vn: "ㄩㄣ",
  iong: "ㄩㄥ",
};

const Y_FINALS: Record<string, string> = {
  i: "ㄧ",
  ia: "ㄧㄚ",
  ie: "ㄧㄝ",
  iao: "ㄧㄠ",
  iu: "ㄧㄡ",
  ian: "ㄧㄢ",
  in: "ㄧㄣ",
  iang: "ㄧㄤ",
  ing: "ㄧㄥ",
  u: "ㄩ",
  ue: "ㄩㄝ",
  uan: "ㄩㄢ",
  un: "ㄩㄣ",
  ong: "ㄩㄥ",
};

const W_FINALS: Record<string, string> = {
  u: "ㄨ",
  ua: "ㄨㄚ",
  uo: "ㄨㄛ",
  o: "ㄨㄛ",
  uai: "ㄨㄞ",
  ui: "ㄨㄟ",
  ei: "ㄨㄟ",
  uan: "ㄨㄢ",
  un: "ㄨㄣ",
  uang: "ㄨㄤ",
  eng: "ㄨㄥ",
};

const RETROFLEX = new Set(["zh", "ch", "sh", "r", "z", "c", "s"]);

export type ZhuyinPart = {
  text: string;
  zhuyin: string | null;
};

type PinyinToken = {
  origin: string;
  initial: string;
  final: string;
  num: number;
  isZh: boolean;
};

export function toZhuyinParts(text: string): ZhuyinPart[] {
  const source = text || "";
  if (!source) return [];

  const tokens = pinyin(source, {
    type: "all",
    traditional: true,
    nonZh: "consecutive",
    toneSandhi: false,
  }) as PinyinToken[];

  return tokens.map((token) => {
    if (!token.isZh) {
      return { text: token.origin, zhuyin: null };
    }
    const letters = toBopomofoLetters(token.initial, stripTone(token.final));
    return {
      text: token.origin,
      zhuyin: letters ? withTone(letters, token.num) : null,
    };
  });
}

function withTone(letters: string, tone: number): string {
  if (tone === 0) return `˙${letters}`;
  const mark = TONE_MARKS[tone as 2 | 3 | 4];
  return mark ? `${letters}${mark}` : letters;
}

function stripTone(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replaceAll("ü", "v")
    .replaceAll("Ü", "v")
    .toLowerCase();
}

function toBopomofoLetters(initial: string, final: string): string {
  if (initial === "y") return Y_FINALS[final] ?? FINALS[final] ?? "";
  if (initial === "w") return W_FINALS[final] ?? FINALS[final] ?? "";
  if (RETROFLEX.has(initial) && final === "i") return INITIALS[initial] ?? "";
  const head = INITIALS[initial] ?? "";
  const tail = FINALS[final] ?? "";
  return `${head}${tail}`;
}
