export function looksLikeWriting(text: string) {
  const compact = text.replace(/\s+/g, "");
  return /作文|寫作|寫一篇|寫日記|日記|幫我寫故事|主題式寫作/.test(compact);
}
