"use client";

import { useState, useEffect, useRef } from "react";
import { Check, Download, ArrowLeft, Star } from "lucide-react";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import StepItem from "@/components/ui/StepItem";
import Button from "@/components/ui/Button";

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
      <Button
        onClick={() => setSubmitted(true)}
        disabled={ratings.some((r) => r === 0)}
        className="mt-2"
      >
        제출하기
      </Button>
    </div>
  );
}

export default function AutobiographyResultPage() {
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(true);
  const [pdfError, setPdfError] = useState(false);
  const blobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    const autoId = sessionStorage.getItem("autobiography_id");
    const url = autoId
      ? `http://localhost:8080/api/v1/autobiography/download/${autoId}?inline=true`
      : "http://localhost:8080/api/v1/autobiography/download?inline=true";
    fetch(url, {
      credentials: "include",
    })
      .then((r) => {
        if (!r.ok) throw new Error("not ok");
        return r.blob();
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        blobUrlRef.current = url;
        setPdfBlobUrl(url);
      })
      .catch(() => setPdfError(true))
      .finally(() => setPdfLoading(false));

    return () => {
      if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current);
    };
  }, []);

  const handleDownload = () => {
    if (pdfBlobUrl) {
      const a = document.createElement("a");
      a.href = pdfBlobUrl;
      a.download = "autobiography.pdf";
      a.click();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <main className="max-w-5xl mx-auto px-6 pt-16">
        <PageHeader
          title="자서전 만들기"
          subtitle="인터뷰 음성을 업로드하면 AI가 나만의 자서전을 완성합니다."
        />

        <div className="flex justify-between items-center mb-16 px-10">
          <StepItem number={<Check size={18} />} label="정보 입력" isDone />
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
            <h2 className="text-xl font-bold text-emerald-900">자서전이 완성되었어요!</h2>
            <p className="text-emerald-700/70">
              AI가 인터뷰를 바탕으로 소중한 이야기를 담은 자서전을 만들었습니다.
            </p>
          </div>
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">미리보기</h3>
          {pdfLoading ? (
            <div className="w-full flex items-center justify-center bg-gray-50 rounded-2xl border border-gray-100" style={{ height: "600px" }}>
              <div className="flex flex-col items-center gap-3 text-gray-400">
                <div className="w-8 h-8 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
                <span className="text-sm">PDF 불러오는 중...</span>
              </div>
            </div>
          ) : pdfError || !pdfBlobUrl ? (
            <div className="w-full flex items-center justify-center bg-gray-50 rounded-2xl border border-gray-100" style={{ height: "600px" }}>
              <p className="text-sm text-gray-400">미리보기를 불러올 수 없습니다. 아래에서 다운로드해 주세요.</p>
            </div>
          ) : (
            <iframe
              src={pdfBlobUrl}
              className="w-full rounded-2xl border border-gray-100"
              style={{ height: "600px" }}
              title="자서전 미리보기"
            />
          )}
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">다운로드</h3>
          <Button size="lg" onClick={handleDownload} className="flex items-center justify-center gap-3">
            <Download size={20} />
            자서전 PDF 다운로드
          </Button>
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">자서전 평가</h3>
          <SurveyForm />
        </div>

        <Link href="/autobiography">
          <Button variant="ghost" className="flex items-center gap-2">
            <ArrowLeft size={16} />
            새 자서전 만들기
          </Button>
        </Link>
      </main>
    </div>
  );
}
