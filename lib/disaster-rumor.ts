export const DISASTER_RUMOR_REPLY =
  "我沒有氣象署的即時警報可以查。網路上說「明天會有大地震」，多半是謠言；地震沒辦法準確預言明天幾點。請看中央氣象署，或問身邊的大人。我們也可以改聊功課或自然課。";

export function needsLiveSearch(text: string) {
  const compact = text.replace(/\s+/g, "");
  if (/氣象署|天氣預報|颱風|新聞說|網路上說/.test(compact)) {
    return true;
  }
  if (/幾度/.test(compact) && /天氣|氣溫|氣象/.test(compact)) {
    return true;
  }
  if (/是真的嗎/.test(compact) && /新聞|網路上|地震|颱風|海嘯/.test(compact)) {
    return true;
  }
  return /地震|海嘯/.test(compact) && /明天|今天|警報/.test(compact);
}

export function isDisasterRumor(text: string) {
  const compact = text.replace(/\s+/g, "");
  return /地震|海嘯|颱風警報|氣象警報/.test(compact) && /明天|今天|是真的|網路上|新聞/.test(compact);
}

export function childSafeErrorMessage(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  if (/老師現在有點忙/.test(raw)) {
    return raw;
  }
  if (/did not match the expected pattern|match the requested format|unexpected token|unexpected end of json|failed to fetch|load failed|networkerror/i.test(raw)) {
    return "暫時無法回覆。請再試一次。";
  }
  return raw.trim() || "暫時無法回覆。";
}
