"use client";

import { useEffect, useRef, useState } from "react";

type ScaledFrameProps = {
  src: string;
  title: string;
  /** The frame always lays out at least this wide, then shrinks to fit, so its breakpoints don't depend on the viewer's screen. */
  layoutWidth: number;
  className?: string;
};

export function ScaledFrame({ src, title, layoutWidth, className = "" }: ScaledFrameProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const observer = new ResizeObserver(([entry]) => {
      setBox({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const width = box ? Math.max(layoutWidth, box.width) : 0;
  const scale = box && width ? box.width / width : 1;

  return (
    <div ref={containerRef} className={`relative overflow-hidden ${className}`}>
      <iframe
        className="absolute left-0 top-0 origin-top-left border-0 bg-white"
        style={box ? { width, height: box.height / scale, transform: `scale(${scale})` } : { width: "100%", height: "100%" }}
        src={src}
        title={title}
        allow="microphone"
      />
    </div>
  );
}
