import type { Metadata } from "next";
import "./globals.css";

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
      <body className="antialiased font-sans">{children}</body>
    </html>
  );
}
