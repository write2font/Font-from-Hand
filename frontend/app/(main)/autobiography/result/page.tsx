"use client";

import { Check, Download, ArrowLeft } from "lucide-react";
import Link from "next/link";
import PageHeader from "@/components/ui/PageHeader";
import StepItem from "@/components/ui/StepItem";
import Button from "@/components/ui/Button";

export default function AutobiographyResultPage() {
  const handleDownload = () => {
    window.location.href = "http://localhost:8080/api/v1/autobiography/download";
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
          <iframe
            src="http://localhost:8080/api/v1/autobiography/download?inline=true"
            className="w-full rounded-2xl border border-gray-100"
            style={{ height: "600px" }}
            title="자서전 미리보기"
          />
        </div>

        <div className="bg-white p-10 rounded-[2.5rem] shadow-sm border border-gray-100 mb-8">
          <h3 className="text-lg font-bold mb-6">다운로드</h3>
          <Button size="lg" onClick={handleDownload} className="flex items-center justify-center gap-3">
            <Download size={20} />
            자서전 PDF 다운로드
          </Button>
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
