"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";

import { useReadingAssist } from "@/hooks/use-reading-assist";
import { toZhuyinParts } from "@/lib/zhuyin";
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
      if (parent.closest("[data-zhuyin-source], [data-zhuyin-skip], ruby")) {
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
    const ruby = document.createElement("ruby");
    ruby.append(part.text);
    const rt = document.createElement("rt");
    rt.textContent = part.zhuyin;
    ruby.append(rt);
    wrapper.append(ruby);
  });
  node.replaceWith(wrapper);
}

function restoreZhuyin(root: HTMLElement) {
  root.querySelectorAll<HTMLElement>("[data-zhuyin-source]").forEach((element) => {
    element.replaceWith(element.dataset.zhuyinSource ?? "");
  });
}
