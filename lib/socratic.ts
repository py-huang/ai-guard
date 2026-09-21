const GENTLE_HINT = "\n\n你先試試看：這一步你會先做什麼？";

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
