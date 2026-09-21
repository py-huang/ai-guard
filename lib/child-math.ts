const MATH_PATTERN =
  /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\$([^$\n]+?)\$|\\\((.+?)\\\)/g;

export function formatChildMath(source: string) {
  return source
    .replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, "$1／$2")
    .replace(/\\sqrt\{([^{}]+)\}/g, "√$1")
    .replace(/\\times/gi, "×")
    .replace(/\\div/gi, "÷")
    .replace(/\\cdot/g, "·")
    .replace(/\\pm/g, "±")
    .replace(/\\leq/g, "≤")
    .replace(/\\geq/g, "≥")
    .replace(/\\neq/g, "≠")
    .replace(/\\approx/g, "≈")
    .replace(/\\left|\\right/g, "")
    .replace(/\\[,;:!]/g, " ")
    .replace(/\\/g, "")
    .replace(/[{}]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function replaceChildMathInMarkdown(markdown: string) {
  return markdown.replace(MATH_PATTERN, (...args) => {
    const match = args[0] as string;
    const groups = args.slice(1, 5) as Array<string | undefined>;
    const raw = groups.find(Boolean) ?? "";
    const expr = formatChildMath(raw);
    if (!expr) {
      return "";
    }

    const isBlock = match.startsWith("$$") || match.startsWith("\\[");
    if (/^[0-9.]+$/.test(expr)) {
      return expr;
    }

    const escaped = expr.replace(/`/g, "'");
    return isBlock ? `\n\n\`${escaped}\`\n\n` : `\`${escaped}\``;
  });
}
