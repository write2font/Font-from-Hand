"use client";

import Link from "next/link";

interface AuthFormProps {
  type: "sign-in" | "sign-up";
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  children: React.ReactNode;
}

export default function AuthForm({ type, onSubmit, children }: AuthFormProps) {
  const isSignIn = type === "sign-in";

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50 p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-10 space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-extrabold text-gray-900">
            {isSignIn ? "로그인" : "회원가입"}
          </h1>
        </div>

        <form onSubmit={onSubmit} className="space-y-5">
          {children}
          <button
            type="submit"
            className="w-full bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 rounded-xl shadow-lg transition-all active:scale-95"
          >
            {isSignIn ? "로그인" : "가입하기"}
          </button>
        </form>

        <div className="text-center text-sm text-gray-600">
          {isSignIn ? "아직 회원이 아니신가요? " : "이미 계정이 있으신가요? "}
          <Link
            href={isSignIn ? "/sign-up" : "/sign-in"}
            className="text-purple-600 font-bold hover:underline"
          >
            {isSignIn ? "회원가입" : "로그인"}
          </Link>
        </div>
      </div>
    </div>
  );
}
