import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variants: Record<Variant, string> = {
  primary: "bg-brand-600 text-white hover:bg-brand-700 shadow-lg shadow-brand-100",
  secondary: "bg-brand-50 text-brand-600 hover:bg-brand-100",
  ghost: "bg-gray-100 text-gray-600 hover:bg-gray-200",
};

const sizes: Record<Size, string> = {
  sm: "px-4 py-2 text-sm rounded-xl",
  md: "px-5 py-3 text-sm rounded-2xl",
  lg: "w-full py-5 text-base rounded-2xl",
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`font-bold transition active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
