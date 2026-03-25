"use client";

import { useState } from "react";
import { authService } from "@/app/lib/axios";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";

export default function SignUpPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    passwordConfirm: "",
  });

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (formData.password !== formData.passwordConfirm) {
      alert("비밀번호가 일치하지 않습니다. 다시 확인해 주세요!");
      return;
    }

    try {
      await authService.signUp(
        formData.email,
        formData.password,
        formData.name,
      );
      alert("회원가입이 완료되었습니다! 로그인해 주세요.");
      router.push("/sign-in");
    } catch (error: any) {
      alert(error.response?.data || "회원가입 중 오류가 발생했습니다.");
    }
  };

  return (
    <AuthForm type="sign-up" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="이름"
        className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500 text-black"
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
        required
      />

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

      <input
        type="password"
        placeholder="비밀번호 확인"
        className="w-full px-4 py-3 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-purple-500 text-black"
        onChange={(e) =>
          setFormData({ ...formData, passwordConfirm: e.target.value })
        }
        required
      />
    </AuthForm>
  );
}
