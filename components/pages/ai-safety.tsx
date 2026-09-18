import Link from "next/link";
import type { ReactNode } from "react";

import { LessonQuiz } from "@/components/pages/image-lesson-quiz";

const lessonHref = "/safety/privacy-lesson";

const safeTopics = ["我喜歡的恐龍", "作文裡想表達的感受", "一道不會的數學題", "想了解的自然現象"];
const privateTopics = ["真實姓名與學校", "住家地址或精確位置", "電話、電子郵件", "密碼、證件與付款資料"];

type InformationCardProps = {
  type: "safe" | "private";
  title: string;
  topics: string[];
  href?: string;
};

function InformationCard({ type, title, topics, href }: InformationCardProps) {
  const isSafe = type === "safe";
  const className = `block min-h-[286px] rounded-[24px] p-[22px] ${
    href
      ? "transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#177049]"
      : ""
  } ${isSafe ? "bg-[#ecf9f3]" : "bg-[#fff0ee]"}`;
  const content = <>
    <span className={`inline-flex h-8 items-center rounded-2xl bg-white px-3 text-xs font-medium ${isSafe ? "text-[#177049]" : "text-[#c02d32]"}`}>
      {isSafe ? "可以安心聊" : "先不要分享"}
    </span>
    <h2 className="mt-4 text-[22px] leading-8 font-bold">{title}</h2>
    <ul className={`mt-4 space-y-3 text-sm leading-[22px] font-medium ${isSafe ? "text-[#177049]" : "text-[#c02d32]"}`}>
      {topics.map((topic) => (
        <li key={topic}>{isSafe ? "✓" : "—"}　{topic}</li>
      ))}
    </ul>
  </>;

  return href ? <Link className={className} href={href}>{content}</Link> : <div className={className}>{content}</div>;
}

export function AiSafety() {
  return (
    <section className="px-5 py-8 sm:px-8 lg:px-12 xl:pl-12 xl:pr-8 xl:pt-10">
      <div className="max-w-[994px]">
        <h1 className="text-[32px] leading-[44px] font-bold">AI 安全小幫手</h1>
        <p className="mt-1 text-[15px] leading-6 text-[#506058]">分享前先想一想：回答問題真的需要這些資料嗎？</p>

        <Link className="mt-6 block rounded-[24px] border border-[#dde3df] bg-white p-6 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#177049]" href={lessonHref}>
          <p className="text-xs leading-[18px] font-medium text-[#8a968f]">小練習</p>
          <h2 className="mt-3 text-xl leading-[30px] font-bold">AI 問你住在哪裡，哪一個回答比較安全？</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="min-h-[82px] rounded-2xl bg-[#fff0ee] px-[18px] py-[14px]">
              <p className="text-[15px] leading-6 font-medium">我住在台北市○○路 8 號</p>
              <p className="mt-1 text-xs leading-[18px] text-[#c02d32]">包含太精確的位置</p>
            </div>
            <div className="min-h-[82px] rounded-2xl bg-[#ecf9f3] px-[18px] py-[14px]">
              <p className="text-[15px] leading-6 font-medium">我住在北部的一個城市</p>
              <p className="mt-1 text-xs leading-[18px] text-[#177049]">✓ 已經足夠回答問題</p>
            </div>
          </div>
          <span className="mt-3 ml-auto flex h-12 w-[162px] items-center justify-center rounded-2xl bg-[#d63a37] text-[15px] leading-5 font-medium tracking-[0.1px] text-white">看答案</span>
        </Link>

        <div className="mt-4 grid gap-4 md:grid-cols-2 md:gap-5">
          <InformationCard type="safe" title="興趣、想法與學習問題" topics={safeTopics} href={lessonHref} />
          <InformationCard type="private" title="能辨認你或保護帳號的資料" topics={privateTopics} href={lessonHref} />
        </div>
      </div>
    </section>
  );
}

type SafetyLessonProps = {
  title: string;
  description: string;
  safeTitle: string;
  safeTopics: string[];
  privateTitle: string;
  privateTopics: string[];
  question: string;
  options: Array<{ answer: string; feedback: string }>;
  quizContent?: ReactNode;
};

function SafetyLesson({
  title,
  description,
  safeTitle,
  safeTopics,
  privateTitle,
  privateTopics,
  question,
  options,
  quizContent,
}: SafetyLessonProps) {
  return (
    <section className="px-5 py-8 sm:px-8 lg:px-12 xl:pl-12 xl:pr-8 xl:pt-10">
      <div className="max-w-[994px]">
        <h1 className="text-[32px] leading-[44px] font-bold">{title}</h1>
        <p className="mt-1 text-[15px] leading-6 text-[#506058]">{description}</p>

        <div className="mt-14 grid gap-4 md:grid-cols-2 md:gap-5">
          <InformationCard type="safe" title={safeTitle} topics={safeTopics} />
          <InformationCard type="private" title={privateTitle} topics={privateTopics} />
        </div>

        <div className="mt-[38px] rounded-[24px] border border-[#dde3df] bg-white p-6">
          {quizContent ?? <>
            <p className="text-xs leading-[18px] font-medium text-[#8a968f]">小練習</p>
            <h2 className="mt-3 text-xl leading-[30px] font-bold">{question}</h2>
            <div className={`mt-4 grid gap-4 sm:grid-cols-2 ${options.length === 3 ? "lg:grid-cols-3 lg:gap-3" : ""}`}>
              {options.map(({ answer, feedback }) => (
                <div className="min-h-[82px] rounded-2xl border border-[#ccd1cc] px-[18px] py-[14px]" key={answer}>
                  <p className="text-lg leading-6 font-medium">{answer}</p>
                  <p className="mt-1 text-base leading-6 text-[#c02d32]">{feedback}</p>
                </div>
              ))}
            </div>
          </>}
          <Link className="mt-3 ml-auto flex h-12 w-fit items-center gap-2 rounded-2xl bg-[#d63a37] px-4 text-[15px] leading-5 font-medium tracking-[0.1px] text-white transition-colors hover:bg-[#bd2e2c] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d63a37]" href="/safety">
            完成並返回安全小幫手
            <img className="size-5" src="/discover/arrow-right-clean.svg" alt="" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </section>
  );
}

