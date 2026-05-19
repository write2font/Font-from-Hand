"use client";

import { useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Loader2, CheckCircle2 } from "lucide-react";
import { CanvasPath } from "react-sketch-canvas";
import api from "@/app/lib/axios";
import DrawingCanvas, { DrawingCanvasHandle } from "@/components/ui/DrawingCanvas";
import Button from "@/components/ui/Button";
import StepItem from "@/components/ui/StepItem";
import { DRAW_CHARACTERS, TOTAL_CHARACTERS } from "@/app/lib/characters";

type Step = "name" | "draw";

export default function DrawPage() {
  const router = useRouter();
  const canvasRef = useRef<DrawingCanvasHandle>(null);

  const [step, setStep] = useState<Step>("name");
  const [fontName, setFontName] = useState("");
  const [fontNameError, setFontNameError] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  // 각 글자의 획 경로 저장 (되돌아왔을 때 복원용)
  const savedPathsRef = useRef<Record<number, CanvasPath[]>>({});
  // 각 글자의 이미지 저장 (최종 제출용)
  const savedImagesRef = useRef<Record<number, string>>({});

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  const drawnCount = Object.keys(savedImagesRef.current).length;

  const saveCurrentCanvas = useCallback(async () => {
    const [paths, image] = await Promise.all([
      canvasRef.current?.exportPaths() ?? Promise.resolve([]),
      canvasRef.current?.exportImage() ?? Promise.resolve(""),
    ]);
    if (paths.length > 0) {
      savedPathsRef.current[currentIndex] = paths;
      savedImagesRef.current[currentIndex] = image;
    }
  }, [currentIndex]);

  const loadCanvas = useCallback((index: number) => {
    canvasRef.current?.clearCanvas();
    const paths = savedPathsRef.current[index];
    if (paths && paths.length > 0) {
      canvasRef.current?.loadPaths(paths);
    }
  }, []);

  const handleNext = async () => {
    await saveCurrentCanvas();
    const next = currentIndex + 1;
    setCurrentIndex(next);
    loadCanvas(next);
  };

  const handlePrev = async () => {
    if (currentIndex === 0) {
      setStep("name");
      return;
    }
    await saveCurrentCanvas();
    const prev = currentIndex - 1;
    setCurrentIndex(prev);
    loadCanvas(prev);
  };

  const handleSubmit = async () => {
    await saveCurrentCanvas();

    const images = savedImagesRef.current;
    if (Object.keys(images).length === 0) {
      alert("최소 한 글자 이상 작성해 주세요!");
      return;
    }

    setIsProcessing(true);
    setProgress(0);

    const interval = setInterval(() => {
      setProgress((prev) => (prev >= 95 ? 95 : prev + 1));
    }, 1500);

    const formData = new FormData();
    for (const [idx, dataUrl] of Object.entries(images)) {
      const res = await fetch(dataUrl);
      const blob = await res.blob();
      formData.append("files", new File([blob], `char_${idx}.png`, { type: "image/png" }));
    }
    formData.append("fontName", fontName.trim());
    formData.append("type", "MANUAL");
    formData.append("drawMode", "true");

    try {
      const response = await api.post("/fonts/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 600000,
      });
      clearInterval(interval);
      setProgress(100);
      localStorage.setItem("lastFontId", response.data.fontId);
      localStorage.setItem("lastFontName", response.data.fontName);
      setTimeout(() => router.push("/scan/result"), 500);
    } catch (error) {
      clearInterval(interval);
      console.error("전송 실패:", error);
      alert("폰트 생성 중 서버 오류가 발생했습니다.");
      setIsProcessing(false);
    }
  };

  const handleStartDraw = () => {
    if (!fontName.trim()) {
      setFontNameError(true);
      return;
    }
    setStep("draw");
  };

  // 로딩 화면
  if (isProcessing) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center pb-20 px-6">
        <div className="bg-white p-12 rounded-[2.5rem] shadow-sm border border-gray-100 max-w-lg w-full text-center animate-in fade-in zoom-in-95 duration-500">
          <div className="w-24 h-24 mx-auto mb-8">
            {progress === 100 ? (
              <CheckCircle2 size={96} className="text-emerald-500 animate-in zoom-in" />
            ) : (
              <Loader2 size={96} className="text-brand-500 animate-spin" />
            )}
          </div>
          <h1 className="text-2xl font-bold mb-4 text-gray-800">
            {progress === 100 ? "폰트 생성 완료!" : "폰트를 생성하고 있어요"}
          </h1>
          <p className="text-gray-500 mb-8">
            {progress === 100
              ? "결과 페이지로 이동합니다..."
              : `${drawnCount}자의 손글씨를 분석하고 있습니다. 잠시만 기다려주세요! (약 3~5분 소요)`}
          </p>
          <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
            <div className="h-full bg-brand-600 transition-all duration-300 ease-out" style={{ width: `${progress}%` }} />
          </div>
          <p className="text-sm font-bold text-brand-600">{progress}%</p>
        </div>
      </div>
    );
  }

  // 폰트 이름 입력 화면
  if (step === "name") {
    return (
      <div className="min-h-screen bg-gray-50 pb-20">
        <main className="max-w-5xl mx-auto px-6 pt-16">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-1 text-gray-400 hover:text-gray-600 mb-8 text-sm transition"
          >
            <ChevronLeft size={18} />
            돌아가기
          </button>

          <h1 className="text-3xl font-bold text-gray-900 mb-2">웹에서 직접 그리기</h1>
          <p className="text-gray-500 mb-12">글자를 하나씩 작성하여 나만의 폰트를 만들어요</p>

          <div className="flex justify-between items-center mb-16 px-10">
            <StepItem number={1} label="폰트 이름" isActive />
            <div className="flex-1 h-px bg-gray-200 mx-4" />
            <StepItem number={2} label="글자 작성" />
            <div className="flex-1 h-px bg-gray-200 mx-4" />
            <StepItem number={3} label="결과" />
          </div>

          <div className="bg-white p-10 rounded-3xl shadow-sm border border-gray-100">
            <label className="block text-sm font-bold text-gray-700 mb-2">
              폰트 이름 <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={fontName}
              onChange={(e) => { setFontName(e.target.value); if (e.target.value.trim()) setFontNameError(false); }}
              onBlur={() => { if (!fontName.trim()) setFontNameError(true); }}
              onKeyDown={(e) => { if (e.key === "Enter") handleStartDraw(); }}
              placeholder="예: 할머니체, 내손글씨"
              autoFocus
              className={`w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 text-gray-800 transition mb-1 ${
                fontNameError ? "border-red-400 focus:ring-red-300" : "border-gray-200 focus:ring-brand-400"
              }`}
            />
            {fontNameError && <p className="text-red-400 text-xs mb-4">폰트 이름을 입력해 주세요.</p>}
            <Button size="lg" onClick={handleStartDraw} className="mt-6">
              글자 작성 시작하기
            </Button>
          </div>
        </main>
      </div>
    );
  }

  // 글자 작성 화면
  const currentChar = DRAW_CHARACTERS[currentIndex];
  const isLast = currentIndex === TOTAL_CHARACTERS - 1;

  return (
    <div className="min-h-screen bg-gray-50 pb-32">
      <main className="max-w-3xl mx-auto px-6 pt-10">
        {/* 상단 헤더 */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="text-xs text-gray-400 mb-1">{fontName}</p>
            <p className="text-sm font-bold text-gray-700">
              {currentIndex + 1} / {TOTAL_CHARACTERS}
              <span className="text-gray-400 font-normal ml-2">({drawnCount}자 완료)</span>
            </p>
          </div>
          <div className="w-40 h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-500 rounded-full transition-all duration-300"
              style={{ width: `${((currentIndex + 1) / TOTAL_CHARACTERS) * 100}%` }}
            />
          </div>
        </div>

        {/* 글자 안내 + 캔버스 */}
        <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-8 mb-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 bg-brand-50 rounded-2xl flex items-center justify-center shrink-0">
              <span className="text-4xl font-bold text-brand-600">{currentChar}</span>
            </div>
            <div>
              <p className="text-xs text-gray-400">이 글자를 아래 캔버스에 작성하세요</p>
              <p className="text-base font-bold text-gray-800">{currentChar}</p>
              <p className="text-xs text-gray-400">
                U+{currentChar.codePointAt(0)?.toString(16).toUpperCase().padStart(4, "0")}
              </p>
            </div>
          </div>
          <DrawingCanvas ref={canvasRef} strokeWidth={4} canvasHeight="380px" />
        </div>
      </main>

      {/* 하단 네비게이션 (고정) */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 px-6 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <button
            onClick={handlePrev}
            className="flex items-center gap-1.5 px-5 py-3 bg-gray-100 text-gray-600 hover:bg-gray-200 rounded-xl font-medium text-sm transition"
          >
            <ChevronLeft size={18} />
            이전
          </button>

          {!isLast ? (
            <button
              onClick={handleNext}
              className="flex-1 flex items-center justify-center gap-1.5 py-3 bg-brand-50 text-brand-600 hover:bg-brand-100 rounded-xl font-bold text-sm transition"
            >
              다음
              <ChevronRight size={18} />
            </button>
          ) : (
            <Button onClick={handleSubmit} className="flex-1">
              폰트 생성하기
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
