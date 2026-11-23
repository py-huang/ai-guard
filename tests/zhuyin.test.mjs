import assert from "node:assert/strict";
import { register } from "node:module";
import { test } from "node:test";
import { pathToFileURL } from "node:url";

register(pathToFileURL(new URL("../scripts/ts-loader.mjs", import.meta.url).pathname));
const { toZhuyinParts } = await import("../lib/zhuyin.ts");

const read = (text) =>
  toZhuyinParts(text)
    .map((part) => part.zhuyin ?? part.text)
    .join(" ");

// Expected readings follow Taiwan Mandarin. 不 tone sandhi is intentionally not asserted.
const CASES = {
  媽媽: "ㄇㄚ ˙ㄇㄚ",
  謝謝: "ㄒㄧㄝˋ ˙ㄒㄧㄝ",
  我們: "ㄨㄛˇ ˙ㄇㄣ",
  好嗎: "ㄏㄠˇ ˙ㄇㄚ",
  為什麼: "ㄨㄟˋ ㄕㄣˊ ˙ㄇㄜ",
  因為: "ㄧㄣ ㄨㄟˋ",
  成為: "ㄔㄥˊ ㄨㄟˊ",
  長大: "ㄓㄤˇ ㄉㄚˋ",
  很長: "ㄏㄣˇ ㄔㄤˊ",
  銀行: "ㄧㄣˊ ㄏㄤˊ",
  還有: "ㄏㄞˊ ㄧㄡˇ",
  還錢: "ㄏㄨㄢˊ ㄑㄧㄢˊ",
  一個: "ㄧˊ ˙ㄍㄜ",
  這個: "ㄓㄜˋ ˙ㄍㄜ",
  個人: "ㄍㄜˋ ㄖㄣˊ",
  看著: "ㄎㄢˋ ˙ㄓㄜ",
  著急: "ㄓㄠ ㄐㄧˊ",
  垃圾: "ㄌㄜˋ ㄙㄜˋ",
  睡覺: "ㄕㄨㄟˋ ㄐㄧㄠˋ",
  音樂: "ㄧㄣ ㄩㄝˋ",
  快樂: "ㄎㄨㄞˋ ㄌㄜˋ",
  跑得快: "ㄆㄠˇ ˙ㄉㄜ ㄎㄨㄞˋ",
  恐龍為什麼會滅絕: "ㄎㄨㄥˇ ㄌㄨㄥˊ ㄨㄟˋ ㄕㄣˊ ˙ㄇㄜ ㄏㄨㄟˋ ㄇㄧㄝˋ ㄐㄩㄝˊ",
};

for (const [text, expected] of Object.entries(CASES)) {
  test(`zhuyin: ${text}`, () => {
    assert.equal(read(text), expected);
  });
}

test("zhuyin keeps non-Chinese text and placeholders untouched", () => {
  const parts = toZhuyinParts("我是 AI，<PERSON_1> 你好");
  assert.equal(parts.map((part) => part.text).join(""), "我是 AI，<PERSON_1> 你好");
  assert.equal(parts.find((part) => part.text.includes("PERSON_1"))?.zhuyin, null);
});
