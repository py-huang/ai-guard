import type { Metadata } from "next";
import { Noto_Sans_TC } from "next/font/google";

import { ReadingAssistProvider } from "@/components/reading-assist-provider";
import "./globals.css";

const notoSansTc = Noto_Sans_TC({
  variable: "--font-noto-sans-tc",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "遠傳智靈｜AI 心守護",
  description: "遠傳智靈 AI 心守護",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="zh-Hant"
      className={`${notoSansTc.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ReadingAssistProvider>{children}</ReadingAssistProvider>
      </body>
    </html>
  );
}
