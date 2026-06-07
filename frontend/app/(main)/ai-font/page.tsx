"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  Download,
  FileImage,
  Info,
  Loader2,
  UploadCloud,
  X,
  Zap,
} from "lucide-react";
import axios from "axios";
import api from "@/app/lib/axios";
import { useRouter } from "next/navigation";
import StepItem from "@/components/ui/StepItem";
import Button from "@/components/ui/Button";

const SAMPLE_CHARS =
  "값 같 곬 곶 깎 넋 녘 늪 닫 닭 닻 됩 뗌 략 몃 밟 볘 뺐 뽈 솩 쐐 앉 않 얘 얾 엌 옳 우 읊 좋 죡 쮜 춰 츄 퀭 틔 핀 핥";

export default function AiFontPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fontName, setFontName] = useState("");
  const [fontNameError, setFontNameError] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(() => {
        setProgress((prev) => (prev >= 95 ? 95 : prev + 1));
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) setSelectedFile(file);
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleSubmit = async () => {
    if (!selectedFile) {
      alert("샘플 이미지를 업로드해 주세요.");
      return;
    }
    if (!fontName.trim()) {
      setFontNameError(true);
      return;
    }

    setIsProcessing(true);
    setProgress(0);

    const formData = new FormData();
    formData.append("files", selectedFile);
    formData.append("fontName", fontName.trim());
    formData.append("type", "AI");

    try {
      const response = await api.post("/fonts/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 1800000,
      });
      setProgress(100);
      localStorage.setItem("lastFontId", response.data.fontId);
      localStorage.setItem("lastFontName", response.data.fontName);
      setTimeout(() => router.push("/ai-font/result"), 500);
    } catch (error) {
      console.error("AI font upload failed:", error);
      const message = axios.isAxiosError(error)
        ? typeof error.response?.data === "string"
          ? error.response.data
          : error.message
        : "폰트 생성 중 서버 오류가 발생했습니다.";
      alert(message || "폰트 생성 중 서버 오류가 발생했습니다.");
      setIsProcessing(false);
    }
  };

  if (isProcessing) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center pb-20 px-6">
        <div className="bg-white p-12 rounded-[2.5rem] shadow-sm border border-gray-100 max-w-lg w-full text-center animate-in fade-in zoom-in-95 duration-500">
          <div className="relative w-24 h-24 mx-auto mb-8">
            {progress === 100 ? (
              <CheckCircle2 size={96} className="text-emerald-500 animate-in zoom-in" />
            ) : (
              <Loader2 size={96} className="text-brand-500 animate-spin" />
            )}
          </div>
          <h1 className="text-2xl font-bold mb-4 text-gray-800">
            {progress === 100 ? "폰트 생성 완료" : "AI가 폰트를 생성하고 있어요"}
          </h1>
          <p className="text-gray-500 mb-8">
            {progress === 100
              ? "결과 페이지로 이동합니다."
              : "38자 샘플을 분석해 DM-Font로 글자를 생성 중입니다. CPU 환경에서는 시간이 오래 걸릴 수 있습니다."}
          </p>
          <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
            <div
              className="h-full bg-brand-600 transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm font-bold text-brand-600">{progress}%</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <main className="max-w-5xl mx-auto px-6 pt-16">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">AI 폰트 생성</h1>
            <p className="text-gray-500 mt-2">
              DM-Font가 38자 손글씨 샘플을 참고해 나머지 글자를 생성합니다.
            </p>
          </div>
          <span className="mt-1 px-3 py-1 bg-brand-100 text-brand-600 text-xs font-bold rounded-full">
            DM-Font
          </span>
        </div>

        <div className="flex justify-between items-center my-12 px-10">
          <StepItem number={1} label="샘플 업로드" isActive />
          <div className="flex-1 h-px bg-gray-200 mx-4" />
          <StepItem number={2} label="AI 처리" />
          <div className="flex-1 h-px bg-gray-200 mx-4" />
          <StepItem number={3} label="결과" />
        </div>

        <div className="bg-brand-50 border border-brand-100 p-6 rounded-3xl flex items-start gap-4 mb-6">
          <div className="w-10 h-10 bg-brand-100 text-brand-600 rounded-2xl flex items-center justify-center shrink-0">
            <Zap size={20} />
          </div>
          <div>
            <h3 className="font-bold text-brand-900 mb-1">AI 생성 안내</h3>
            <p className="text-sm text-brand-700/80 leading-relaxed">
              업로드한 샘플지는 네 모서리 마커로 보정한 뒤, 11x17 격자의 앞 38칸을
              `ref_chars.json` 순서대로 잘라 DM-Font에 전달합니다.
            </p>
          </div>
        </div>

        <div className="bg-white p-10 rounded-3xl shadow-sm border border-gray-100 mb-6">
          <div className="flex items-center gap-2 mb-4 text-brand-600 font-bold">
            <Info size={18} />
            <span>작성할 38자</span>
          </div>
          <p className="text-xl font-medium text-gray-800 mb-5 leading-9 break-keep">
            {SAMPLE_CHARS}
          </p>
          <ul className="space-y-2 text-sm text-gray-500 mb-8">
            <li>템플릿의 마커와 격자 형식이 보이도록 촬영해 주세요.</li>
            <li>왼쪽 위 첫 칸부터 오른쪽으로, 줄이 바뀌면 다음 줄 왼쪽부터 작성해 주세요.</li>
            <li>38자 이후의 빈 칸은 작성하지 않아도 됩니다.</li>
            <li>글자는 진하게 쓰고, 촬영할 때 네 모서리 마커가 모두 보이게 해 주세요.</li>
          </ul>
          <div className="flex flex-wrap gap-3">
            <a
              href="/templates/ai_sample_template.pdf"
              download
              className="inline-flex items-center gap-2 px-6 py-3 bg-brand-600 text-white font-bold rounded-xl hover:bg-brand-700 transition"
            >
              <Download size={18} />
              PDF 템플릿 다운로드
            </a>
            <a
              href="/templates/ai_sample_template.png"
              download
              className="inline-flex items-center gap-2 px-6 py-3 bg-white border border-gray-200 text-gray-700 font-bold rounded-xl hover:bg-gray-50 transition"
            >
              <FileImage size={18} />
              PNG 템플릿 다운로드
            </a>
          </div>
        </div>

        <div className="bg-white p-10 rounded-3xl shadow-sm border border-gray-100 mb-8">
          <h2 className="text-sm font-bold text-gray-700 mb-4">샘플 이미지 업로드</h2>
          <input
            type="file"
            accept="image/*"
            className="hidden"
            ref={fileInputRef}
            onChange={handleFileChange}
          />

          {selectedFile ? (
            <div className="flex items-center justify-between p-5 bg-brand-50 rounded-2xl border border-brand-100">
              <div className="flex items-center gap-3 truncate">
                <div className="w-9 h-9 bg-brand-100 text-brand-600 flex items-center justify-center rounded-xl font-bold text-xs shrink-0">
                  IMG
                </div>
                <span className="text-sm text-gray-700 truncate">{selectedFile.name}</span>
              </div>
              <button
                onClick={clearSelectedFile}
                className="text-gray-400 hover:text-red-500 transition ml-2 shrink-0"
                aria-label="선택한 파일 제거"
              >
                <X size={18} />
              </button>
            </div>
          ) : (
            <div
              onClick={() => fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              className="border-2 border-dashed border-gray-200 rounded-3xl py-20 flex flex-col items-center justify-center cursor-pointer hover:border-brand-300 hover:bg-brand-50 transition group"
            >
              <UploadCloud size={48} className="text-gray-300 mb-4 group-hover:text-brand-400" />
              <p className="text-gray-600 font-medium mb-1">38자 샘플지를 촬영한 이미지를 업로드하세요</p>
              <p className="text-gray-400 text-xs">최대 20MB</p>
            </div>
          )}

          <div className="mt-8">
            <label className="block text-sm font-bold text-gray-700 mb-2">
              폰트 이름 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={fontName}
              onChange={(e) => {
                setFontName(e.target.value);
                if (e.target.value.trim()) setFontNameError(false);
              }}
              onBlur={() => {
                if (!fontName.trim()) setFontNameError(true);
              }}
              placeholder="예: 나의 손글씨"
              className={`w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 text-gray-800 transition ${
                fontNameError
                  ? "border-red-400 focus:ring-red-300"
                  : "border-gray-200 focus:ring-brand-400"
              }`}
            />
            {fontNameError && (
              <p className="text-red-400 text-xs mt-1.5">폰트 이름을 입력해 주세요.</p>
            )}
          </div>

          <Button size="lg" onClick={handleSubmit} className="mt-10">
            AI 폰트 생성 시작하기
          </Button>
        </div>
      </main>
    </div>
  );
}
