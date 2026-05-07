import { ReactNode } from "react";

interface ServiceCardProps {
  title: string;
  description: string;
  icon: ReactNode;
  tag: string;
  onStart: () => void;
  isPrimary?: boolean;
}

export default function ServiceCard({
  title,
  description,
  icon,
  tag,
  onStart,
  isPrimary = false,
}: ServiceCardProps) {
  return (
    <div
      className={`relative flex flex-col items-center p-10 bg-white rounded-3xl transition-all duration-300 hover:scale-105 ${
        isPrimary ? "ring-2 ring-brand-500 shadow-xl" : "shadow-md hover:shadow-lg"
      }`}
    >
      <span
        className={`absolute top-6 right-6 px-3 py-1 text-[10px] font-bold rounded-full ${
          isPrimary ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-400"
        }`}
      >
        {tag}
      </span>
      <div className="mb-8 p-4 bg-brand-50 rounded-2xl">{icon}</div>
      <h2 className="text-2xl font-bold mb-4">{title}</h2>
      <p className="text-sm text-gray-500 leading-relaxed mb-10 min-h-12">
        {description}
      </p>
      <button
        onClick={onStart}
        className={`w-full py-4 rounded-2xl font-bold transition active:scale-95 ${
          isPrimary
            ? "bg-brand-600 text-white hover:bg-brand-700"
            : "bg-gray-50 text-brand-600 hover:bg-brand-100"
        }`}
      >
        시작하기
      </button>
    </div>
  );
}
