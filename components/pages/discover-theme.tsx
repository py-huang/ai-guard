"use client";

import { useState } from "react";

type Topic = {
  title: string;
  color: string;
  icon: string;
  questions: string[];
};

const topics: Topic[] = [
  {
    title: "自然探索",
    color: "bg-[#ecf9f3]",
    icon: "/discover/topic-dinosaur-clean.svg",
    questions: ["恐龍為什麼會滅絕？", "植物為什麼需要陽光？", "火山怎麼形成？"],
  },
  {
    title: "太空世界",
    color: "bg-[#f4f0ff]",
    icon: "/discover/topic-planet-clean.svg",
    questions: ["月亮為什麼會變形？", "宇宙有多大？", "人能住在火星嗎？"],
  },
  {
    title: "寫作靈感",
    color: "bg-[#ffe7d7]",
    icon: "/discover/topic-writing-clean.svg",
    questions: ["怎麼寫第一次看雪？", "讓角色更有個性的方法？", "一句話怎麼變成一段？"],
  },
  {
    title: "數位安全",
    color: "bg-[#ecf6ff]",
    icon: "/discover/safety-shield-clean.svg",
    questions: ["怎麼設定安全密碼？", "網友問地址怎麼辦？", "遊戲帳號被盜怎麼做？"],
  },
];

export function DiscoverTheme() {
  const [selectedQuestion, setSelectedQuestion] = useState<string | null>(null);

  return (
    <section className="px-5 py-9 sm:px-8 lg:px-12 lg:pt-10">
      <p className="text-sm leading-[22px] font-medium text-[#c02d32]">我的 AI 探索筆記</p>
      <h1 className="mt-3 text-[30px] leading-[1.4] font-bold sm:text-[36px] sm:leading-[50px]">今天想探索什麼？</h1>
      <p className="mt-1 text-base leading-[26px] text-[#506058]">從一個好奇開始，看看問題可以走到哪裡。</p>

      <div className="mt-[60px] grid max-w-[1064px] grid-cols-1 gap-5 lg:grid-cols-2 lg:gap-x-8 lg:gap-y-8">
        {topics.map((topic) => (
          <article className={`h-[260px] overflow-hidden rounded-[22px] p-5 ${topic.color}`} key={topic.title}>
            <div className="flex items-center gap-4">
              <span className="grid size-[54px] shrink-0 place-items-center rounded-[17px] bg-white">
                <img className="size-[50px] drop-shadow-[0_2px_3px_rgba(20,33,26,0.06)]" src={topic.icon} alt="" aria-hidden="true" />
              </span>
              <div>
                <h2 className="text-xl leading-[30px] font-bold">{topic.title}</h2>
                <p className="mt-0.5 text-xs leading-[18px] text-[#506058]">3 個可以開始的問題</p>
              </div>
            </div>

            <div className="mt-5 space-y-2.5">
              {topic.questions.map((question) => (
                <button
                  aria-pressed={selectedQuestion === question}
                  className="flex h-[38px] w-full items-center justify-between rounded-xl bg-white px-[14px] text-left text-[13px] leading-[21px] font-medium text-[#13221b] transition-[transform,box-shadow] hover:-translate-y-0.5 hover:shadow-[0_2px_6px_rgba(20,33,26,0.06)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#177049]"
                  key={question}
                  onClick={() => setSelectedQuestion(question)}
                  type="button"
                >
                  <span className="truncate">{question}</span>
                  <img className="ml-3 size-5 shrink-0" src="/discover/question-arrow.svg" alt="" aria-hidden="true" />
                </button>
              ))}
            </div>
          </article>
        ))}
      </div>

      <div className="mt-8 flex max-w-[1064px] flex-wrap items-center justify-between gap-4 lg:mt-8">
        <p className="text-[13px] leading-5 text-[#506058]">找不到想問的？直接開始一個新問題。</p>
        <button
          aria-label="問自己的問題"
          className="h-12 overflow-hidden rounded-2xl transition-[filter] hover:brightness-[.875] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#177049]"
          onClick={() => setSelectedQuestion(null)}
          type="button"
        >
          <img className="block h-12 w-auto" src="/discover/explore-ask.svg" alt="" aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}