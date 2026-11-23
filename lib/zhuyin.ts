import { pinyin } from "pinyin-pro";
import { T2S_SIMPLIFIED, T2S_TRADITIONAL } from "./t2s-map";

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

const T2S = new Map<string, string>();
{
  const from = [...T2S_TRADITIONAL];
  const to = [...T2S_SIMPLIFIED];
  from.forEach((ch, i) => T2S.set(ch, to[i]));
}

// pinyin-pro's word dictionary only knows simplified text. Given traditional input it
// silently drops to per-character readings (長大 -> chang2, 音樂 -> le4), so we hand it
// the simplified form. The map is one character to one character, so offsets still line up.
function toSimplified(text: string): string {
  let out = "";
  for (const ch of text) out += T2S.get(ch) ?? ch;
  return out;
}

// Whole-word readings for Taiwan Mandarin, one syllable per space. Keys are traditional.
// Longest match wins and beats both pinyin-pro and the per-character table above.
// Only add words whose reading we are sure of (self-written, not copied from a dictionary).
const PHRASE_READINGS: Record<string, string> = {
  // Reduplicated kin words and 疊詞: the second syllable is light.
  媽媽: "ㄇㄚ ˙ㄇㄚ",
  爸爸: "ㄅㄚˋ ˙ㄅㄚ",
  哥哥: "ㄍㄜ ˙ㄍㄜ",
  姐姐: "ㄐㄧㄝˇ ˙ㄐㄧㄝ",
  姊姊: "ㄐㄧㄝˇ ˙ㄐㄧㄝ",
  弟弟: "ㄉㄧˋ ˙ㄉㄧ",
  妹妹: "ㄇㄟˋ ˙ㄇㄟ",
  爺爺: "ㄧㄝˊ ˙ㄧㄝ",
  奶奶: "ㄋㄞˇ ˙ㄋㄞ",
  叔叔: "ㄕㄨ ˙ㄕㄨ",
  姑姑: "ㄍㄨ ˙ㄍㄨ",
  舅舅: "ㄐㄧㄡˋ ˙ㄐㄧㄡ",
  婆婆: "ㄆㄛˊ ˙ㄆㄛ",
  公公: "ㄍㄨㄥ ˙ㄍㄨㄥ",
  寶寶: "ㄅㄠˇ ˙ㄅㄠ",
  娃娃: "ㄨㄚˊ ˙ㄨㄚ",
  星星: "ㄒㄧㄥ ˙ㄒㄧㄥ",
  謝謝: "ㄒㄧㄝˋ ˙ㄒㄧㄝ",
  看看: "ㄎㄢˋ ˙ㄎㄢ",
  試試: "ㄕˋ ˙ㄕˋ",
  想想: "ㄒㄧㄤˇ ˙ㄒㄧㄤ",
  玩玩: "ㄨㄢˊ ˙ㄨㄢ",
  聽聽: "ㄊㄧㄥ ˙ㄊㄧㄥ",
  說說: "ㄕㄨㄛ ˙ㄕㄨㄛ",
  問問: "ㄨㄣˋ ˙ㄨㄣ",
  走走: "ㄗㄡˇ ˙ㄗㄡ",
  // Common light-tone words.
  東西: "ㄉㄨㄥ ˙ㄒㄧ",
  喜歡: "ㄒㄧˇ ˙ㄏㄨㄢ",
  漂亮: "ㄆㄧㄠˋ ˙ㄌㄧㄤ",
  休息: "ㄒㄧㄡ ˙ㄒㄧ",
  認識: "ㄖㄣˋ ˙ㄕˋ",
  事情: "ㄕˋ ˙ㄑㄧㄥ",
  清楚: "ㄑㄧㄥ ˙ㄔㄨ",
  舒服: "ㄕㄨ ˙ㄈㄨ",
  眼睛: "ㄧㄢˇ ˙ㄐㄧㄥ",
  頭髮: "ㄊㄡˊ ˙ㄈㄚ",
  衣服: "ㄧ ˙ㄈㄨ",
  名字: "ㄇㄧㄥˊ ˙ㄗ",
  時候: "ㄕˊ ˙ㄏㄡ",
  先生: "ㄒㄧㄢ ˙ㄕㄥ",
  耳朵: "ㄦˇ ˙ㄉㄨㄛ",
  地方: "ㄉㄧˋ ˙ㄈㄤ",
  一步一步: "ㄧˊ ㄅㄨˋ ㄧˊ ㄅㄨˋ",
  // Taiwan-specific readings.
  垃圾: "ㄌㄜˋ ㄙㄜˋ",
  // 長 as "grow / senior".
  長大: "ㄓㄤˇ ㄉㄚˋ",
  長高: "ㄓㄤˇ ㄍㄠ",
  成長: "ㄔㄥˊ ㄓㄤˇ",
  生長: "ㄕㄥ ㄓㄤˇ",
  校長: "ㄒㄧㄠˋ ㄓㄤˇ",
  家長: "ㄐㄧㄚ ㄓㄤˇ",
  班長: "ㄅㄢ ㄓㄤˇ",
  隊長: "ㄉㄨㄟˋ ㄓㄤˇ",
  組長: "ㄗㄨˇ ㄓㄤˇ",
  市長: "ㄕˋ ㄓㄤˇ",
  長輩: "ㄓㄤˇ ㄅㄟˋ",
  // 行 / 還 / 為 / 著 / 覺 / 樂 words.
  銀行: "ㄧㄣˊ ㄏㄤˊ",
  行業: "ㄏㄤˊ ㄧㄝˋ",
  因為: "ㄧㄣ ㄨㄟˋ",
  為什麼: "ㄨㄟˋ ㄕㄣˊ ˙ㄇㄜ",
  為了: "ㄨㄟˋ ˙ㄌㄜ",
  為何: "ㄨㄟˋ ㄏㄜˊ",
  還錢: "ㄏㄨㄢˊ ㄑㄧㄢˊ",
  還書: "ㄏㄨㄢˊ ㄕㄨ",
  還給: "ㄏㄨㄢˊ ㄍㄟˇ",
  歸還: "ㄍㄨㄟ ㄏㄨㄢˊ",
  著急: "ㄓㄠ ㄐㄧˊ",
  睡著: "ㄕㄨㄟˋ ㄓㄠˊ",
  著名: "ㄓㄨˋ ㄇㄧㄥˊ",
  睡覺: "ㄕㄨㄟˋ ㄐㄧㄠˋ",
  音樂: "ㄧㄣ ㄩㄝˋ",
  快樂: "ㄎㄨㄞˋ ㄌㄜˋ",
};