export function PrivacyLesson() {
  const options = [
    { answer: "我叫小宇，住在瑞光路。", feedback: "包含姓名與地址" },
    { answer: "我是一位國小學生。", feedback: "沒錯！只留下真正需要的資訊" },
  ];

  return (
    <SafetyLesson
      title="哪些資料不要告訴 AI？"
      description="小宇想問附近的活動，但不需要說出真實姓名和門牌。"
      safeTitle="只留下問題真正需要的資訊"
      safeTopics={["年齡層", "城市層級位置", "想問的事情", "不需要真實姓名"]}
      privateTitle="先拿掉這些資訊"
      privateTopics={["真實姓名", "學校", "詳細地址", "電話與電子郵件"]}
      question="哪一句比較安全？"
      options={options}
      quizContent={<LessonQuiz
        question="哪一句比較安全？"
        options={options}
        feedbackTitle="沒錯！只留下問題真正需要的資訊就好。"
        correctOptionIndex={1}
      />}
    />
  );
}

export function AiTruthLesson() {
  const options = [
    { answer: "直接相信", feedback: "先停一下再確認" },
    { answer: "再找其他資料確認", feedback: "沒錯！多確認會更安心" },
    { answer: "立刻分享給朋友", feedback: "先停一下再確認" },
  ];

  return (
    <SafetyLesson
      title="AI 說的一定是真的嗎？"
      description="AI 很會整理答案，但也可能理解錯、記錯或答得不完整。"
      safeTitle="看到奇怪答案時"
      safeTopics={["再問一次", "找其他資料", "問老師或家長", "比較不同說法"]}
      privateTitle="不要立刻這樣做"
      privateTopics={["直接相信", "不檢查就分享", "當成唯一答案", "忽略不合理的地方"]}
      question="看到奇怪答案時，可以怎麼做？"
      options={options}
      quizContent={<LessonQuiz
        question="看到奇怪答案時，可以怎麼做？"
        options={options}
        feedbackTitle="答對了！AI 也可能答錯，重要資訊可以多確認一次。"
        correctOptionIndex={1}
      />}
    />
  );
}

export function StrangerLesson() {
  const options = [
    { answer: "直接回答學校和住址", feedback: "還是太精確" },
    { answer: "不分享，找可信任的大人", feedback: "很好！保護位置也保護自己" },
  ];

  return (
    <SafetyLesson
      title="網友問我住哪裡怎麼辦？"
      description="地址、學校與即時位置，不用告訴陌生人。"
      safeTitle="可以這樣回應"
      safeTopics={["不回答詳細位置", "停止聊天", "告訴信任的大人", "封鎖可疑帳號"]}
      privateTitle="不要分享"
      privateTopics={["家裡門牌", "學校班級", "現在在哪裡", "一個人在家的時間"]}
      question="陌生人問你現在在哪裡，怎麼回答？"
      options={options}
      quizContent={<LessonQuiz
        question="陌生人問你現在在哪裡，怎麼回答？"
        options={options}
        feedbackTitle="做得好！不分享學校與住址，並找可信任的大人。"
        correctOptionIndex={1}
      />}
    />
  );
}

export function ImageLesson() {
  const options = [
    { answer: "有姓名電話的聯絡簿", feedback: "會一起分享個人資料" },
    { answer: "沒有個人資料的作業題目", feedback: "正確：使用安全圖片" },
  ];

  return (
    <SafetyLesson
      title="哪些圖片不要上傳？"
      description="圖片裡也可能藏著個人資料或不適合分享的內容。"
      safeTitle="上傳前先看看"
      safeTopics={["問題真的需要圖片嗎", "姓名是否遮住", "電話是否遮住", "只拍需要的部分"]}
      privateTitle="這些圖片不要上傳"
      privateTopics={["私密內容", "證件與付款資料", "偷拍", "嚴重暴力"]}
      question="作業照片上有姓名和電話，先怎麼做？"
      options={options}
      quizContent={<LessonQuiz
        question="作業照片上有姓名和電話，先怎麼做？"
        options={options}
        feedbackTitle="答對了！沒有個人資料的作業題目比較適合傳給 AI。"
        correctOptionIndex={1}
      />}
    />
  );
}