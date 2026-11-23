import type { Metadata } from "next";
import { ScaledFrame } from "@/components/scaled-frame";

export const metadata: Metadata = {
  title: "遠傳智靈｜AI 心守護示範",
};

export default function DemoPage() {
  return (
    <main className="flex h-dvh w-full overflow-hidden bg-[#111]">
      <ScaledFrame className="h-full min-w-0 flex-1" src="/" title="網頁版" layoutWidth={1280} />
      <div className="flex h-full shrink-0 items-center px-10">
        <ScaledFrame className="aspect-[390/844] h-[90%] max-h-[844px] rounded-[28px]" src="/mobile" title="手機版" layoutWidth={390} />
      </div>
    </main>
  );
}
