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
  a: "ㄧㄚ",
  ie: "ㄧㄝ",
  e: "ㄧㄝ",
  iao: "ㄧㄠ",
  ao: "ㄧㄠ",
  iu: "ㄧㄡ",
  ou: "ㄧㄡ",
  ian: "ㄧㄢ",
  an: "ㄧㄢ",
  in: "ㄧㄣ",
  en: "ㄧㄣ",
  iang: "ㄧㄤ",
  ang: "ㄧㄤ",
  ing: "ㄧㄥ",
  eng: "ㄧㄥ",
  u: "ㄩ",
  ue: "ㄩㄝ",
  uan: "ㄩㄢ",
  un: "ㄩㄣ",
  ong: "ㄩㄥ",
};

const W_FINALS: Record<string, string> = {
  u: "ㄨ",
  ua: "ㄨㄚ",
  a: "ㄨㄚ",
  uo: "ㄨㄛ",
  o: "ㄨㄛ",
  uai: "ㄨㄞ",
  ai: "ㄨㄞ",
  ui: "ㄨㄟ",
  ei: "ㄨㄟ",
  uan: "ㄨㄢ",
  an: "ㄨㄢ",
  un: "ㄨㄣ",
  en: "ㄨㄣ",
  uang: "ㄨㄤ",
  ang: "ㄨㄤ",
  eng: "ㄨㄥ",
  ong: "ㄨㄥ",
};

const RETROFLEX = new Set(["zh", "ch", "sh", "r", "z", "c", "s"]);

export type ZhuyinPart = {
  text: string;
  zhuyin: string | null;
};

export type ZhuyinGlyphs = {
  letters: string[];
  tone: string | null;
};

const SIDE_TONES = new Set(["ˊ", "ˇ", "ˋ"]);

export function splitZhuyin(zhuyin: string): ZhuyinGlyphs {
  const letters: string[] = [];
  let tone: string | null = null;
  for (const mark of zhuyin) {
    if (SIDE_TONES.has(mark)) {
      tone = mark;
      continue;
    }
    letters.push(mark);
  }
  return { letters, tone };
}

type PinyinToken = {
  origin: string;
  initial: string;
  final: string;
  num: number;
  isZh: boolean;
};

const TAIWAN_READINGS: Record<string, string> = {
  們: "˙ㄇㄣ",
  吗: "˙ㄇㄚ",
  嗎: "˙ㄇㄚ",
  麼: "˙ㄇㄜ",
  么: "˙ㄇㄜ",
  嗨: "ㄏㄞ",
};

export function toZhuyinParts(text: string): ZhuyinPart[] {
  const source = text || "";
  if (!source) return [];

  const tokens = pinyin(source, {
    type: "all",
    traditional: true,
    nonZh: "consecutive",
    toneSandhi: true,
  }) as PinyinToken[];

  return tokens.map((token) => {
    if (!token.isZh) {
      return { text: token.origin, zhuyin: null };
    }
    const fixed = TAIWAN_READINGS[token.origin];
    if (fixed) {
      return { text: token.origin, zhuyin: fixed };
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
    .normalize("NFKD")
    .replace(/[uü][\u0308]/gi, "v")
    .replace(/\p{M}/gu, "")
    .replaceAll("ü", "v")
    .replaceAll("Ü", "v")
    .toLowerCase();
}

const JQX = new Set(["j", "q", "x"]);
const JQX_U: Record<string, string> = {
  u: "v",
  ue: "ve",
  uan: "van",
  un: "vn",
};

function toBopomofoLetters(initial: string, final: string): string {
  if (initial === "y") return Y_FINALS[final] ?? FINALS[final] ?? "";
  if (initial === "w") return W_FINALS[final] ?? FINALS[final] ?? "";
  if (RETROFLEX.has(initial) && final === "i") return INITIALS[initial] ?? "";
  const tailKey = JQX.has(initial) ? (JQX_U[final] ?? final) : final;
  const head = INITIALS[initial] ?? "";
  const tail = FINALS[tailKey] ?? "";
  return `${head}${tail}`;
}
