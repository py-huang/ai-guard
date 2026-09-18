import type { ReactNode } from "react";

type ParentLayoutProps = {
  children: ReactNode;
};

export default function ParentLayout({ children }: ParentLayoutProps) {
  return <div className="min-h-dvh bg-white text-[#13221b]">{children}</div>;
}