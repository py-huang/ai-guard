"use client";

import { useState } from "react";

type QuizOption = {
  answer: string;
  feedback: string;
};

type LessonQuizProps = {
  question: string;
  options: QuizOption[];
  feedbackTitle: string;
  correctOptionIndex: number;
};

export function LessonQuiz({ question, options, feedbackTitle, correctOptionIndex }: LessonQuizProps) {
  const [showFeedback, setShowFeedback] = useState(false);
  const correctOption = options[correctOptionIndex];

  if (showFeedback) {
    return (
      <>
        <p className="text-xs leading-[18px] font-medium text-[#8a968f]">回饋</p>
        <h2 className="mt-3 text-xl leading-[30px] font-bold">{feedbackTitle}</h2>
        <div className="mt-4 flex min-h-[82px] flex-col gap-1.5 rounded-2xl border border-[#ccd1cc] px-[18px] py-[14px]">
          <p className="text-lg leading-6 font-medium">{correctOption.answer}</p>
          <p className="flex items-center gap-2 text-base leading-6 text-[#c02d32]">
            <img className="size-6 shrink-0 drop-shadow-[0px_2px_3px_rgba(20,33,26,0.06)]" src="/safety/learning-correct.svg" alt="" aria-hidden="true" />
            這個答案比較安全。
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      <p className="text-xs leading-[18px] font-medium text-[#8a968f]">小練習</p>
      <h2 className="mt-3 text-xl leading-[30px] font-bold">{question}</h2>
      <div className={`mt-4 grid gap-4 sm:grid-cols-2 ${options.length === 3 ? "lg:grid-cols-3 lg:gap-3" : ""}`}>
        {options.map(({ answer, feedback }, index) => (
          <button
            className="min-h-[82px] cursor-pointer rounded-2xl border border-[#ccd1cc] px-[18px] py-[14px] text-left transition-colors hover:border-[#177049] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#177049]"
            key={answer}
            onClick={() => index === correctOptionIndex && setShowFeedback(true)}
            type="button"
          >
            <span className="block text-lg leading-6 font-medium">{answer}</span>
            <span className="mt-1 block text-base leading-6 text-[#c02d32]">{feedback}</span>
          </button>
        ))}
      </div>
    </>
  );
}