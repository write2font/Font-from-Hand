"use client";

import { useState } from "react";
import { authService } from "@/app/lib/axios";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";

export default function SignInPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({ email: "", password: "" });

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      await authService.signIn(formData.email, formData.password);
      router.push("/");
    } catch (error) {
      alert("로그인 실패!");
    }
  };

  return (
    <AuthForm type="sign-in" onSubmit={handleSubmit}>
      <input
        type="email"
        placeholder="이메일 주소"
        className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500 text-black"
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
        required
      />
      <input
        type="password"
        placeholder="비밀번호"
        className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500 text-black"
        onChange={(e) => setFormData({ ...formData, password: e.target.value })}
        required
      />
    </AuthForm>
  );
}
