"use client";

import React, { useRef, useState, useEffect } from "react";
import {
  Image as ImageIcon,
  PencilLine,
  Download,
  UploadCloud,
  Info,
  X,
  Loader2,
  CheckCircle2,
} from "lucide-react";
import axios from "axios";
import { useRouter } from "next/navigation";

export default function ScanPage() {
  const router = useRouter();
  const [selectedMethod, setSelectedMethod] = useState<
    "upload" | "draw" | null
  >(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 95) return 95;
          return prev + 1;
        });
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  const onUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      setSelectedFiles((prev) => [...prev, ...filesArray]);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleStartGeneration = async () => {
    if (selectedFiles.length === 0) {
      alert("파일을 먼저 업로드해 주세요!");
      return;
    }

    setIsProcessing(true);
    setProgress(0);

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append("files", file);
    });

    try {
      const response = await axios.post(
        "http://localhost:8080/api/v1/fonts/upload",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        },
      );
      if (response.status === 200) {
        setProgress(100);
        setTimeout(() => {
          alert("성공적으로 폰트가 생성되었습니다!");
          router.push("/scan/result");
        }, 500);
      }
    } catch (error) {
      console.error("전송 실패:", error);
      alert("폰트 생성 중 서버 오류가 발생했습니다.");
      setIsProcessing(false);
    }
  };

  if (isProcessing) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center pb-20 px-6">
        <div className="bg-white p-12 rounded-[2.5rem] shadow-sm border border-gray-100 max-w-lg w-full text-center animate-in fade-in zoom-in-95 duration-500">
          <div className="relative w-24 h-24 mx-auto mb-8">
            {progress === 100 ? (
              <CheckCircle2
                size={96}
                className="text-emerald-500 animate-in zoom-in"
              />
            ) : (
              <Loader2 size={96} className="text-purple-500 animate-spin" />
            )}
          </div>

          <h1 className="text-2xl font-bold mb-4 text-gray-800">
            {progress === 100 ? "폰트 생성 완료!" : "폰트를 생성하고 있어요"}
          </h1>
          <p className="text-gray-500 mb-8">
            {progress === 100
              ? "결과 페이지로 이동합니다..."
              : "글자를 분석하고 조합하는 중입니다. 창을 닫지 말고 잠시만 기다려주세요! (약 3~5분 소요)"}
          </p>

          <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
            <div
              className="h-full bg-purple-600 transition-all duration-300 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-sm font-bold text-purple-600">{progress}%</p>
        </div>
      </div>
    );
  }
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
          <StepItem number={1} label="업로드/작성" isActive={true} />
          <div className="flex-1 h-[1px] bg-gray-200 mx-4" />
          <StepItem number={2} label="처리" />
          <div className="flex-1 h-[1px] bg-gray-200 mx-4" />
          <StepItem number={3} label="결과" />
        </div>

        <div className="bg-white p-10 rounded-3xl shadow-sm border border-gray-100 mb-8">
          <h2 className="text-xl font-bold mb-8">작성 방법 선택</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <MethodCard
              icon={<ImageIcon size={32} />}
              title="템플릿 촬영 업로드"
              description="템플릿을 다운로드하고 작성 후 촬영하여 업로드합니다."
              isSelected={selectedMethod === "upload"}
              onClick={() => setSelectedMethod("upload")}
            />
            <MethodCard
              icon={<PencilLine size={32} />}
              title="웹에서 직접 그리기"
              description="브라우저에서 마우스나 태블릿으로 직접 작성합니다."
              isSelected={selectedMethod === "draw"}
              onClick={() => setSelectedMethod("draw")}
            />
          </div>
        </div>

        {selectedMethod === "upload" && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white p-10 rounded-3xl shadow-sm border border-gray-100">
              <div className="flex items-center gap-2 mb-6 text-purple-600 font-bold">
                <Info size={20} />
                <span>촬영 가이드</span>
              </div>
              <ul className="space-y-3 text-gray-500 text-sm mb-8">
                <li>• 밝은 조명 아래에서 그림자 없이 촬영하세요.</li>
                <li>• 템플릿을 정면에서 찍어주세요 (기울지 않게).</li>
                <li>• 해상도는 최소 1200x1200 이상을 권장합니다.</li>
                <li>• JPG, PNG 형식을 지원합니다.</li>
              </ul>
              <button className="flex items-center gap-2 px-6 py-3 bg-purple-100 text-purple-600 font-bold rounded-xl hover:bg-purple-200 transition">
                <Download size={18} />
                템플릿 다운로드 (PDF)
              </button>
            </div>
            <div className="bg-white p-10 rounded-3xl shadow-sm border border-gray-100">
              <h2 className="text-lg font-bold mb-6">템플릿 이미지 업로드</h2>
              <input
                type="file"
                multiple
                className="hidden"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/*"
              />

              <div
                onClick={onUploadClick}
                className="border-2 border-dashed border-gray-200 rounded-3xl py-20 flex flex-col items-center justify-center cursor-pointer hover:border-purple-300 hover:bg-purple-50 transition group"
              >
                <UploadCloud
                  size={48}
                  className="text-gray-300 mb-4 group-hover:text-purple-400"
                />
                <p className="text-gray-600 font-medium mb-1">
                  클릭하여 이미지들을 선택하세요
                </p>
                <p className="text-gray-400 text-xs">최대 18장 권장</p>
              </div>

              {selectedFiles.length > 0 && (
                <div className="mt-10">
                  <h3 className="text-sm font-bold text-gray-400 mb-4 uppercase tracking-wider">
                    선택된 파일 ({selectedFiles.length})
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    {selectedFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl border border-gray-100"
                      >
                        <div className="flex items-center gap-3 truncate">
                          <div className="w-8 h-8 bg-purple-100 text-purple-600 flex items-center justify-center rounded-lg font-bold text-xs shrink-0">
                            {index + 1}
                          </div>
                          <span className="text-sm text-gray-700 truncate">
                            {file.name}
                          </span>
                        </div>
                        <button
                          onClick={() => removeFile(index)}
                          className="text-gray-400 hover:text-red-500 transition ml-2"
                        >
                          <X size={18} />
                        </button>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={handleStartGeneration}
                    className="w-full mt-10 py-5 bg-purple-600 text-white font-bold rounded-2xl hover:bg-purple-700 transition shadow-lg shadow-purple-100"
                  >
                    폰트 생성 시작하기
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function StepItem({ number, label, isActive = false }: any) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${isActive ? "bg-purple-600 text-white" : "bg-gray-100 text-gray-400"}`}
      >
        {number}
      </div>
      <span
        className={`text-sm font-medium ${isActive ? "text-gray-900" : "text-gray-400"}`}
      >
        {label}
      </span>
    </div>
  );
}

function MethodCard({ icon, title, description, isSelected, onClick }: any) {
  return (
    <div
      onClick={onClick}
      className={`p-8 rounded-2xl border-2 cursor-pointer transition-all ${isSelected ? "border-purple-500 bg-purple-50/30 shadow-inner" : "border-gray-100 hover:border-purple-200"}`}
    >
      <div
        className={`mb-4 ${isSelected ? "text-purple-600" : "text-gray-400"}`}
      >
        {icon}
      </div>
      <h3 className="text-lg font-bold mb-2">{title}</h3>
      <p className="text-sm text-gray-500">{description}</p>
    </div>
  );
}
