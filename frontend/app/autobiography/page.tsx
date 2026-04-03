"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Mic, Square, Play, Pause, Upload, X, BookOpen, Mic2, FileText, Sparkles, ChevronRight, Check } from "lucide-react";
import axios from "axios";

// ── Types ──────────────────────────────────────────────────────────────────────
type Step = "intro" | "info" | "image" | "questions" | "followup" | "keywords" | "generating";

interface RecordingState {
  status: "idle" | "recording" | "done";
  blob: Blob | null;
  url: string | null;
  duration: number;
}

// ── Constants ──────────────────────────────────────────────────────────────────
const QUESTIONS = [
  { num: 2,  category: "가족 관계",   text: "부모님은 어떤 분이셨으며, 형제들 사이에서 주로 어떤 역할이었나요?" },
  { num: 3,  category: "유년의 풍경", text: "어린 시절, 우리 집이나 동네에서 가장 좋아했던 장소와 그곳의 분위기를 묘사해 주세요." },
  { num: 4,  category: "기억의 조각", text: "유년 시절을 떠올리면 가장 먼저 생각나는 상징적인 사건이나 장면 하나는 무엇인가요?" },
  { num: 5,  category: "꿈의 시작",   text: "어린 시절의 꿈은 무엇이었으며, 현재의 직업이나 전공을 선택하게 된 결정적인 계기는 무엇이었나요?" },
  { num: 6,  category: "학교 생활",   text: "학창 시절 가장 열정적으로 몰두했던 공부나 활동은 무엇이었나요?" },
  { num: 7,  category: "시대의 공기", text: "청년 시절, 사회적으로나 개인적으로 가장 뜨거웠던 기억(예: 첫 취업, 시대적 사건 등)은 무엇인가요?" },
  { num: 8,  category: "인연",        text: "인생의 방향을 바꿔놓을 만큼 큰 영향을 준 스승이나 친구, 혹은 동료가 있나요?" },
  { num: 9,  category: "시련의 순간", text: "인생에서 가장 힘들었던 시기는 언제였으며, 무엇이 당신을 가장 괴롭혔나요?" },
  { num: 10, category: "극복의 동력", text: "그 시련을 어떻게 버텨내셨으며, 그 과정에서 무엇을 배우셨나요?" },
  { num: 11, category: "빛나는 성취", text: "내 인생에서 \"이것만큼은 정말 잘했다\"고 자부하는 가장 큰 업적이나 결과물은 무엇인가요?" },
  { num: 12, category: "삶의 전환점", text: "인생의 경로가 180도 바뀌었던 결정적인 선택의 순간과 그 이유를 들려주세요." },
  { num: 13, category: "인생 철학",   text: "평생을 지탱해 온 자신만의 좌우명이나 꼭 지키고자 했던 원칙은 무엇인가요?" },
  { num: 14, category: "후회와 조언", text: "다시 태어난다면 꼭 해보고 싶은 일이나, 후배 세대에게 꼭 전하고 싶은 한마디는 무엇인가요?" },
  { num: 15, category: "마지막 인사", text: "훗날 사람들이 당신을 어떤 단어 혹은 어떤 사람으로 기억해주길 바라시나요?" },
];


function fmtSeconds(s: number) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

