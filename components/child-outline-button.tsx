"use client";

import { type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

/** Figma secondary / outline action: red border, hover fill, pressed inset. */
export const childOutlineButtonClass =
  "inline-flex h-12 items-center justify-center gap-2 rounded-2xl border border-solid border-[#d63a37] bg-white px-4 text-[15px] font-medium tracking-[0.1px] text-[#c02d32] transition-all duration-150 hover:bg-[#fff0ee] hover:shadow-[0px_4px_5px_rgba(38,20,18,0.14)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d63a37] active:border-[#c02d32] active:bg-[#ffe2df] active:shadow-[inset_0px_2px_3px_0px_rgba(46,10,10,0.24)] disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none";

export function ChildOutlineButton({ className, type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={cn(childOutlineButtonClass, className)} type={type} {...props} />;
}
