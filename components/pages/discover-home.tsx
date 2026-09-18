"use client";

import { FormEvent, useState } from "react";

const topics = [
  {
    title: "自然探索",
    description: "從恐龍、植物到火山",
    color: "bg-[#ddf5ea]",
    icon: "/discover/topic-dinosaur.svg",
  },
  {
    title: "數學挑戰",
    description: "一步一步看懂方法",
    color: "bg-[#dceeff]",
    icon: "/discover/topic-math.svg",
  },
  {
    title: "故事與寫作",
    description: "把想法整理成自己的話",
    color: "bg-[#ffe7d7]",
    icon: "/discover/topic-writing.svg",
  },
  {
    title: "英文練習",
    description: "單字、發音與生活對話",
    color: "bg-[#ecf6ff]",
    icon: "/discover/topic-english.svg",
  },
  {
    title: "數位安全",
    description: "保護帳號與個人資料",
    color: "bg-[#ecf9f3]",
    icon: "/discover/safety-shield.svg",
  },
  {
    title: "太空世界",
    description: "星星、月亮與行星",
    color: "bg-[#eae1ff]",
    icon: "/discover/topic-planet.svg",
  },
];

export function DiscoverHome() {
  const [message, setMessage] = useState("");

  function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
  }

  return (
    <section className="relative overflow-hidden px-5 py-6 sm:px-8 lg:px-12 xl:pl-[130px] xl:pr-8 xl:pt-6">
      <h1 className="text-[18px] leading-7 font-bold">我的 AI 探索筆記</h1>

      <div className="relative mt-[34px] max-w-[854px]">
        <div className="absolute right-[68px] top-0 hidden rotate-[-5deg] rounded-[24px] bg-[#fff0ee] p-[3px] lg:block">
          <img className="size-[66px]" src="/discover/system-spark.svg" alt="" aria-hidden="true" />
        </div>
        <img className="absolute right-[2px] top-[88px] hidden lg:block" src="/discover/sticker-leaf.svg" alt="" aria-hidden="true" />
        <img className="absolute right-[104px] top-[123px] hidden lg:block" src="/discover/sticker-star.svg" alt="" aria-hidden="true" />

        <p className="text-base leading-6 text-[#506058]">嗨，小宇</p>
        <h2 className="mt-3 text-[32px] leading-[1.4] font-bold sm:text-[40px] sm:leading-[56px]">今天想探索什麼？</h2>
        <p className="mt-1 text-[17px] leading-7 text-[#506058]">打字或用說的都可以，我們一起找答案。</p>

        <form className="mt-[54px] flex h-[66px] max-w-[820px] items-center gap-2 rounded-full border border-[#dde3df] bg-white py-[9px] pl-2 pr-[10px]" onSubmit={submitMessage}>
          <button className="grid size-12 shrink-0 place-items-center rounded-full text-[#d63a37] hover:bg-[#fff0ee] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d63a37]" type="button" aria-label="新增附件" title="新增附件">
            <img className="size-8" src="/discover/composer-plus.svg" alt="" aria-hidden="true" />
          </button>
          <label className="sr-only" htmlFor="discover-message">想知道什麼？</label>
          <input
            id="discover-message"
            className="min-w-0 flex-1 bg-transparent text-[18px] text-[#13221b] outline-none placeholder:text-[#8a968f]"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="想知道什麼？可以打字或用說的"
          />
          <button className="grid size-12 shrink-0 place-items-center rounded-full border border-[#d63a37] text-[#d63a37] hover:bg-[#fff0ee] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d63a37]" type="button" aria-label="語音輸入" title="語音輸入">
            <img className="size-6" src="/discover/composer-microphone.svg" alt="" aria-hidden="true" />
          </button>
          <button className="grid size-12 shrink-0 place-items-center rounded-full bg-[#d63a37] text-white hover:bg-[#bd2e2c] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d63a37]" type="submit" aria-label="送出問題" title="送出問題">
            <img className="size-6 brightness-0 invert" src="/discover/composer-send.svg" alt="" aria-hidden="true" />
          </button>
        </form>
        <p className="mt-1 pl-1 text-[11px] leading-[17px] font-medium text-[#177049]">分享前會先保護你的個人資料</p>

        <h2 className="mt-[27px] text-xl leading-[30px] font-bold">今天想探索哪一個？</h2>
        <div className="mt-5 grid max-w-[854px] grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 xl:gap-x-[22px] xl:gap-y-[22px]">
          {topics.map((topic) => (
            <button
              className={`flex h-[104px] items-start gap-[11px] rounded-[18px] px-[13px] pt-[15px] text-left transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#177049] ${topic.color}`}
              key={topic.title}
              onClick={() => setMessage(`我想探索${topic.title}`)}
              type="button"
            >
              <span className="grid size-12 shrink-0 place-items-center overflow-hidden">
                <span className="grid size-[42px] place-items-center rounded-[14px] bg-white">
                  <img className="size-11 drop-shadow-[0_2px_3px_rgba(20,33,26,0.06)]" src={topic.icon} alt="" aria-hidden="true" />
                </span>
              </span>
              <span className="min-w-0 pt-0.5">
                <span className="block text-[15px] leading-[23px] font-bold">{topic.title}</span>
                <span className="mt-2 block text-xs leading-[19px] text-[#506058]">{topic.description}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}