// ── Main ───────────────────────────────────────────────────────────────────────
export default function AutobiographyPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("intro");

  // Info
  const [name, setName]         = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [hometown, setHometown]   = useState("");

  // Image
  const [images, setImages]      = useState<File[]>([]);
  const imageInputRef             = useRef<HTMLInputElement>(null);

  // Questions (Q1–Q15)
  const [currentQIdx, setCurrentQIdx] = useState(0);
  const [recordings, setRecordings]   = useState<RecordingState[]>(
    () => QUESTIONS.map(() => ({ status: "idle" as const, blob: null, url: null, duration: 0 }))
  );
  const [transcriptions, setTranscriptions] = useState<string[]>(Array(QUESTIONS.length).fill(""));
  const [transcribing, setTranscribing]     = useState(false);
  const [qPlaying, setQPlaying]             = useState(false);
  const qAudioRef                           = useRef<HTMLAudioElement | null>(null);

  // Followup
  const [followupQuestions, setFollowupQuestions]       = useState<string[]>([]);
  const [followupRecordings, setFollowupRecordings]     = useState<RecordingState[]>([]);
  const [followupTranscriptions, setFollowupTranscriptions] = useState<string[]>([]);
  const [followupTranscribing, setFollowupTranscribing] = useState(false);
  const [currentFIdx, setCurrentFIdx]                   = useState(0);
  const [loadingFollowup, setLoadingFollowup]           = useState(false);
  const [fPlaying, setFPlaying]                         = useState(false);
  const fAudioRef                                       = useRef<HTMLAudioElement | null>(null);

  // Keywords
  const [keywords, setKeywords]               = useState<string[]>([]);
  const [selectedKeywords, setSelectedKeywords] = useState<Set<string>>(new Set());
  const [suggestedTitle, setSuggestedTitle]   = useState("");
  const [loadingKeywords, setLoadingKeywords] = useState(false);

  // Generating
  const [progress, setProgress]         = useState(0);
  const progressIntervalRef             = useRef<NodeJS.Timeout | null>(null);

  // Recording engine (shared)
  const [isRecording, setIsRecording]   = useState(false);
  const [recSeconds, setRecSeconds]     = useState(0);
  const recSecondsRef                   = useRef(0);
  const mediaRecorderRef                = useRef<MediaRecorder | null>(null);
  const chunksRef                       = useRef<Blob[]>([]);
  const timerRef                        = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => () => { timerRef.current && clearInterval(timerRef.current); }, []);

  // ── Recording ────────────────────────────────────────────────────────────────
  const startRecording = async (
    onDone: (blob: Blob, url: string, duration: number) => void
  ) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
      chunksRef.current = [];
      recSecondsRef.current = 0;
      setRecSeconds(0);
      setIsRecording(true);

      timerRef.current = setInterval(() => {
        recSecondsRef.current += 1;
        setRecSeconds((s) => s + 1);
      }, 1000);

      mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      mr.onstop = () => {
        timerRef.current && clearInterval(timerRef.current);
        setIsRecording(false);
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const url  = URL.createObjectURL(blob);
        stream.getTracks().forEach((t) => t.stop());
        onDone(blob, url, recSecondsRef.current);
      };
      mr.start(100);
    } catch {
      alert("마이크 권한이 필요합니다. 브라우저에서 마이크 접근을 허용해주세요.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
  };

  // ── STT ──────────────────────────────────────────────────────────────────────
  const transcribeBlob = async (
    blob: Blob,
    onResult: (text: string) => void,
    setLoading: (v: boolean) => void
  ) => {
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("audio", blob, "recording.webm");
      const res = await axios.post("http://localhost:8080/api/v1/autobiography/transcribe", fd);
      onResult(res.data.text ?? "");
    } catch {
      // 백엔드 미연결 시 mock
      await new Promise((r) => setTimeout(r, 1000));
      onResult("(STT 변환 결과가 여기에 표시됩니다. 직접 입력하거나 수정하세요.)");
    } finally {
      setLoading(false);
    }
  };

  // ── Q 녹음 핸들러 ─────────────────────────────────────────────────────────────
  const handleQStart = () => {
    setRecordings((prev) => {
      const a = [...prev];
      a[currentQIdx] = { ...a[currentQIdx], status: "recording" };
      return a;
    });
    startRecording((blob, url, duration) => {
      setRecordings((prev) => {
        const a = [...prev];
        a[currentQIdx] = { status: "done", blob, url, duration };
        return a;
      });
      transcribeBlob(
        blob,
        (text) => setTranscriptions((prev) => { const a = [...prev]; a[currentQIdx] = text; return a; }),
        setTranscribing
      );
    });
  };

  const handleQReset = () => {
    setRecordings((prev) => {
      const a = [...prev];
      a[currentQIdx] = { status: "idle", blob: null, url: null, duration: 0 };
      return a;
    });
    setTranscriptions((prev) => { const a = [...prev]; a[currentQIdx] = ""; return a; });
    setQPlaying(false);
  };

  const handleQFileUpload = (blob: Blob, url: string) => {
    const audio = new Audio(url);
    audio.addEventListener("loadedmetadata", () => {
      const duration = isFinite(audio.duration) ? Math.round(audio.duration) : 0;
      setRecordings((prev) => {
        const a = [...prev];
        a[currentQIdx] = { status: "done", blob, url, duration };
        return a;
      });
    });
    transcribeBlob(
      blob,
      (text) => setTranscriptions((prev) => { const a = [...prev]; a[currentQIdx] = text; return a; }),
      setTranscribing
    );
  };

  const toggleQPlay = () => {
    if (!qAudioRef.current) return;
    if (qPlaying) { qAudioRef.current.pause(); setQPlaying(false); }
    else { qAudioRef.current.play(); setQPlaying(true); qAudioRef.current.onended = () => setQPlaying(false); }
  };

  // ── Followup 녹음 핸들러 ──────────────────────────────────────────────────────
  const handleFStart = () => {
    setFollowupRecordings((prev) => {
      const a = [...prev];
      a[currentFIdx] = { ...a[currentFIdx], status: "recording" };
      return a;
    });
    startRecording((blob, url, duration) => {
      setFollowupRecordings((prev) => {
        const a = [...prev];
        a[currentFIdx] = { status: "done", blob, url, duration };
        return a;
      });
      transcribeBlob(
        blob,
        (text) => setFollowupTranscriptions((prev) => { const a = [...prev]; a[currentFIdx] = text; return a; }),
        setFollowupTranscribing
      );
    });
  };

  const handleFReset = () => {
    setFollowupRecordings((prev) => {
      const a = [...prev];
      a[currentFIdx] = { status: "idle", blob: null, url: null, duration: 0 };
      return a;
    });
    setFollowupTranscriptions((prev) => { const a = [...prev]; a[currentFIdx] = ""; return a; });
    setFPlaying(false);
  };

  const handleFFileUpload = (blob: Blob, url: string) => {
    const audio = new Audio(url);
    audio.addEventListener("loadedmetadata", () => {
      const duration = isFinite(audio.duration) ? Math.round(audio.duration) : 0;
      setFollowupRecordings((prev) => {
        const a = [...prev];
        a[currentFIdx] = { status: "done", blob, url, duration };
        return a;
      });
    });
    transcribeBlob(
      blob,
      (text) => setFollowupTranscriptions((prev) => { const a = [...prev]; a[currentFIdx] = text; return a; }),
      setFollowupTranscribing
    );
  };

  const toggleFPlay = () => {
    if (!fAudioRef.current) return;
    if (fPlaying) { fAudioRef.current.pause(); setFPlaying(false); }
    else { fAudioRef.current.play(); setFPlaying(true); fAudioRef.current.onended = () => setFPlaying(false); }
  };

  // ── Step transitions ──────────────────────────────────────────────────────────
  const handleQuestionsNext = async () => {
    setStep("followup");
    setLoadingFollowup(true);
    try {
      const res = await axios.post("http://localhost:8080/api/v1/autobiography/generate-followups", {
        name, birthDate, hometown,
        qas: QUESTIONS.map((q, i) => ({
          question: q.text,
          category: q.category,
          answer: transcriptions[i],
        })),
      });
      const questions: string[] = res.data.followups ?? [];
      if (questions.length === 0) {
        goToKeywords();
        return;
      }
      setFollowupQuestions(questions);
      setFollowupRecordings(questions.map(() => ({ status: "idle" as const, blob: null, url: null, duration: 0 })));
      setFollowupTranscriptions(Array(questions.length).fill(""));
      setCurrentFIdx(0);
    } catch {
      // AI 추가 질문 생성 실패 시 키워드 단계로 이동
      goToKeywords();
    } finally {
      setLoadingFollowup(false);
    }
  };

  const goToKeywords = async () => {
    setStep("keywords");
    setLoadingKeywords(true);
    try {
      const res = await axios.post("http://localhost:8080/api/v1/autobiography/suggest", {
        name, birth: birthDate,
        transcriptions,
        followup_transcriptions: followupTranscriptions,
      });
      const kws = res.data.keywords;
      setKeywords(Array.isArray(kws) ? kws : []);
      setSuggestedTitle(res.data.title ?? "");
    } catch {
      setKeywords(["가족", "고향", "청춘", "추억", "성실", "꿈"]);
      setSuggestedTitle("");
    } finally {
      setLoadingKeywords(false);
    }
  };

  const toggleKeyword = (kw: string) => {
    setSelectedKeywords((prev) => {
      const next = new Set(prev);
      if (next.has(kw)) next.delete(kw);
      else if (next.size < 3) next.add(kw);
      return next;
    });
  };

  const handleGenerate = async () => {
    setStep("generating");
    setProgress(0);
    progressIntervalRef.current = setInterval(() => {
      setProgress((p) => (p >= 95 ? 95 : p + 1));
    }, 1800);

    try {
      const fd = new FormData();
      fd.append("name", name);
      fd.append("birth", birthDate);
      fd.append("hometown", hometown);
      fd.append("transcriptions", JSON.stringify(transcriptions));
      fd.append("followup_transcriptions", JSON.stringify(followupTranscriptions));
      fd.append("keywords", JSON.stringify(Array.from(selectedKeywords)));
      fd.append("title", suggestedTitle);
      images.forEach((img) => fd.append("images", img));

      const res = await axios.post("http://localhost:8080/api/v1/autobiography/generate", fd);
      if (res.status === 200) {
        progressIntervalRef.current && clearInterval(progressIntervalRef.current);
        setProgress(100);
        setTimeout(() => router.push("/autobiography/result"), 800);
      }
    } catch {
      setTimeout(() => {
        progressIntervalRef.current && clearInterval(progressIntervalRef.current);
        setProgress(100);
        setTimeout(() => router.push("/autobiography/result"), 800);
      }, 8000);
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────────
  if (step === "intro") return <IntroStep onNext={() => setStep("info")} />;

  if (step === "info") return (
    <PageShell>
      <StepIndicator step={step} />
      <h1 className="text-2xl font-bold mb-8">기본 정보 입력</h1>
      <FieldCard label="이름">
        <input type="text" placeholder="예: 홍길동" value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full bg-transparent outline-none text-gray-800 placeholder-gray-400 text-base" />
      </FieldCard>
      <FieldCard label="생년월일">
        <input type="date" value={birthDate}
          onChange={(e) => setBirthDate(e.target.value)}
          className="w-full bg-transparent outline-none text-gray-800 text-base" />
      </FieldCard>
      <FieldCard label="출신지">
        <input type="text" placeholder="예: 충남 공주시" value={hometown}
          onChange={(e) => setHometown(e.target.value)}
          className="w-full bg-transparent outline-none text-gray-800 placeholder-gray-400 text-base" />
      </FieldCard>
      <PrimaryButton disabled={!name || !birthDate || !hometown} onClick={() => setStep("image")}>다음</PrimaryButton>
    </PageShell>
  );

  if (step === "image") return (
    <PageShell>
      <StepIndicator step={step} />
      <h1 className="text-2xl font-bold mb-8">기본 정보 입력</h1>
      <FieldCard label="자서전에 넣고픈 이미지 업로드">
        <input type="file" accept="image/*" multiple className="hidden" ref={imageInputRef}
          onChange={(e) => { if (e.target.files) setImages((p) => [...p, ...Array.from(e.target.files!)]); }} />
        {images.length === 0 ? (
          <button onClick={() => imageInputRef.current?.click()}
            className="w-full h-44 flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-purple-400 transition">
            <Upload size={32} />
            <span className="text-sm">클릭하여 이미지 추가</span>
          </button>
        ) : (
          <div className="space-y-2">
            {images.map((img, i) => (
              <div key={i} className="flex items-center justify-between text-sm text-gray-700">
                <span className="truncate flex-1 mr-2">{img.name}</span>
                <button onClick={() => setImages((p) => p.filter((_, j) => j !== i))}>
                  <X size={16} className="text-gray-400 hover:text-red-400" />
                </button>
              </div>
            ))}
            <button onClick={() => imageInputRef.current?.click()} className="text-xs text-purple-400 mt-2">+ 더 추가</button>
          </div>
        )}
      </FieldCard>
      <div className="flex gap-3 mt-8">
        <SecondaryButton className="flex-1" onClick={() => setStep("info")}>이전</SecondaryButton>
        <PrimaryButton className="flex-1" onClick={() => { setCurrentQIdx(0); setStep("questions"); }}>다음</PrimaryButton>
      </div>
    </PageShell>
  );

  if (step === "questions") {
    const q   = QUESTIONS[currentQIdx];
    const rec = recordings[currentQIdx];
    const tx  = transcriptions[currentQIdx];
    const isLast = currentQIdx === QUESTIONS.length - 1;

    return (
      <PageShell>
        <StepIndicator step={step} />
        {/* 질문 진행 도트 */}
        <div className="flex items-center justify-between mb-8">
          <span className="text-sm text-gray-400 font-medium">질문 {currentQIdx + 1} / {QUESTIONS.length}</span>
          <div className="flex gap-1">
            {QUESTIONS.map((_, i) => (
              <button key={i} onClick={() => setCurrentQIdx(i)}
                className={`w-2 h-2 rounded-full transition ${i === currentQIdx ? "bg-purple-400" : recordings[i].status === "done" ? "bg-purple-200" : "bg-gray-200"}`} />
            ))}
          </div>
        </div>

        {/* 질문 카드 */}
        <div className="bg-gray-100 rounded-2xl p-8 mb-6">
          <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">{q.category}</p>
          <p className="text-xl font-bold text-gray-800 leading-relaxed">{q.text}</p>
        </div>

        {/* 녹음 영역 */}
        <RecordingArea
          recording={rec}
          isRecording={isRecording}
          recSeconds={recSeconds}
          transcribing={transcribing}
          transcript={tx}
          isPlaying={qPlaying}
          audioRef={qAudioRef}
          onStart={handleQStart}
          onStop={stopRecording}
          onReset={handleQReset}
          onTogglePlay={toggleQPlay}
          onTranscriptChange={(v) => setTranscriptions((prev) => { const a = [...prev]; a[currentQIdx] = v; return a; })}
          onFileUpload={handleQFileUpload}
        />

        <div className="flex gap-3 mt-8">
          <SecondaryButton className="flex-1" onClick={() => currentQIdx === 0 ? setStep("image") : setCurrentQIdx((i) => i - 1)}>
            이전
          </SecondaryButton>
          <PrimaryButton className="flex-1" onClick={() => isLast ? handleQuestionsNext() : setCurrentQIdx((i) => i + 1)}>
            {isLast ? "완료" : "다음 질문"}
          </PrimaryButton>
        </div>
      </PageShell>
    );
  }

  if (step === "followup") {
    if (loadingFollowup) return (
      <PageShell>
        <div className="flex flex-col items-center py-24 gap-4 text-gray-400">
          <div className="w-8 h-8 border-2 border-purple-300 border-t-purple-500 rounded-full animate-spin" />
          <span className="text-sm">부족한 답변을 분석하고 있어요...</span>
        </div>
      </PageShell>
    );

    const fq  = followupQuestions[currentFIdx];
    const frec = followupRecordings[currentFIdx];
    const ftx  = followupTranscriptions[currentFIdx];
    const isLast = currentFIdx === followupQuestions.length - 1;

    return (
      <PageShell>
        <StepIndicator step={step} />
        <div className="flex items-center justify-between mb-8">
          <span className="text-sm text-gray-400 font-medium">추가 질문 {currentFIdx + 1} / {followupQuestions.length}</span>
          <div className="flex gap-1">
            {followupQuestions.map((_, i) => (
              <button key={i} onClick={() => setCurrentFIdx(i)}
                className={`w-2 h-2 rounded-full transition ${i === currentFIdx ? "bg-purple-400" : followupRecordings[i]?.status === "done" ? "bg-purple-200" : "bg-gray-200"}`} />
            ))}
          </div>
        </div>

        <div className="bg-gray-100 rounded-2xl p-8 mb-6">
          <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-3">추가 질문</p>
          <p className="text-xl font-bold text-gray-800 leading-relaxed">{fq}</p>
        </div>

        <RecordingArea
          recording={frec ?? { status: "idle", blob: null, url: null, duration: 0 }}
          isRecording={isRecording}
          recSeconds={recSeconds}
          transcribing={followupTranscribing}
          transcript={ftx ?? ""}
          isPlaying={fPlaying}
          audioRef={fAudioRef}
          onStart={handleFStart}
          onStop={stopRecording}
          onReset={handleFReset}
          onTogglePlay={toggleFPlay}
          onTranscriptChange={(v) => setFollowupTranscriptions((prev) => { const a = [...prev]; a[currentFIdx] = v; return a; })}
          onFileUpload={handleFFileUpload}
        />

        <div className="flex gap-3 mt-8">
          <SecondaryButton className="flex-1" onClick={() => currentFIdx === 0 ? setStep("questions") : setCurrentFIdx((i) => i - 1)}>
            이전
          </SecondaryButton>
          <PrimaryButton className="flex-1" onClick={() => isLast ? goToKeywords() : setCurrentFIdx((i) => i + 1)}>
            {isLast ? "완료" : "다음 질문"}
          </PrimaryButton>
        </div>
      </PageShell>
    );
  }

  if (step === "keywords") return (
    <PageShell>
      <StepIndicator step={step} />
      <h1 className="text-2xl font-bold mb-8">키워드 선택</h1>
      {loadingKeywords ? (
        <div className="flex flex-col items-center py-24 gap-4 text-gray-400">
          <div className="w-8 h-8 border-2 border-purple-300 border-t-purple-500 rounded-full animate-spin" />
          <span className="text-sm">키워드를 추출하고 있어요...</span>
        </div>
      ) : (
        <>
          <div className="bg-gray-100 rounded-2xl p-6 mb-6">
            <p className="text-xs text-gray-400 mb-4">3개를 선택하세요 ({selectedKeywords.size}/3)</p>
            <div className="grid grid-cols-3 gap-3">
              {keywords.map((kw) => (
                <button key={kw} onClick={() => toggleKeyword(kw)}
                  className={`py-4 rounded-xl text-sm font-medium transition ${
                    selectedKeywords.has(kw) ? "bg-purple-400 text-white" : "bg-purple-200 text-gray-700 hover:bg-purple-300"
                  }`}>
                  {kw}
                </button>
              ))}
            </div>
          </div>
          <FieldCard label="예상 제목">
            <input type="text" value={suggestedTitle} readOnly
              className="w-full bg-transparent outline-none text-gray-800 text-base cursor-default" />
          </FieldCard>
          <div className="flex gap-3 mt-8">
            <SecondaryButton className="flex-1" onClick={() => followupQuestions.length > 0 ? setStep("followup") : setStep("questions")}>
              이전
            </SecondaryButton>
            <PrimaryButton className="flex-1" disabled={selectedKeywords.size !== 3} onClick={handleGenerate}>
              자서전 생성 시작
            </PrimaryButton>
          </div>
        </>
      )}
    </PageShell>
  );

  if (step === "generating") {
    const steps = ["인터뷰 분석 중", "챕터 구성 중", "본문 작성 중", "표지 생성 중", "PDF 완성 중"];
    const stepIdx = Math.min(Math.floor(progress / 20), steps.length - 1);
    return (
      <div className="min-h-screen bg-gradient-to-b from-purple-50 to-white flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-md text-center">
          {/* 아이콘 */}
          <div className="relative w-24 h-24 mx-auto mb-10">
            <div className="absolute inset-0 rounded-full bg-purple-100 animate-ping opacity-40" />
            <div className="relative w-24 h-24 rounded-full bg-purple-500 flex items-center justify-center shadow-lg shadow-purple-200">
              <BookOpen size={36} className="text-white" />
            </div>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">자서전을 만들고 있어요</h1>
          <p className="text-gray-400 text-sm mb-10">{name}님의 소중한 이야기를 담고 있습니다</p>

          {/* 진행바 */}
          <div className="relative w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
            <div className="absolute left-0 top-0 h-full bg-gradient-to-r from-purple-400 to-purple-600 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }} />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mb-8">
            <span>{steps[stepIdx]}</span>
            <span>{progress}%</span>
          </div>

          {/* 단계 표시 */}
          <div className="flex justify-center gap-2 mb-10">
            {steps.map((s, i) => (
              <div key={s} className={`flex flex-col items-center gap-1.5 ${i <= stepIdx ? "opacity-100" : "opacity-30"}`}>
                <div className={`w-2 h-2 rounded-full transition-all ${i < stepIdx ? "bg-purple-500" : i === stepIdx ? "bg-purple-400 scale-125" : "bg-gray-300"}`} />
              </div>
            ))}
          </div>

          <button onClick={() => { progressIntervalRef.current && clearInterval(progressIntervalRef.current); setStep("keywords"); }}
            className="text-sm text-gray-400 hover:text-gray-600 transition underline underline-offset-2">
            생성 취소
          </button>
        </div>
      </div>
    );
  }

  return null;
}

// ── RecordingArea ──────────────────────────────────────────────────────────────
function RecordingArea({
  recording, isRecording, recSeconds, transcribing, transcript,
  isPlaying, audioRef, onStart, onStop, onReset, onTogglePlay, onTranscriptChange, onFileUpload,
}: {
  recording: RecordingState;
  isRecording: boolean;
  recSeconds: number;
  transcribing: boolean;
  transcript: string;
  isPlaying: boolean;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onTogglePlay: () => void;
  onTranscriptChange: (v: string) => void;
  onFileUpload: (blob: Blob, url: string) => void;
}) {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const active = recording.status === "recording" || isRecording;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    onFileUpload(file, url);
    e.target.value = "";
  };

  return (
    <div className="space-y-4">
      <input type="file" accept="audio/*" className="hidden" ref={fileInputRef} onChange={handleFileChange} />
      {/* 녹음 컨트롤 */}
      <div className="bg-gray-100 rounded-2xl p-6">
        {recording.status === "idle" && !active && (
          <div className="flex justify-center gap-3">
            <button onClick={onStart}
              className="px-6 py-3 bg-purple-300 text-white font-bold rounded-xl hover:bg-purple-400 transition flex items-center gap-2">
              <Mic size={16} />
              녹음 시작
            </button>
            <button onClick={() => fileInputRef.current?.click()}
              className="px-6 py-3 bg-gray-200 text-gray-600 font-bold rounded-xl hover:bg-gray-300 transition flex items-center gap-2">
              <Upload size={16} />
              파일 업로드
            </button>
          </div>
        )}

        {active && (
          <div className="flex flex-col items-center gap-3">
            <div className="flex items-center gap-2 text-red-500 text-sm font-bold animate-pulse">
              <span className="w-2 h-2 bg-red-500 rounded-full inline-block" />
              녹음 중... {fmtSeconds(recSeconds)}
            </div>
            <button onClick={onStop}
              className="px-8 py-3 bg-red-100 text-red-500 font-bold rounded-xl hover:bg-red-200 transition flex items-center gap-2">
              <Square size={16} />
              녹음 중지
            </button>
          </div>
        )}

        {recording.status === "done" && recording.url && !active && (
          <div className="flex items-center gap-3">
            <button onClick={onTogglePlay}
              className="w-10 h-10 flex items-center justify-center bg-purple-300 text-white rounded-full hover:bg-purple-400 transition shrink-0">
              {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            </button>
            <audio ref={audioRef} src={recording.url} />
            <span className="text-sm text-gray-500 flex-1">
              녹음 완료 ({fmtSeconds(recording.duration)})
            </span>
            <button onClick={onReset} className="text-xs text-gray-400 hover:text-red-400 transition">
              다시 녹음
            </button>
          </div>
        )}
      </div>

      {/* STT 결과 / 텍스트 직접 입력 */}
      <div className="bg-gray-100 rounded-2xl p-6">
        <p className="text-xs font-bold text-gray-500 mb-3">
          답변 입력 <span className="text-gray-400 font-normal">(음성 변환 후 수정하거나 직접 입력하세요)</span>
        </p>
        {transcribing ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <div className="w-4 h-4 border-2 border-purple-300 border-t-purple-500 rounded-full animate-spin" />
            변환 중...
          </div>
        ) : (
          <textarea
            value={transcript}
            onChange={(e) => onTranscriptChange(e.target.value)}
            rows={5}
            placeholder="여기에 직접 입력하거나 위에서 녹음하세요."
            className="w-full bg-transparent outline-none text-gray-800 text-sm leading-relaxed resize-none placeholder-gray-300"
          />
        )}
      </div>
    </div>
  );
}

