import { cn } from "@/lib/utils";

const WAVE_HEIGHTS = [18, 28, 38, 48, 58];
const WAVE_BARS = Array.from({ length: 23 }, (_, index) => WAVE_HEIGHTS[index % 5]);

const badgeToneClass = {
  mint: "bg-[#ddf5ea] text-[#177049]",
  sky: "bg-[#ecf6ff] text-[#25324a]",
  coral: "bg-[#fff0ee] text-[#9d1a25]",
} as const;

export type WatchBadgeTone = keyof typeof badgeToneClass;

type WatchVoiceCallProps = {
  badge: string;
  tone: WatchBadgeTone;
  headline: string;
  waveform: "live" | "idle" | "levels";
  levels?: readonly number[] | null;
  micOpen: boolean;
  status: readonly [string, string];
  showEnd?: boolean;
  onEnd?: () => void;
  onActivate?: () => void;
};

export function WatchVoiceCall({
  badge,
  tone,
  headline,
  waveform,
  levels = null,
  micOpen,
  status,
  showEnd = false,
  onEnd,
  onActivate,
}: WatchVoiceCallProps) {
  const live = waveform === "live";
  const driven = waveform === "levels";

  return (
    <div className="relative aspect-[430/592] w-full [container-type:inline-size]">
      <div
        className="absolute top-0 left-0 h-[592px] w-[430px] origin-top-left"
        style={{ transform: "scale(calc(100cqw / 430px))" }}
      >
        <div className="relative h-full w-full overflow-hidden rounded-[72px] border border-[#506058] bg-[#0b1017]">
          <div className="absolute top-[41px] left-[33px] h-[508px] w-[362px] overflow-hidden rounded-[48px] bg-[#171f2b]">
            <p className="absolute top-[26px] left-7 w-[200px] text-left text-base leading-6 font-bold text-white">
              遠傳智靈
            </p>
            <p className="absolute top-[50px] left-7 w-[220px] text-left text-xs leading-[18px] font-medium text-[#8a968f]">
              AI 心守護
            </p>
            <p
              className={cn(
                "absolute top-[90px] left-7 inline-flex h-[30px] items-center justify-center rounded-full px-3 text-xs leading-[18px] font-medium tracking-[0.2px]",
                badgeToneClass[tone],
              )}
            >
              {badge}
            </p>
            <p className="absolute top-[138px] left-7 w-[190px] text-left text-[36px] leading-[44px] font-bold text-white tabular-nums">
              {headline}
            </p>
            <img
              alt=""
              className={cn("absolute top-[127px] left-[270px] size-14", micOpen ? "opacity-100" : "opacity-45")}
              height={56}
              src="/watch/microphone.svg"
              width={56}
            />
            <div
              className={cn(
                "absolute top-[198px] left-7 h-28 w-[306px] overflow-hidden rounded-[20px] bg-[#111821]",
                live || driven ? "opacity-100" : "opacity-30",
              )}
            >
              {WAVE_BARS.map((resting, index) => {
                const level = driven ? Math.max(0, Math.min(1, levels?.[index] ?? 0)) : 1;
                const shape = resting / 58;
                const amount = driven ? Math.max(level, 0.16) : 1;
                const height = driven ? 8 + amount * shape * 54 : resting;
                return (
                  <span
                    key={index}
                    className={cn(
                      "absolute w-1.5 rounded-[3px] bg-[#2ea56f]",
                      live && "watch-wave-bar",
                    )}
                    style={{
                      height,
                      left: 16 + index * 12,
                      top: (112 - height) / 2,
                      animationDelay: live ? `${(index % 5) * 0.12}s` : undefined,
                    }}
                  />
                );
              })}
            </div>
            <div className="absolute top-[435px] left-7 w-[306px] text-left text-sm leading-[22px] font-normal text-[#8a968f]">
              <p>{status[0]}</p>
              <p>{status[1]}</p>
            </div>
          </div>
          {showEnd ? (
            <button
              className="absolute top-[385px] left-[171px] z-10 grid h-[72px] w-[88px] cursor-pointer place-items-center rounded-[25px] bg-[#d12e30] text-base font-bold text-white"
              onClick={onEnd}
              type="button"
            >
              結束
            </button>
          ) : null}
          {onActivate ? (
            <button
              aria-label="撥打遠傳智靈"
              className="absolute inset-0 z-10 cursor-pointer rounded-[72px]"
              onClick={onActivate}
              type="button"
            />
          ) : null}
        </div>
      </div>
    </div>
  );
}
