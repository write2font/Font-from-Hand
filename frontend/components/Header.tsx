import Link from "next/link";

export default function Header() {
  return (
    <header className="flex justify-between items-center px-12 py-6 bg-white border-b border-gray-100 w-full">
      <Link
        href="/"
        className="text-2xl font-bold tracking-tight text-purple-600"
      >
        FFH
      </Link>
      <div className="flex gap-6 items-center">
        <button className="px-5 py-2 text-sm font-medium text-white bg-purple-600 rounded-full hover:bg-purple-700 transition shadow-sm">
          로그인
        </button>
      </div>
    </header>
  );
}