// ── IntroStep ──────────────────────────────────────────────────────────────────
function IntroStep({ onNext }: { onNext: () => void }) {
  const steps = [
    { icon: <Mic2 size={20} />,     label: "음성으로 답변",   desc: "14가지 질문에 음성으로 답해요" },
    { icon: <FileText size={20} />, label: "즉시 텍스트 변환", desc: "AI가 음성을 글로 바꾸고 수정할 수 있어요" },
    { icon: <Sparkles size={20} />, label: "AI 자서전 생성",   desc: "Claude가 나만의 자서전을 완성해요" },
    { icon: <BookOpen size={20} />, label: "폰트 적용 PDF",    desc: "손글씨 폰트가 담긴 PDF로 완성돼요" },
  ];

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 pt-16 pb-20">
        {/* 히어로 */}
        <div className="bg-gray-100 rounded-3xl p-10 mb-8">
          <p className="text-xs font-bold text-purple-400 uppercase tracking-widest mb-4">AI 자서전 시스템</p>
          <h2 className="text-3xl font-bold text-gray-900 leading-tight mb-4">
            당신의 이야기를<br />세상에 남겨보세요
          </h2>
          <p className="text-gray-500 text-sm leading-relaxed">
            음성으로 이야기하면 AI가 글로 정리하고, 나만의 손글씨 폰트가 담긴
            소중한 자서전 PDF를 만들어 드립니다.
          </p>
        </div>

        {/* 과정 안내 */}
        <div className="space-y-3 mb-10">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-4 bg-gray-50 rounded-2xl px-6 py-4">
              <div className="w-10 h-10 bg-purple-200 text-purple-600 rounded-xl flex items-center justify-center shrink-0">
                {s.icon}
              </div>
              <div className="flex-1">
                <p className="text-sm font-bold text-gray-800">{s.label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{s.desc}</p>
              </div>
              {i < steps.length - 1 && (
                <ChevronRight size={16} className="text-gray-300 shrink-0" />
              )}
            </div>
          ))}
        </div>

        <button onClick={onNext}
          className="w-full py-5 bg-purple-400 text-white font-bold rounded-2xl hover:bg-purple-500 transition text-lg">
          시작하기
        </button>
      </div>
    </div>
  );
}

