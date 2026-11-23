import type { Metadata } from "next";
import { Noto_Sans_TC } from "next/font/google";

import { ConversationStoreProvider } from "@/store/conversation-store";
import { WritingStoreProvider } from "@/store/writing-store";
import { ReadingAssistProvider } from "@/components/reading-assist-provider";
import "./globals.css";

const notoSansTc = Noto_Sans_TC({
  variable: "--font-noto-sans-tc",
  subsets: ["latin"],
  display: "swap",
  fallback: ["Microsoft JhengHei", "PingFang TC", "Noto Sans TC", "sans-serif"],
});

export const metadata: Metadata = {
  title: "遠傳智靈｜AI 心守護",
  description: "遠傳智靈 AI 心守護",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // Translation extensions (e.g. Immersive Translate) add attributes to <html> before React
    // hydrates. This only silences attribute differences on this one element, not its children.
    <html
      lang="zh-Hant"
      className={`${notoSansTc.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col">
        <ReadingAssistProvider>
          <ConversationStoreProvider>
            <WritingStoreProvider>{children}</WritingStoreProvider>
          </ConversationStoreProvider>
        </ReadingAssistProvider>
      </body>
    </html>
  );
}
