import type { Components } from "react-markdown";
import Markdown from "react-markdown";

import { replaceChildMathInMarkdown } from "@/lib/child-math";
import { cn } from "@/lib/utils";

type MarkdownMessageProps = {
  children: string;
  className?: string;
  compact?: boolean;
};

export function MarkdownMessage({ children, className, compact = false }: MarkdownMessageProps) {
  const body = compact ? "text-sm leading-6" : "text-[17px] leading-8";
  const heading = compact ? "text-base font-bold leading-6" : "text-[20px] font-bold leading-8";

  const components: Components = {
    p: ({ children: nodes }) => <p className={cn(body, "my-2 last:mb-0 first:mt-0")}>{nodes}</p>,
    strong: ({ children: nodes }) => <strong className="font-bold">{nodes}</strong>,
    em: ({ children: nodes }) => <em className="italic">{nodes}</em>,
    h1: ({ children: nodes }) => <h1 className={cn(heading, "mt-4 mb-2")}>{nodes}</h1>,
    h2: ({ children: nodes }) => <h2 className={cn(heading, "mt-4 mb-2")}>{nodes}</h2>,
    h3: ({ children: nodes }) => <h3 className={cn(heading, "mt-3 mb-1")}>{nodes}</h3>,
    ul: ({ children: nodes }) => <ul className={cn(body, "my-3 list-disc space-y-1 pl-6")}>{nodes}</ul>,
    ol: ({ children: nodes }) => <ol className={cn(body, "my-3 list-decimal space-y-1 pl-6")}>{nodes}</ol>,
    li: ({ children: nodes }) => <li className={cn(body, "pl-1")}>{nodes}</li>,
    blockquote: ({ children: nodes }) => (
      <blockquote className="my-3 border-l-4 border-[#cfe8da] pl-4 text-[#506058]">{nodes}</blockquote>
    ),
    a: ({ href, children: nodes }) => (
      <a className="font-medium text-[#177049] underline underline-offset-2" href={href} rel="noreferrer" target="_blank">
        {nodes}
      </a>
    ),
    code: ({ children: nodes, className: codeClassName }) => {
      const isBlock = Boolean(codeClassName);
      if (isBlock) {
        return <code className={codeClassName}>{nodes}</code>;
      }
      return <code className="rounded bg-[#ecf9f3] px-1 py-0.5 text-[0.95em] tabular-nums">{nodes}</code>;
    },
    pre: ({ children: nodes }) => (
      <pre className="my-3 overflow-x-auto rounded-2xl bg-[#14211a] px-4 py-3 text-[14px] leading-6 text-white">{nodes}</pre>
    ),
    hr: () => <hr className="my-4 border-[#dde3df]" />,
  };

  return (
    <div className={cn("max-w-none break-words", className)}>
      <Markdown components={components}>{replaceChildMathInMarkdown(children)}</Markdown>
    </div>
  );
}
