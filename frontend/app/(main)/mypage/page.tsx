"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, FileText } from "lucide-react";
import api from "@/app/lib/axios";
import PageHeader from "@/components/ui/PageHeader";
import Button from "@/components/ui/Button";

interface Font {
  fontId: string;
  fontName: string;
  type: string;
  createdAt: string;
}

export default function MyPage() {
  const router = useRouter();
  const [fonts, setFonts] = useState<Font[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchFonts = async () => {
      try {
        const response = await api.get("/fonts/list");
        setFonts(response.data);
      } catch (error: any) {
        if (error.response?.status === 401) {
          router.push("/sign-in");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchFonts();
  }, [router]);

  const handleDownload = async (fontId: string, fontName: string) => {
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
      <main className="max-w-4xl mx-auto px-6 pt-16">
        <PageHeader title="마이페이지" subtitle="내가 만든 폰트를 확인하고 다운로드하세요." />

        <section>
          <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
            <FileText size={20} className="text-brand-500" />
            내 폰트 목록
          </h2>

          {loading ? (
            <div className="text-center py-20 text-gray-400">불러오는 중...</div>
          ) : fonts.length === 0 ? (
            <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-16 text-center">
              <p className="text-gray-400 mb-6">아직 만든 폰트가 없어요.</p>
              <Button onClick={() => router.push("/scan")}>
                폰트 만들러 가기
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {fonts.map((font) => (
                <div
                  key={font.fontId}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm px-8 py-6 flex items-center justify-between"
                >
                  <div>
                    <p className="text-lg font-bold text-gray-800">{font.fontName}</p>
                    <p className="text-sm text-gray-400 mt-1">
                      {font.type === "MANUAL" ? "직접 작성" : "AI 생성"} •{" "}
                      {new Date(font.createdAt).toLocaleDateString("ko-KR")}
                    </p>
                  </div>
                  <Button
                    onClick={() => handleDownload(font.fontId, font.fontName)}
                    className="flex items-center gap-2"
                  >
                    <Download size={16} />
                    TTF 다운로드
                  </Button>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
