export type PiiKind = "姓名" | "學校" | "班級" | "學號" | "IG帳號" | "電話" | "地址" | "Email" | "身分證" | "其他";

export type PiiHit = {
  kind: PiiKind;
  value: string;
};

export type PiiPreview = {
  hits: PiiHit[];
  safeText: string;
  highlighted: { text: string; sensitive: boolean }[];
};

const PATTERNS: { kind: PiiKind; regex: RegExp }[] = [
  { kind: "Email", regex: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g },
  { kind: "電話", regex: /(?:0?9\d{2}[-\s]?\d{3}[-\s]?\d{3}|0\d{1,2}[-\s]?\d{6,8})/g },
  { kind: "身分證", regex: /[A-Z][12]\d{8}/g },
  { kind: "學校", regex: /[\u4e00-\u9fff]{2,8}(?:國小|國中|高中|小學|中學)/g },
  { kind: "班級", regex: /[一二三四五六七八九十兩\d]{1,2}年[一二三四五六七八九十甲乙丙丁\d]{1,2}班/g },
  { kind: "學號", regex: /(?:學號)[:：是為]?\s*(\d{3,10})/g },
  { kind: "IG帳號", regex: /(?:IG|ig|Instagram|instagram)\s*(?:帳號)?[:：是為]?\s*@?([A-Za-z][A-Za-z0-9._]{1,29})/g },
  { kind: "姓名", regex: /(?:我叫|我是|名字是)\s*(?:[一二三四五六七八九十兩\d]{1,2}年[一二三四五六七八九十甲乙丙丁\d]{1,2}班)?\s*([\u4e00-\u9fff]{2,4})/g },
  { kind: "地址", regex: /(?:台北市|臺北市|新北市|桃園市|台中市|臺中市|台南市|臺南市|高雄市|基隆市|新竹市|嘉義市)[\u4e00-\u9fff0-9]{0,16}/g },
];

function uniqueHits(hits: PiiHit[]) {
  const seen = new Set<string>();
  return hits.filter((hit) => {
    const key = `${hit.kind}:${hit.value}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function inspectPii(text: string): PiiPreview {
  const hits: PiiHit[] = [];

  for (const { kind, regex } of PATTERNS) {
    const pattern = new RegExp(regex.source, regex.flags);
    let match: RegExpExecArray | null;
    while ((match = pattern.exec(text))) {
      const value = (match[1] ?? match[0]).trim();
      if (value) {
        hits.push({ kind, value });
      }
    }
  }

  const unique = uniqueHits(hits);
  let safeText = text;
  for (const hit of unique) {
    safeText = safeText.replaceAll(hit.value, replacementFor(hit.kind));
  }

  safeText = polishSafeText(safeText);

  return {
    hits: unique,
    safeText,
    highlighted: highlight(text, unique.map((hit) => hit.value)),
  };
}

function replacementFor(kind: PiiKind) {
  switch (kind) {
    case "姓名":
      return "一位國小學生";
    case "學校":
      return "學校";
    case "班級":
      return "班級";
    case "學號":
      return "";
    case "IG帳號":
      return "";
    case "電話":
      return "";
    case "地址":
      return "這個城市";
    case "Email":
      return "";
    case "身分證":
      return "";
    case "其他":
      return "";
  }
}

function polishSafeText(text: string) {
  return text
    .replace(/我叫一位國小學生/g, "我是一位國小學生")
    .replace(/我是一位國小學生[，,]\s*我在學校上課/g, "我是一位國小學生")
    .replace(/\s{2,}/g, " ")
    .replace(/[，,]{2,}/g, "，")
    .trim();
}

function highlight(text: string, values: string[]) {
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

export function hasPii(text: string) {
  return inspectPii(text).hits.length > 0;
}