const MAX_PHRASE_LENGTH = Math.max(...Object.keys(PHRASE_READINGS).map((key) => key.length));

// Characters that follow 還 when it means "still / also" (ㄏㄞˊ) rather than "give back" (ㄏㄨㄢˊ).
const HAI_FOLLOWERS = new Set(["有", "是", "要", "好", "沒", "在", "能", "會", "可", "很", "不", "想", "得", "比", "更"]);
// 個 stays heavy (ㄍㄜˋ) in these words; everywhere else after another character it is a light measure word.
const GE_HEAVY_NEXT = new Set(["人", "別", "性", "體", "案", "頭", "數", "子"]);
const GE_NUMERALS = new Set(["一", "二", "兩", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千", "幾", "這", "那", "哪", "每", "多", "整", "半", "某", "另", "各", "單"]);
const ZHE_PREFIXES = new Set(["看", "拿", "笑", "吃", "走", "說", "玩", "等", "想", "跟", "抱", "站", "坐", "躺", "帶", "聽", "唱", "跑", "握", "背", "穿", "戴", "含", "拉", "推", "蓋", "放", "接", "忙", "活", "向", "沿", "順"]);

// undefined = not a Chinese token (no zhuyin slot), null = Chinese but unmappable.
// Verbs that take a complement with light-tone 得 (跑得快, 說得好). Others keep pinyin-pro's reading (得到 ㄉㄜˊ).
const DE_VERBS = new Set(["跑", "走", "說", "講", "跳", "飛", "唱", "寫", "畫", "做", "玩", "吃", "看", "長", "變", "笑", "哭", "睡", "打", "洗", "開", "想", "學", "讀", "游"]);

type Syllable = string | null | undefined;

function isHan(char: string | undefined): boolean {
  return !!char && /\p{Script=Han}/u.test(char);
}

// Context rules for single characters whose reading depends on their neighbours.
function applyContextRules(chars: string[], syllables: Syllable[]): void {
  for (let i = 0; i < chars.length; i += 1) {
    const char = chars[i];
    const prev = chars[i - 1];
    const next = chars[i + 1];
    if (syllables[i] === undefined) continue;

    if (char === "個") {
      if (GE_HEAVY_NEXT.has(next ?? "") && !GE_NUMERALS.has(prev ?? "")) {
        syllables[i] = "ㄍㄜˋ";
      } else if (isHan(prev)) {
        syllables[i] = "˙ㄍㄜ";
      }
    } else if (char === "著" && ZHE_PREFIXES.has(prev ?? "")) {
      syllables[i] = "˙ㄓㄜ";
    } else if (char === "得" && DE_VERBS.has(prev ?? "") && next !== "到") {
      syllables[i] = "˙ㄉㄜ";
    } else if (char === "還") {
      syllables[i] = HAI_FOLLOWERS.has(next ?? "") ? "ㄏㄞˊ" : syllables[i];
    } else if (char === "為" && ["什", "了", "何", "啥", "甚", "誰"].includes(next ?? "")) {
      syllables[i] = "ㄨㄟˋ";
    }
  }
}

export function toZhuyinParts(text: string): ZhuyinPart[] {
  const source = text || "";
  if (!source) return [];

  const tokens = pinyin(toSimplified(source), {
    type: "all",
    nonZh: "consecutive",
    toneSandhi: true,
  }) as PinyinToken[];

  // Rebuild per-token original (traditional) text; the simplified string has the same length.
  const originals: string[] = [];
  const syllables: Syllable[] = [];
  let offset = 0;
  for (const token of tokens) {
    const original = source.slice(offset, offset + token.origin.length);
    offset += token.origin.length;
    originals.push(original);
    if (!token.isZh) {
      syllables.push(undefined);
      continue;
    }
    const letters = toBopomofoLetters(token.initial, stripTone(token.final));
    syllables.push(letters ? withTone(letters, token.num) : null);
  }

  // Phrase table: longest match over consecutive single-character Chinese tokens.
  for (let i = 0; i < originals.length; i += 1) {
    if (syllables[i] === undefined) continue;
    for (let length = Math.min(MAX_PHRASE_LENGTH, originals.length - i); length >= 2; length -= 1) {
      const slice = originals.slice(i, i + length);
      if (slice.some((part, index) => part.length !== 1 || syllables[i + index] === undefined)) continue;
      const reading = PHRASE_READINGS[slice.join("")];
      if (!reading) continue;
      reading.split(" ").forEach((syllable, index) => {
        syllables[i + index] = syllable;
      });
      i += length - 1;
      break;
    }
  }

  // Context rules and per-character Taiwan readings only touch characters the phrase table left alone.
  const chars = originals.map((part) => (part.length === 1 ? part : ""));
  applyContextRules(chars, syllables);

  return originals.map((original, index) => {
    if (syllables[index] === undefined) return { text: original, zhuyin: null };
    const fixed = TAIWAN_READINGS[original];
    return { text: original, zhuyin: fixed ?? syllables[index] ?? null };
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
