"use client";

import { useState, useEffect, useRef } from "react";
import { Check, Download, ArrowLeft, Star } from "lucide-react";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import StepItem from "@/components/ui/StepItem";
import Button from "@/components/ui/Button";
import api from "@/app/lib/axios";

const SURVEY_QUESTIONS: { key: string; label: string }[] = [
  { key: "원자료충실",      label: "내가 말한 내용이 자서전에 충실하게 담겼나요?" },
  { key: "할루시네이션위험도", label: "실제로 말한 내용만 담겨 있나요?" },
  { key: "감정표현적합성",   label: "AI가 내 감정과 경험을 적절하게 표현했나요?" },
  { key: "화자고유성",      label: "이 자서전이 나만의 고유한 이야기처럼 느껴지나요?" },
  { key: "챕터구성연결성",   label: "챕터 간 내용이 자연스럽게 이어지나요?" },
  { key: "문장자연스러움",   label: "글이 자연스럽게 읽히나요?" },
  { key: "제목목차전달력",   label: "제목과 목차를 봤을 때 이 자서전이 잘 전달된다고 느껴지나요?" },
];

const STAR_LABELS = ["매우 아니다", "아니다", "보통이다", "그렇다", "매우 그렇다"];

function SurveyForm() {
  const [ratings, setRatings]     = useState<Record<string, number>>(
    Object.fromEntries(SURVEY_QUESTIONS.map((q) => [q.key, 0]))
  );
  const [freeText, setFreeText]   = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const allAnswered = Object.values(ratings).every((r) => r > 0);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const autoId = sessionStorage.getItem("autobiography_id");
      if (autoId) {
        await api.post(`/autobiography/${autoId}/survey`, { ratings, freeText });
      }
    } catch {
      // 저장 실패해도 감사 메시지는 표시
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  };

  if (submitted) return (
    <div className="text-center py-10">
      <div className="w-12 h-12 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4">
        <Check size={24} strokeWidth={3} />
      </div>
      <p className="text-emerald-700 font-semibold text-lg">소중한 의견 감사합니다!</p>
      <p className="text-gray-400 text-sm mt-1">더 나은 자서전을 만드는 데 큰 도움이 됩니다.</p>
    </div>
  );

  return (
    <div>
      <p className="text-sm text-gray-500 mb-8">
        AI 자서전의 품질을 평가해 주세요. 모든 항목에 응답해야 제출할 수 있어요.
      </p>

      <div className="space-y-8">
        {SURVEY_QUESTIONS.map((q, qi) => (
          <div key={q.key} className="border-b border-gray-100 pb-7 last:border-0">
            <div className="flex gap-3 mb-4">
              <span className="text-xs font-bold text-emerald-500 bg-emerald-50 rounded-full w-6 h-6 flex items-center justify-center shrink-0 mt-0.5">
                {qi + 1}
              </span>
              <p className="text-sm font-medium text-gray-800 leading-relaxed">{q.label}</p>
            </div>
            <div className="flex items-center gap-2 pl-9">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => setRatings((prev) => ({ ...prev, [q.key]: star }))}
                  className="flex flex-col items-center gap-1 group"
                >
                  <Star
                    size={28}
                    className={
                      star <= ratings[q.key]
                        ? "text-yellow-400 fill-yellow-400"
                        : "text-gray-200 group-hover:text-yellow-200 group-hover:fill-yellow-100 transition-colors"
                    }
                  />
                  <span className="text-[10px] text-gray-400 hidden sm:block">{star}</span>
                </button>
              ))}
              {ratings[q.key] > 0 && (
                <span className="ml-2 text-xs text-gray-400 italic">
                  {STAR_LABELS[ratings[q.key] - 1]}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <p className="text-sm font-medium text-gray-800 mb-2">자유롭게 의견을 남겨주세요 <span className="text-gray-400 font-normal">(선택)</span></p>
        <textarea
          value={freeText}
          onChange={(e) => setFreeText(e.target.value)}
          placeholder="불편했던 점, 개선됐으면 하는 점, 좋았던 점 무엇이든 환영합니다."
          rows={4}
          className="w-full rounded-2xl border border-gray-200 px-4 py-3 text-sm text-gray-700 resize-none focus:outline-none focus:ring-2 focus:ring-emerald-300"
        />
      </div>

      <div className="mt-6 flex items-center gap-4">
        <Button
          onClick={handleSubmit}
          disabled={!allAnswered || submitting}
          className="flex items-center gap-2"
        >
          {submitting ? "저장 중..." : "평가 제출하기"}
        </Button>
        {!allAnswered && (
          <p className="text-xs text-gray-400">모든 항목에 별점을 선택해 주세요.</p>
        )}
      </div>
    </div>
  );
}

export default function AutobiographyResultPage() {
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(true);
  const [pdfError, setPdfError]     = useState(false);
  const blobUrlRef = useRef<string | null>(null);

  useEffect(() => {
    const autoId = sessionStorage.getItem("autobiography_id");
    const endpoint = autoId
      ? `/autobiography/download/${autoId}?inline=true`
      : `/autobiography/download?inline=true`;

    api.get(endpoint, { responseType: "blob" })
      .then((res) => {
        const objectUrl = URL.createObjectURL(res.data);
        blobUrlRef.current = objectUrl;
        setPdfBlobUrl(objectUrl);
      })
      .catch(() => setPdfError(true))
      .finally(() => setPdfLoading(false));

    return () => { if (blobUrlRef.current) URL.revokeObjectURL(blobUrlRef.current); };
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
          <h3 className="text-lg font-bold mb-2">다운로드</h3>
          <p className="text-sm text-gray-400 mb-6">PDF 파일로 저장하거나 인쇄하실 수 있습니다.</p>
          <Button size="lg" onClick={handleDownload} className="flex items-center justify-center gap-3">
            <Download size={20} />
            자서전 PDF 다운로드
          </Button>
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-1">자서전 품질 평가</h3>
          <p className="text-xs text-gray-400 mb-6">연구 목적으로 수집되며 서비스 개선에 활용됩니다.</p>
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
