"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { authService } from "@/app/lib/axios";

export default function Header() {
  const [user, setUser] = useState<{ name: string; email: string } | null>(
    null,
  );
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await authService.getMe();
        setUser(data);
      } catch (error) {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, []);

  return (
    <header className="flex justify-between items-center px-12 py-6 bg-white border-b border-gray-100 w-full">
      <Link
        href="/"
        className="text-2xl font-bold tracking-tight text-purple-600"
      >
        FFH
      </Link>

      <div className="flex gap-6 items-center">
        {loading ? (
          <div className="w-16 h-8" />
        ) : user ? (
          <div className="flex items-center gap-4">
            <span className="text-sm font-semibold text-gray-700">
              <span className="text-purple-600">{user.name}</span>님
            </span>
            <button
              onClick={async () => {
                await authService.signOut();
                window.location.reload();
              }}
              className="text-xs text-gray-400 hover:text-red-400 underline"
            >
              로그아웃
            </button>
          </div>
        ) : (
          <Link href="/sign-in">
            <button className="px-5 py-2 text-sm font-medium text-white bg-purple-600 rounded-full hover:bg-purple-700 transition shadow-sm active:scale-95">
              로그인
            </button>
          </Link>
        )}
      </div>
    </header>
  );
}
