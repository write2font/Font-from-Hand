"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Download, FileText, Pencil, Trash2, User } from "lucide-react";
import api, { authService } from "@/app/lib/axios";
import PageHeader from "@/components/ui/PageHeader";
import Button from "@/components/ui/Button";

interface UserInfo {
  name: string;
  email: string;
}

interface Font {
  fontId: string;
  fontName: string;
  type: string;
  createdAt: string;
}

interface AutobiographyItem {
  id: number;
  subjectName: string;
  title: string;
  createdAt: string;
}

export default function MyPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [fonts, setFonts] = useState<Font[]>([]);
  const [autobiographies, setAutobiographies] = useState<AutobiographyItem[]>([]);
  const [loading, setLoading] = useState(true);

  const [isEditingName, setIsEditingName] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [nameLoading, setNameLoading] = useState(false);

  const [deleteLoading, setDeleteLoading] = useState(false);
  const [autoDeleteLoading, setAutoDeleteLoading] = useState(false);

  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawLoading, setWithdrawLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [userData, fontsData, autoData] = await Promise.all([
          authService.getMe(),
          api.get("/fonts/list").then((r) => r.data),
          api.get("/autobiography/list").then((r) => r.data).catch(() => []),
        ]);
        setUser(userData);
        setFonts(fontsData);
        setAutobiographies(autoData);
      } catch (error: any) {
        if (error.response?.status === 401) {
          router.push("/sign-in");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [router]);

  const handleEditName = () => {
    setNameInput(user?.name ?? "");
    setIsEditingName(true);
  };

  const handleSaveName = async () => {
    if (!nameInput.trim()) return;
    setNameLoading(true);
    try {
      const updated = await authService.updateName(nameInput.trim());
      setUser(updated);
      setIsEditingName(false);
    } catch {
      alert("이름 수정 중 오류가 발생했습니다.");
    } finally {
      setNameLoading(false);
    }
  };

  const handleDownload = async (fontId: string, fontName: string) => {
    try {
      const response = await api.get(`/fonts/download/${fontId}`, {
        responseType: "blob",
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${fontName}.ttf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch {
      alert("다운로드 중 오류가 발생했습니다.");
    }
  };

  const handleDeleteFont = async (fontId: string) => {
    if (!window.confirm("폰트를 삭제할까요? 삭제한 폰트는 복구할 수 없어요.")) return;
    setDeleteLoading(true);
    try {
      await api.delete(`/fonts/${fontId}`);
      setFonts((prev) => prev.filter((f) => f.fontId !== fontId));
    } catch {
      alert("폰트 삭제 중 오류가 발생했습니다.");
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleDeleteAutobiography = async (id: number) => {
    if (!window.confirm("자서전을 삭제할까요? 삭제한 자서전은 복구할 수 없어요.")) return;
    setAutoDeleteLoading(true);
    try {
      await api.delete(`/autobiography/${id}`);
      setAutobiographies((prev) => prev.filter((a) => a.id !== id));
    } catch {
      alert("자서전 삭제 중 오류가 발생했습니다.");
    } finally {
      setAutoDeleteLoading(false);
    }
  };

  const handleWithdraw = async () => {
    setWithdrawLoading(true);
    try {
      await authService.deleteAccount();
      window.location.href = "/";
    } catch {
      alert("회원탈퇴 중 오류가 발생했습니다.");
      setWithdrawLoading(false);
      setShowWithdrawModal(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">불러오는 중...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      <main className="max-w-4xl mx-auto px-6 pt-16">
        <PageHeader title="마이페이지" />

        {/* 사용자 정보 */}
        <section className="bg-white rounded-3xl border border-gray-100 shadow-sm px-8 py-7 mb-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-brand-50 rounded-xl">
              <User size={18} className="text-brand-500" />
            </div>
            <h2 className="text-base font-bold text-gray-800">내 정보</h2>
          </div>

          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400 w-16">이름</span>
              {isEditingName ? (
                <div className="flex items-center gap-2 flex-1 ml-4">
                  <input
                    autoFocus
                    value={nameInput}
                    onChange={(e) => setNameInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSaveName()}
                    onBlur={() => setIsEditingName(false)}
                    className="flex-1 px-3 py-1.5 text-sm border border-brand-300 rounded-xl outline-none focus:ring-2 focus:ring-brand-200"
                  />
                  <button
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={handleSaveName}
                    disabled={nameLoading}
                    className="px-3 py-1.5 text-sm font-bold text-brand-600 hover:bg-brand-50 rounded-xl transition disabled:opacity-50"
                  >
                    저장
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 flex-1 ml-4">
                  <span className="text-sm font-medium text-gray-800">{user?.name}</span>
                  <button
                    onClick={handleEditName}
                    className="p-1.5 text-gray-300 hover:text-brand-500 hover:bg-brand-50 rounded-lg transition"
                  >
                    <Pencil size={14} />
                  </button>
                </div>
              )}
            </div>

            <div className="h-px bg-gray-50" />

            <div className="flex items-center">
              <span className="text-sm text-gray-400 w-16">이메일</span>
              <span className="text-sm text-gray-800 ml-4">{user?.email}</span>
            </div>
          </div>
        </section>

        {/* 폰트 목록 */}
        <section className="mb-10">
          <h2 className="text-base font-bold mb-6 flex items-center gap-2">
            <FileText size={18} className="text-brand-500" />
            내 폰트 목록
          </h2>

          {fonts.length === 0 ? (
            <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-16 text-center">
              <p className="text-gray-400 mb-6">아직 만든 폰트가 없어요.</p>
              <Button onClick={() => router.push("/")}>폰트 만들러 가기</Button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {fonts.map((font) => (
                <div
                  key={font.fontId}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm px-8 py-6 flex items-center justify-between"
                >
                  <div>
                    <p className="text-base font-bold text-gray-800">{font.fontName}</p>
                    <p className="text-sm text-gray-400 mt-1">
                      {font.type === "MANUAL" ? "직접 작성" : "AI 생성"} •{" "}
                      {new Date(font.createdAt).toLocaleDateString("ko-KR")}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <Button
                      size="sm"
                      onClick={() => handleDownload(font.fontId, font.fontName)}
                      className="flex items-center gap-2"
                    >
                      <Download size={14} />
                      TTF 다운로드
                    </Button>

                    <button
                      onClick={() => handleDeleteFont(font.fontId)}
                      disabled={deleteLoading}
                      className="p-2 text-gray-300 hover:text-red-400 hover:bg-red-50 rounded-xl transition disabled:opacity-50"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 자서전 목록 */}
        <section className="mb-10">
          <h2 className="text-base font-bold mb-6 flex items-center gap-2">
            <BookOpen size={18} className="text-brand-500" />
            내 자서전 목록
          </h2>

          {autobiographies.length === 0 ? (
            <div className="bg-white rounded-3xl border border-gray-100 shadow-sm p-16 text-center">
              <p className="text-gray-400 mb-6">아직 만든 자서전이 없어요.</p>
              <Button onClick={() => router.push("/autobiography")}>자서전 만들러 가기</Button>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              {autobiographies.map((auto) => (
                <div
                  key={auto.id}
                  className="bg-white rounded-2xl border border-gray-100 shadow-sm px-8 py-6 flex items-center justify-between"
                >
                  <div>
                    <p className="text-base font-bold text-gray-800">
                      {auto.title || `${auto.subjectName}의 자서전`}
                    </p>
                    <p className="text-sm text-gray-400 mt-1">
                      {auto.subjectName} • {new Date(auto.createdAt).toLocaleDateString("ko-KR")}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Button
                      size="sm"
                      onClick={() => window.open(`http://localhost:8080/api/v1/autobiography/download/${auto.id}`, "_blank")}
                      className="flex items-center gap-2"
                    >
                      <Download size={14} />
                      PDF 다운로드
                    </Button>
                    <button
                      onClick={() => handleDeleteAutobiography(auto.id)}
                      disabled={autoDeleteLoading}
                      className="p-2 text-gray-300 hover:text-red-400 hover:bg-red-50 rounded-xl transition disabled:opacity-50"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 회원탈퇴 */}
        <section className="flex justify-end">
          <button
            onClick={() => setShowWithdrawModal(true)}
            className="text-sm text-gray-300 hover:text-red-400 transition underline underline-offset-2"
          >
            회원탈퇴
          </button>
        </section>
      </main>

      {/* 회원탈퇴 모달 */}
      {showWithdrawModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 px-6">
          <div className="bg-white rounded-3xl shadow-xl p-8 w-full max-w-sm">
            <h3 className="text-lg font-bold text-gray-900 mb-2">정말 탈퇴하시겠어요?</h3>
            <p className="text-sm text-gray-400 mb-8 leading-relaxed">
              탈퇴하면 내 폰트와 모든 정보가 <br />
              영구적으로 삭제되며 복구할 수 없어요.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowWithdrawModal(false)}
                className="flex-1 py-3 text-sm font-bold text-gray-500 bg-gray-100 hover:bg-gray-200 rounded-2xl transition"
              >
                취소
              </button>
              <button
                onClick={handleWithdraw}
                disabled={withdrawLoading}
                className="flex-1 py-3 text-sm font-bold text-white bg-red-400 hover:bg-red-500 rounded-2xl transition disabled:opacity-50"
              >
                {withdrawLoading ? "처리 중..." : "탈퇴하기"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
