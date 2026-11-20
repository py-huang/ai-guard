import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "遠傳智靈｜AI 心守護示範",
};

export default function DemoPage() {
  return (
    <main className="flex h-dvh w-full overflow-x-auto bg-[#111]">
      <iframe
        className="h-full min-w-[768px] flex-1 border-0 bg-white"
        src="/"
        title="網頁版"
        allow="microphone"
      />
      <div className="flex h-full shrink-0 items-center px-10">
        <iframe
          className="aspect-[390/844] h-[90%] max-h-[844px] max-w-[390px] rounded-[28px] border-0"
          src="/mobile"
          title="手機版"
          allow="microphone"
        />
      </div>
    </main>
  );
}