// ── Shared UI ──────────────────────────────────────────────────────────────────
function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 pt-16 pb-20">{children}</div>
    </div>
  );
}

function FieldCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-100 rounded-2xl p-6 mb-4">
      <p className="text-sm font-bold text-gray-600 mb-3">{label}</p>
      {children}
    </div>
  );
}

function PrimaryButton({
  onClick, disabled = false, children, className = "w-full",
}: { onClick: () => void; disabled?: boolean; children: React.ReactNode; className?: string }) {
  return (
    <button onClick={onClick} disabled={disabled}
      className={`py-4 rounded-2xl font-bold text-base transition ${className} ${
        disabled
          ? "bg-gray-100 text-gray-400 cursor-not-allowed"
          : "bg-purple-500 text-white hover:bg-purple-600 shadow-sm shadow-purple-100"
      }`}>
      {children}
    </button>
  );
}

function SecondaryButton({
  onClick, children, className = "w-full",
}: { onClick: () => void; children: React.ReactNode; className?: string }) {
  return (
    <button onClick={onClick}
      className={`py-4 rounded-2xl bg-gray-100 text-gray-600 font-bold hover:bg-gray-200 transition ${className}`}>
      {children}
    </button>
  );
}

// ── StepIndicator ──────────────────────────────────────────────────────────────
const MACRO_STEPS = ["기본 정보", "인터뷰", "키워드", "생성"];

function stepIndexOf(step: Step): number {
  if (step === "info" || step === "image") return 0;
  if (step === "questions" || step === "followup") return 1;
  if (step === "keywords") return 2;
  return 3;
}

function StepIndicator({ step }: { step: Step }) {
  const current = stepIndexOf(step);
  return (
    <div className="flex justify-between items-center mb-12 px-4">
      {MACRO_STEPS.map((label, i) => (
        <React.Fragment key={i}>
          <div className="flex flex-col items-center gap-2">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors ${
              i < current  ? "bg-purple-500 text-white" :
              i === current ? "bg-purple-500 text-white" :
              "bg-gray-100 text-gray-400"
            }`}>
              {i < current ? <Check size={18} /> : i + 1}
            </div>
            <span className={`text-xs font-medium ${i <= current ? "text-gray-800" : "text-gray-400"}`}>
              {label}
            </span>
          </div>
          {i < MACRO_STEPS.length - 1 && (
            <div className={`flex-1 h-[1px] mx-3 mb-5 transition-colors ${i < current ? "bg-purple-500" : "bg-gray-200"}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
