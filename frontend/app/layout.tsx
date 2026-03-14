import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "FFH",
  description: "나만의 손글씨를 폰트로 만드세요",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="antialiased font-sans">
        <Header />
        {children}
      </body>
    </html>
  );
}
