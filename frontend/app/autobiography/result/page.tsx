"use client";

import React, { useState } from "react";
import { Check, Download, ArrowLeft, Star } from "lucide-react";
import Link from "next/link";

const SURVEY_QUESTIONS = [
  "내 이야기가 정확하게 담겼나요?",
  "글이 자연스럽게 읽히나요?",
  "AI가 내 감정과 경험을 잘 표현했나요?",
];

function SurveyForm() {
  const [ratings, setRatings] = useState<number[]>(Array(SURVEY_QUESTIONS.length).fill(0));
  const [submitted, setSubmitted] = useState(false);

  if (submitted) return (
    <div className="text-center py-8 text-emerald-600 font-medium">
      소중한 의견 감사합니다!
    </div>
  );

  return (
    <div className="space-y-6">
      {SURVEY_QUESTIONS.map((q, qi) => (
        <div key={qi}>
          <p className="text-sm text-gray-700 mb-2">{q}</p>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <button key={star} onClick={() => {
                setRatings((prev) => { const next = [...prev]; next[qi] = star; return next; });
              }}>
                <Star
                  size={24}
                  className={star <= ratings[qi] ? "text-yellow-400 fill-yellow-400" : "text-gray-200"}
                />
              </button>
            ))}
          </div>
        </div>
      ))}
      <button
        onClick={() => setSubmitted(true)}
        disabled={ratings.some((r) => r === 0)}
        className="mt-2 px-6 py-3 bg-purple-500 text-white text-sm font-bold rounded-2xl hover:bg-purple-600 disabled:bg-gray-100 disabled:text-gray-400 transition"
      >
        제출하기
      </button>
    </div>
  );
}

export default function AutobiographyResultPage() {
  const handleDownload = () => {
    window.location.href = "http://localhost:8080/api/v1/autobiography/download";
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <main className="max-w-5xl mx-auto px-6 pt-16">
        {/* 헤더 */}
        <div className="mb-12">
          <h1 className="text-3xl font-bold mb-4">자서전 만들기</h1>
          <p className="text-gray-500">
            인터뷰 음성을 업로드하면 AI가 나만의 자서전을 완성합니다.
          </p>
        </div>

        {/* 스텝 표시 */}
        <div className="flex justify-between items-center mb-16 px-10">
          <StepItem number={<Check size={18} />} label="정보 입력" isDone />
          <div className="flex-1 h-[2px] bg-purple-500 mx-4" />
          <StepItem number={<Check size={18} />} label="처리" isDone />
          <div className="flex-1 h-[2px] bg-purple-500 mx-4" />
          <StepItem number={3} label="결과" isActive />
        </div>

        {/* 완료 배너 */}
        <div className="bg-emerald-50/50 border border-emerald-100 p-8 rounded-[2rem] flex items-center gap-5 mb-8">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center shrink-0">
            <Check size={24} strokeWidth={3} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-emerald-900">
              자서전이 완성되었어요!
            </h2>
            <p className="text-emerald-700/70">
              AI가 인터뷰를 바탕으로 소중한 이야기를 담은 자서전을 만들었습니다.
            </p>
          </div>
        </div>

        {/* PDF 미리보기 영역 */}
        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">미리보기</h3>
          <iframe
            src="http://localhost:8080/api/v1/autobiography/download?inline=true"
            className="w-full rounded-2xl border border-gray-100"
            style={{ height: "600px" }}
            title="자서전 미리보기"
          />
        </div>

        {/* 다운로드 */}
        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">다운로드</h3>
          <button
            onClick={handleDownload}
            className="w-full flex items-center justify-center gap-3 py-5 bg-purple-600 text-white font-bold rounded-2xl hover:bg-purple-700 transition shadow-lg shadow-purple-100"
          >
            <Download size={20} />
            <span>자서전 PDF 다운로드</span>
          </button>
        </div>

        {/* 사용자 평가 */}
        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">자서전 평가</h3>
          <SurveyForm />
        </div>

        {/* 다시 만들기 */}
        <Link href="/autobiography">
          <button className="flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-600 font-bold rounded-2xl hover:bg-gray-200 transition text-sm">
            <ArrowLeft size={16} />
            새 자서전 만들기
          </button>
        </Link>
      </main>
    </div>
  );
}

function StepItem({ number, label, isActive = false, isDone = false }: any) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm
        ${isDone ? "bg-purple-500 text-white" : ""}
        ${isActive ? "bg-purple-600 text-white" : ""}
        ${!isActive && !isDone ? "bg-gray-100 text-gray-400" : ""}
      `}
      >
        {number}
      </div>
      <span
        className={`text-sm font-medium ${
          isActive || isDone ? "text-gray-900" : "text-gray-400"
        }`}
      >
        {label}
      </span>
    </div>
  );
}
