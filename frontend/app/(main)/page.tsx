"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authService } from "@/app/lib/axios";
import { PenTool, Sparkles, BookOpen } from "lucide-react";
import ServiceCard from "@/components/ServiceCard";

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string } | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const data = await authService.getMe();
        setUser(data);
      } catch {
        setUser(null);
      }
    };
    checkAuth();
  }, []);

  const handleStart = (href: string) => {
    if (!user) {
      alert("로그인이 필요한 서비스입니다.");
      router.push("/sign-in");
    } else {
      router.push(href);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <main className="max-w-6xl mx-auto px-6 py-20 text-center">
        <h1 className="text-xl font-medium text-gray-500 mb-4">
          원하시는 서비스를 선택하여 시작하세요
        </h1>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-12">
          <ServiceCard
            title="직접 작성 폰트"
            description="템플릿을 작성하여 나만의 정성이 담긴 손글씨 폰트를 만듭니다."
            icon={<PenTool size={40} className="text-brand-500" />}
            tag="무료"
            onStart={() => handleStart("/scan")}
          />
          <ServiceCard
            title="AI 폰트 생성"
            description="적은 수의 글자만으로도 AI가 전체 폰트를 완성합니다."
            icon={<Sparkles size={40} className="text-brand-500" />}
            tag="유료"
            onStart={() => handleStart("/ai-font")}
          />
          <ServiceCard
            title="자서전 제작"
            description="당신의 이야기를 기록하여 특별한 자서전으로 만듭니다."
            icon={<BookOpen size={40} className="text-brand-500" />}
            tag="유료"
            onStart={() => handleStart("/autobiography")}
          />
        </div>
      </main>
    </div>
  );
}
