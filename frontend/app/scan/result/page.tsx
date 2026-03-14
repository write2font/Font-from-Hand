"use client";

import React from "react";
import { Check, Download, Info, ArrowRight } from "lucide-react";

export default function ResultPage() {
  const handleDownloadTTF = () => {
    const downloadUrl = "http://localhost:8080/api/v1/fonts/download";
    window.location.href = downloadUrl;
  };

  const handleDownloadWOFF2 = () => {
    alert("WOFF2 변환 기능은 아직 준비 중입니다!");
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <main className="max-w-5xl mx-auto px-6 pt-16">
        <div className="mb-12">
          <h1 className="text-3xl font-bold mb-4">직접 작성 폰트 만들기</h1>
          <p className="text-gray-500">
            템플릿을 다운로드하고 손글씨를 작성하여 폰트를 제작합니다.
          </p>
        </div>

        <div className="flex justify-between items-center mb-16 px-10">
          <StepItem
            number={<Check size={18} />}
            label="업로드/작성"
            isDone={true}
          />
          <div className="flex-1 h-[2px] bg-indigo-500 mx-4" />
          <StepItem number={<Check size={18} />} label="처리" isDone={true} />
          <div className="flex-1 h-[2px] bg-indigo-500 mx-4" />
          <StepItem number={3} label="결과" isActive={true} />
        </div>

        <div className="bg-emerald-50/50 border border-emerald-100 p-8 rounded-[2rem] flex items-center gap-5 mb-8">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center shrink-0">
            <Check size={24} strokeWidth={3} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-emerald-900">
              폰트 생성 완료!
            </h2>
            <p className="text-emerald-700/70">
              손글씨 폰트가 성공적으로 생성되었습니다. 아래에서 다운로드하세요.
            </p>
          </div>
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-8">폰트 미리보기</h3>
          <div className="bg-gray-50/50 p-12 rounded-3xl border border-dashed border-gray-200 flex flex-col items-center justify-center min-h-[250px]">
            <p className="text-4xl text-gray-800 mb-6 leading-relaxed text-center font-serif">
              손글씨 폰트로 작성된 샘플입니다
            </p>
            <p className="text-2xl text-gray-400 text-center font-serif">
              가나다라마바사아자차카타파하
            </p>
            <p className="mt-8 text-xs text-gray-300 italic">
              * 실제 폰트가 적용된 미리보기가 표시됩니다
            </p>
          </div>
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">다운로드</h3>
          <div className="flex flex-col gap-4">
            <DownloadButton
              label="MyFont.ttf"
              subLabel="TTF 포맷"
              onClick={handleDownloadTTF}
            />
            <DownloadButton
              label="MyFont.woff2"
              subLabel="WOFF2 포맷 (웹용)"
              onClick={handleDownloadWOFF2}
            />
          </div>
        </div>

        <div className="bg-indigo-50/30 p-8 rounded-[2rem] border border-indigo-100">
          <div className="flex items-start gap-4 mb-6">
            <Info className="text-indigo-500 mt-1 shrink-0" size={20} />
            <div>
              <h4 className="font-bold text-indigo-900 mb-1">
                무료 서비스 제한 사항
              </h4>
              <p className="text-sm text-indigo-700/80 leading-relaxed">
                무료 서비스는 기본 폰트 생성만 제공되며, 세밀한 글자 수정 기능은
                제한됩니다. <br />더 정확한 폰트를 원하신다면 유료 AI 폰트
                생성을 이용해보세요.
              </p>
            </div>
          </div>
          <button className="flex items-center gap-2 px-6 py-3 bg-indigo-100 text-indigo-600 font-bold rounded-2xl hover:bg-indigo-200 transition text-sm">
            AI 폰트 생성 알아보기
            <ArrowRight size={16} />
          </button>
        </div>
      </main>
    </div>
  );
}

function StepItem({ number, label, isActive = false, isDone = false }: any) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm
        ${isDone ? "bg-indigo-500 text-white" : ""}
        ${isActive ? "bg-indigo-600 text-white" : ""}
        ${!isActive && !isDone ? "bg-gray-100 text-gray-400" : ""}
      `}
      >
        {number}
      </div>
      <span
        className={`text-sm font-medium ${isActive || isDone ? "text-gray-900" : "text-gray-400"}`}
      >
        {label}
      </span>
    </div>
  );
}

function DownloadButton({ label, subLabel, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-center gap-3 py-5 bg-indigo-500 text-white font-bold rounded-2xl hover:bg-indigo-600 transition shadow-lg shadow-indigo-100"
    >
      <Download size={20} />
      <span>{label}</span>
      <span className="text-indigo-200 text-xs font-normal ml-1">
        {subLabel}
      </span>
    </button>
  );
}
