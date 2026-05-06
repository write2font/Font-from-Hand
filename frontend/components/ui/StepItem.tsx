import { ReactNode } from "react";

interface StepItemProps {
  number: ReactNode;
  label: string;
  isActive?: boolean;
  isDone?: boolean;
}

export default function StepItem({
  number,
  label,
  isActive = false,
  isDone = false,
}: StepItemProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
          isDone
            ? "bg-brand-500 text-white"
            : isActive
            ? "bg-brand-600 text-white"
            : "bg-gray-100 text-gray-400"
        }`}
      >
        {number}
      </div>
      <span
        className={`text-sm font-medium ${
          isActive || isDone ? "text-gray-900" : "text-gray-400"
        }`}
      >
        {label}
      </span>
    </div>
  );
}
