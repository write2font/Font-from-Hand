"use client";

import { useEffect, useState } from "react";
import { Check, Download, Zap } from "lucide-react";
import api from "@/app/lib/axios";
import StepItem from "@/components/ui/StepItem";
import Button from "@/components/ui/Button";

export default function AiFontResultPage() {
  const [fontId, setFontId] = useState<string | null>(null);
  const [fontName, setFontName] = useState("MyFont");

  useEffect(() => {
    const id = localStorage.getItem("lastFontId");
    const name = localStorage.getItem("lastFontName");
    if (id) setFontId(id);
    if (name) setFontName(name);
  }, []);

  const handleDownloadTTF = async () => {
    if (!fontId) {
      alert("다운로드할 폰트 정보가 없습니다.");
      return;
    }
    try {
      const response = await api.get(`/fonts/download/${fontId}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${fontName}.ttf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      alert("다운로드 중 오류가 발생했습니다.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <main className="max-w-5xl mx-auto px-6 pt-16">
        {/* 헤더 */}
        <div className="flex items-start justify-between mb-2">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI 폰트 생성</h1>
            <p className="text-gray-500 mt-2">20자만 작성하면 AI가 2,350자 전체를 자동으로 생성합니다</p>
          </div>
          <span className="mt-1 px-3 py-1 bg-brand-100 text-brand-600 text-xs font-bold rounded-full">
            유료
          </span>
        </div>

        {/* 스텝 */}
        <div className="flex justify-between items-center my-12 px-10">
          <StepItem number={<Check size={18} />} label="샘플 업로드" isDone />
          <div className="flex-1 h-0.5 bg-brand-500 mx-4" />
          <StepItem number={<Check size={18} />} label="AI 처리" isDone />
          <div className="flex-1 h-0.5 bg-brand-500 mx-4" />
          <StepItem number={3} label="결과" isActive />
        </div>

        {/* 완료 배너 */}
        <div className="bg-emerald-50/50 border border-emerald-100 p-8 rounded-4xl flex items-center gap-5 mb-8">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center shrink-0">
            <Check size={24} strokeWidth={3} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-emerald-900">AI 폰트 생성 완료!</h2>
            <p className="text-emerald-700/70">
              AI가 20자 샘플을 분석하여 2,350자 전체 폰트를 완성했습니다.
            </p>
          </div>
        </div>

        {/* 미리보기 */}
        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-8">폰트 미리보기</h3>
          <div className="bg-gray-50/50 p-12 rounded-3xl border border-dashed border-gray-200 flex flex-col items-center justify-center min-h-62.5">
            <p className="text-4xl text-gray-800 mb-6 leading-relaxed text-center font-serif">
              AI가 만든 나만의 손글씨 폰트
            </p>
            <p className="text-2xl text-gray-400 text-center font-serif">
              가나다라마바사아자차카타파하
            </p>
            <p className="mt-8 text-xs text-gray-300 italic">
              * 실제 폰트가 적용된 미리보기가 표시됩니다
            </p>
          </div>
        </div>

        {/* 다운로드 */}
        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">다운로드</h3>
          <div className="flex flex-col gap-4">
            <Button size="lg" onClick={handleDownloadTTF} className="flex items-center justify-center gap-3">
              <Download size={20} />
              <span>{fontName}.ttf</span>
              <span className="text-brand-200 text-xs font-normal ml-1">TTF 포맷</span>
            </Button>
          </div>
        </div>

        {/* AI 생성 정보 */}
        <div className="bg-brand-50/30 p-8 rounded-4xl border border-brand-100">
          <div className="flex items-start gap-4">
            <div className="w-10 h-10 bg-brand-100 text-brand-600 rounded-2xl flex items-center justify-center shrink-0">
              <Zap size={20} />
            </div>
            <div>
              <h4 className="font-bold text-brand-900 mb-1">AI 폰트 생성 완료</h4>
              <p className="text-sm text-brand-700/80 leading-relaxed">
                20자 샘플을 기반으로 2,350자 전체 글자가 AI에 의해 생성되었습니다.
                생성된 TTF 파일을 다운로드하여 바로 사용하실 수 있습니다.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
