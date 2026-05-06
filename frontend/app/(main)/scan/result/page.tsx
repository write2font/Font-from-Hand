"use client";

import { useEffect, useState } from "react";
import { Check, Download, Info, ArrowRight } from "lucide-react";
import api from "@/app/lib/axios";
import PageHeader from "@/components/ui/PageHeader";
import StepItem from "@/components/ui/StepItem";

export default function ResultPage() {
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

  const handleDownloadWOFF2 = () => {
    alert("WOFF2 변환 기능은 아직 준비 중입니다!");
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <main className="max-w-5xl mx-auto px-6 pt-16">
        <PageHeader
          title="직접 작성 폰트 만들기"
          subtitle="템플릿을 다운로드하고 손글씨를 작성하여 폰트를 제작합니다."
        />

        <div className="flex justify-between items-center mb-16 px-10">
          <StepItem number={<Check size={18} />} label="업로드/작성" isDone />
          <div className="flex-1 h-0.5 bg-brand-500 mx-4" />
          <StepItem number={<Check size={18} />} label="처리" isDone />
          <div className="flex-1 h-0.5 bg-brand-500 mx-4" />
          <StepItem number={3} label="결과" isActive />
        </div>

        <div className="bg-emerald-50/50 border border-emerald-100 p-8 rounded-4xl flex items-center gap-5 mb-8">
          <div className="w-12 h-12 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center shrink-0">
            <Check size={24} strokeWidth={3} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-emerald-900">폰트 생성 완료!</h2>
            <p className="text-emerald-700/70">
              손글씨 폰트가 성공적으로 생성되었습니다. 아래에서 다운로드하세요.
            </p>
          </div>
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-8">폰트 미리보기</h3>
          <div className="bg-gray-50/50 p-12 rounded-3xl border border-dashed border-gray-200 flex flex-col items-center justify-center min-h-62.5">
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
            <DownloadButton label={`${fontName}.ttf`} subLabel="TTF 포맷" onClick={handleDownloadTTF} />
            <DownloadButton label="MyFont.woff2" subLabel="WOFF2 포맷 (웹용)" onClick={handleDownloadWOFF2} />
          </div>
        </div>

        <div className="bg-brand-50/30 p-8 rounded-4xl border border-brand-100">
          <div className="flex items-start gap-4 mb-6">
            <Info className="text-brand-500 mt-1 shrink-0" size={20} />
            <div>
              <h4 className="font-bold text-brand-900 mb-1">무료 서비스 제한 사항</h4>
              <p className="text-sm text-brand-700/80 leading-relaxed">
                무료 서비스는 기본 폰트 생성만 제공되며, 세밀한 글자 수정 기능은
                제한됩니다. <br />더 정확한 폰트를 원하신다면 유료 AI 폰트 생성을 이용해보세요.
              </p>
            </div>
          </div>
          <button className="flex items-center gap-2 px-6 py-3 bg-brand-100 text-brand-600 font-bold rounded-2xl hover:bg-brand-200 transition text-sm">
            AI 폰트 생성 알아보기
            <ArrowRight size={16} />
          </button>
        </div>
      </main>
    </div>
  );
}

function DownloadButton({ label, subLabel, onClick }: { label: string; subLabel: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center justify-center gap-3 py-5 bg-brand-500 text-white font-bold rounded-2xl hover:bg-brand-600 transition shadow-lg shadow-brand-100"
    >
      <Download size={20} />
      <span>{label}</span>
      <span className="text-brand-200 text-xs font-normal ml-1">{subLabel}</span>
    </button>
  );
}
