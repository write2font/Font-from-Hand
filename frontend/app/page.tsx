import Link from "next/link";
import { PenTool, Sparkles, BookOpen } from "lucide-react";

export default function Home() {
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
            icon={<PenTool size={40} className="text-purple-500" />}
            tag="무료"
            href="/scan"
          />
          <ServiceCard
            title="AI 폰트 생성"
            description="적은 수의 글자만으로도 AI가 전체 폰트를 완성합니다."
            icon={<Sparkles size={40} className="text-purple-500" />}
            tag="유료"
            href="/ai-font"
          />
          <ServiceCard
            title="자서전 제작"
            description="당신의 이야기를 기록하여 특별한 자서전으로 만듭니다."
            icon={<BookOpen size={40} className="text-purple-500" />}
            tag="유료"
            href="/autobiography"
          />
        </div>
      </main>
    </div>
  );
}

function ServiceCard({
  title,
  description,
  icon,
  tag,
  href,
  isPrimary = false,
}: any) {
  return (
    <div
      className={`relative flex flex-col items-center p-10 bg-white rounded-3xl transition-all duration-300 hover:scale-105 ${
        isPrimary
          ? "ring-2 ring-purple-500 shadow-xl"
          : "shadow-md hover:shadow-lg"
      }`}
    >
      <span
        className={`absolute top-6 right-6 px-3 py-1 text-[10px] font-bold rounded-full ${
          isPrimary ? "bg-purple-500 text-white" : "bg-gray-100 text-gray-400"
        }`}
      >
        {tag}
      </span>

      <div className="mb-8 p-4 bg-purple-50 rounded-2xl">{icon}</div>

      <h2 className="text-2xl font-bold mb-4">{title}</h2>
      <p className="text-sm text-gray-500 leading-relaxed mb-10 min-h-[48px]">
        {description}
      </p>

      <Link href={href || "#"} className="w-full">
        <button
          className={`w-full py-4 rounded-2xl font-bold transition ${
            isPrimary
              ? "bg-purple-600 text-white hover:bg-purple-700"
              : "bg-gray-50 text-purple-600 hover:bg-purple-100"
          }`}
        >
          시작하기
        </button>
      </Link>
    </div>
  );
}
