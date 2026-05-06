"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { authService } from "@/app/lib/axios";

export default function Header() {
  const [user, setUser] = useState<{ name: string; email: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const data = await authService.getMe();
        setUser(data);
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="flex justify-between items-center px-12 py-6 bg-white border-b border-gray-100 w-full">
      <Link href="/" className="text-2xl font-bold tracking-tight text-purple-600">
        FFH
      </Link>

      <div className="flex gap-6 items-center">
        {loading ? (
          <div className="w-16 h-8" />
        ) : user ? (
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen((prev) => !prev)}
              className="flex items-center gap-1 text-sm font-semibold text-gray-700 hover:text-purple-600 transition"
            >
              <span className="text-purple-600">{user.name}</span>님
              <ChevronDown size={14} className={`transition-transform ${dropdownOpen ? "rotate-180" : ""}`} />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-36 bg-white border border-gray-100 rounded-2xl shadow-lg overflow-hidden z-50">
                <Link
                  href="/mypage"
                  onClick={() => setDropdownOpen(false)}
                  className="block px-4 py-3 text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-600 transition"
                >
                  마이페이지
                </Link>
                <button
                  onClick={async () => {
                    setDropdownOpen(false);
                    await authService.signOut();
                    window.location.reload();
                  }}
                  className="w-full text-left px-4 py-3 text-sm text-gray-400 hover:bg-red-50 hover:text-red-400 transition"
                >
                  로그아웃
                </button>
              </div>
            )}
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
