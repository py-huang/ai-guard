import type { Metadata } from "next";

import { WatchVoiceFlow } from "@/components/pages/watch-voice-flow";

export const metadata: Metadata = {
  title: "遠傳智靈｜AI 心守護手錶語音",
  description: "兒童手錶上的 AI 心守護語音通話示意",
};

export default function WatchPage() {
  return <WatchVoiceFlow />;
}
