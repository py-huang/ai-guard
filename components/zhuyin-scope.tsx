"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";

import { useReadingAssist } from "@/hooks/use-reading-assist";
import { splitZhuyin, toZhuyinParts } from "@/lib/zhuyin";
import { cn } from "@/lib/utils";

const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "TEXTAREA", "INPUT", "SELECT", "CODE", "PRE", "SVG", "NOSCRIPT"]);

export function ZhuyinScope({ children, className }: { children: ReactNode; className?: string }) {
  const { zhuyinEnabled } = useReadingAssist();
  const ref = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;

    if (!zhuyinEnabled) {
      restoreZhuyin(root);
      return;
    }

    const observer = new MutationObserver(() => {
      observer.disconnect();
      restoreZhuyin(root);
      annotateZhuyin(root);
      observer.observe(root, { childList: true, subtree: true, characterData: true });
    });

    annotateZhuyin(root);
    observer.observe(root, { childList: true, subtree: true, characterData: true });

    return () => {
      observer.disconnect();
      restoreZhuyin(root);
    };
  }, [zhuyinEnabled]);

  return (
    <div className={cn(className)} ref={ref}>
      {children}
    </div>
  );
}

function annotateZhuyin(root: HTMLElement) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (!node.nodeValue || !/[\u3400-\u9fff]/.test(node.nodeValue)) {
        return NodeFilter.FILTER_REJECT;
      }
      const parent = node.parentElement;
      if (!parent) return NodeFilter.FILTER_REJECT;
      if (parent.closest("[data-zhuyin-source], [data-zhuyin-skip], .zhuyin-unit")) {
        return NodeFilter.FILTER_REJECT;
      }
      if (SKIP_TAGS.has(parent.tagName)) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  const nodes: Text[] = [];
  while (walker.nextNode()) {
    nodes.push(walker.currentNode as Text);
  }
  nodes.forEach(replaceTextNode);
}

function replaceTextNode(node: Text) {
  const value = node.nodeValue ?? "";
  const parts = toZhuyinParts(value);
  if (!parts.some((part) => part.zhuyin)) return;

  const wrapper = document.createElement("span");
  wrapper.dataset.zhuyinSource = value;
  parts.forEach((part) => {
    if (!part.zhuyin) {
      wrapper.append(part.text);
      return;
    }
    const unit = document.createElement("span");
    unit.className = "zhuyin-unit";
    const han = document.createElement("span");
    han.className = "zhuyin-han";
    han.textContent = part.text;
    const ruby = document.createElement("span");
    ruby.className = "zhuyin-ruby";
    const { letters, tone } = splitZhuyin(part.zhuyin);
    const col = document.createElement("span");
    col.className = "zhuyin-col";
    unit.style.setProperty("--zhuyin-n", String(Math.max(letters.length, 3)));
    letters.forEach((letter) => {
      const glyph = document.createElement("span");
      glyph.className = letter === "˙" ? "zhuyin-letter zhuyin-light" : "zhuyin-letter";
      glyph.textContent = letter;
      col.append(glyph);
    });
    ruby.append(col);
    if (tone) {
      const mark = document.createElement("span");
      mark.className = "zhuyin-tone";
      mark.textContent = tone;
      ruby.append(mark);
    }
    unit.append(han, ruby);
    wrapper.append(unit);
  });
  node.replaceWith(wrapper);
}

function restoreZhuyin(root: HTMLElement) {
  root.querySelectorAll<HTMLElement>("[data-zhuyin-source]").forEach((element) => {
    element.replaceWith(element.dataset.zhuyinSource ?? "");
  });
}
