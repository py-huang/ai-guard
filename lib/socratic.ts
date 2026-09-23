const GENTLE_HINT = "\n\n你先試試看：這一步你會先做什麼？";

const INBOUND_PREFIX =
  "【教學模式】小朋友想直接拿到答案。請用蘇格拉底法：" +
  "先給一個小提示，最多示範一步，最後用一個問題請他自己想。" +
  "不要一次寫完整解答。\n\n小朋友說：";

export function stripSocraticInboundPrefix(text: string) {
  if (text.startsWith(INBOUND_PREFIX)) {
    return text.slice(INBOUND_PREFIX.length);
  }
  return text.replace(/^【教學模式】[\s\S]*?小朋友說：\s*/u, "");
}

export function applyOutboundSocraticHint(reply: string, llmPrompt: string) {
  if (!llmPrompt.includes("【教學模式】")) {
    return reply;
  }

  const stripped = reply.trim();
  if (!stripped) {
    return reply;
  }

  if (/[？?]/.test(stripped) || stripped.endsWith("嗎") || stripped.endsWith("呢")) {
    return reply;
  }

  return `${stripped}${GENTLE_HINT}`;
}
