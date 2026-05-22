"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Mic, Square, Play, Pause, Upload, X, BookOpen, Mic2, FileText, Sparkles, Check, Plus } from "lucide-react";
import axios from "axios";
import api from "@/app/lib/axios";

// ── Types ──────────────────────────────────────────────────────────────────────
type Step = "intro" | "info" | "image" | "questions" | "followup" | "keyword" | "generating";

interface RecordingState {
  status: "idle" | "recording" | "done";
  blob: Blob | null;
  url: string | null;
  duration: number;
}

interface Question {
  num: number;
  category: string;
  text: string;
  conditionalOn?: number;
}

interface FreeEntry {
  period: string;
  recording: RecordingState;
  transcription: string;
}

// ── Question Sets ──────────────────────────────────────────────────────────────
const QUESTIONS_20S: Question[] = [
  { num: 1, category: "어린 날의 장소",        text: "어릴 때 가장 자주 가셨던 장소가 어디셨나요? 그곳이 왜 좋으셨나요?" },
  { num: 2, category: "유년의 맛",              text: "어릴 때 집에서 자주 드시던 음식이나 냄새 중 지금도 기억에 남는 것이 있으신가요?" },
  { num: 3, category: "학교 생활",              text: "학창 시절 공부 외에 가장 열정적으로 하셨던 것이 무엇인가요?" },
  { num: 4, category: "오래된 인연",            text: "지금 가장 친하게 지내는 사람을 처음 만났던 순간이 기억나시나요?" },
  { num: 5, category: "어린 시절의 꿈",         text: "어릴 때 어떤 사람이 되고 싶으셨나요? 지금의 모습과 어떻게 연결되나요?" },
  { num: 6, category: "버티던 시절",            text: "지금까지 무언가를 위해 정말 고생하거나 밤새워 매달리셨던 경험이 있으신가요?" },
  { num: 7, category: "내가 제일 빛났을 때",    text: "주변 사람에게 자랑하고 싶었던 순간이 있으신가요?" },
  { num: 8, category: "나에게 영향을 준 사람",  text: "지금까지 살면서 나에게 가장 큰 영향을 준 사람은 누구인가요? 어떤 영향을 받으셨나요?" },
  { num: 9, category: "앞으로의 나",            text: "10년 뒤, 어떤 모습이면 좋겠다고 생각하시나요?" },
];

const QUESTIONS_3040S: Question[] = [
  { num: 1,  category: "어린 날의 장소",      text: "어릴 때 가장 기억에 남는 장소나 풍경이 있으신가요?" },
  { num: 2,  category: "학교 생활",            text: "학창 시절 가장 열정적으로 하셨던 것이 무엇인가요?" },
  { num: 3,  category: "첫 도전",              text: "20대에 처음으로 혼자서 해내셨던 일이 기억나시나요?" },
  { num: 4,  category: "소중한 인연",          text: "가장 오래 함께하신 동료나 친구가 계신가요? 어떻게 친해지셨나요?" },
  { num: 5,  category: "삶의 전환점",          text: "지금과 전혀 다른 길을 갈 뻔했던 순간이 있으신가요?" },
  { num: 6,  category: "만약에",               text: "만약 그 선택을 하지 않으셨다면, 지금은 어떤 모습일 것 같으세요?", conditionalOn: 4 },
  { num: 7,  category: "버티던 시절",          text: "일이나 삶에서 가장 고되고 버거우셨던 시기는 언제였나요? 어떻게 버티셨나요?" },
  { num: 8,  category: "내가 제일 빛났을 때",  text: "일이나 생활에서 가장 뿌듯하셨던 순간은 언제인가요?" },
  { num: 9,  category: "가족과 함께",          text: "가족과 함께 가장 기억에 남는 순간이 있으신가요?" },
  { num: 10, category: "인생 철학",            text: "살면서 꼭 지키려 하셨던 원칙이 있으신가요?" },
  { num: 11, category: "앞으로의 꿈",          text: "앞으로 가장 해보고 싶으신 것이 있으신가요?" },
];

const QUESTIONS_5060S: Question[] = [
  { num: 1,  category: "어린 날의 장소",      text: "어릴 때 가장 자주 가셨던 장소가 어디인가요? 그곳이 왜 기억에 남으시나요?" },
  { num: 2,  category: "유년의 맛",            text: "어릴 때 집에서 자주 드시던 음식 중 지금도 생각나는 게 있으신가요?" },
  { num: 3,  category: "학교 생활",            text: "학창 시절 가장 열정적으로 하셨던 것이 무엇인가요?" },
  { num: 4,  category: "첫 사회생활",          text: "처음 사회에 나오셨을 때 어떤 일을 하셨나요? 그때 기억이 나시나요?" },
  { num: 5,  category: "오래된 인연",          text: "지금까지 가장 오래 함께한 친구나 동료가 계신가요? 어떻게 인연이 되셨나요?" },
  { num: 6,  category: "삶의 전환점",          text: "지금과 전혀 다른 길을 갈 뻔했던 순간이 있으신가요?" },
  { num: 7,  category: "만약에",               text: "만약 그 선택을 하지 않으셨다면 지금은 어떤 모습일 것 같으세요?", conditionalOn: 5 },
  { num: 8,  category: "버티던 시절",          text: "가장 고되고 버티기 힘드셨던 시기가 언제였나요? 어떻게 견디셨나요?" },
  { num: 9,  category: "내가 제일 빛났을 때",  text: "일이나 삶에서 가장 뿌듯하셨던 순간을 하나 꼽아주실 수 있으신가요?" },
  { num: 10, category: "인생 철학",            text: "살면서 꼭 지키려 하셨던 원칙이 있으신가요?" },
  { num: 11, category: "앞으로의 나",          text: "앞으로 가장 해보고 싶으신 것이 있으신가요?" },
];

const QUESTIONS_70PLUS: Question[] = [
  { num: 1,  category: "고향의 기억",          text: "고향이 어디이신가요? 어릴 때 고향의 풍경이나 냄새 중 지금도 기억에 남는 것이 있으신가요?" },
  { num: 2,  category: "유년의 맛",            text: "어릴 때 집에서 자주 드시던 음식이 무엇인가요? 그 맛이 아직도 기억나시나요?" },
  { num: 3,  category: "아끼던 것",            text: "어린 시절 가장 아끼셨던 물건이나 장소가 있으신가요?" },
  { num: 4,  category: "학교 생활",            text: "학창 시절 가장 좋아하셨던 과목이나 활동이 있으신가요?" },
  { num: 5,  category: "첫 사회생활",          text: "처음 사회에 나오셨을 때가 기억나시나요? 어떤 일을 하셨나요?" },
  { num: 6,  category: "버티던 시절",          text: "그 시절 가장 고생하거나 버티기 어려우셨던 순간이 있으신가요?" },
  { num: 7,  category: "오래된 인연",          text: "살면서 꼭 한 번 고맙다고 전하고 싶은 분이 계신가요? 그분은 어떤 분이셨나요?" },
  { num: 8,  category: "내가 제일 빛났을 때",  text: "인생에서 가장 잘하셨다고 생각하시는 일을 하나 꼽아주실 수 있으신가요?" },
  { num: 9,  category: "만약에",               text: "만약 그 선택을 하지 않으셨다면 지금의 삶이 어떻게 달랐을 것 같으세요?", conditionalOn: 7 },
  { num: 10, category: "인생 철학",            text: "평생 지켜오신 나만의 원칙이나 좌우명이 있으신가요?" },
  { num: 11, category: "젊은이에게",           text: "지금 젊은 분들에게 꼭 하고 싶으신 말씀이 있으신가요?" },
];

const QUESTION_HINTS: Record<string, string> = {
  "어린 날의 장소":        "예: 동네 뒷산 약수터였어요. 초등학교 때 친구들이랑 매일 거기서 놀았는데, 바위에 앉아 도시락 먹던 기억이 아직도 선해요. 친구 이름이나 그때 무엇을 했는지도 이야기해 주세요.",
  "고향의 기억":           "예: 경북 안동이요. 하회마을 근처 논 냄새, 여름에 모깃불 피우던 기억이 나요. 마당에 평상 놓고 수박 먹던 것도요. 고향의 어떤 장면이 가장 먼저 떠오르시나요?",
  "유년의 맛":             "예: 어머니가 겨울마다 끓여주시던 팥죽이요. 그 냄새가 나면 겨울이 왔다고 느꼈어요. 어떤 음식인지, 누가 만들어 줬는지, 어떤 맛이었는지 구체적으로 말씀해 주세요.",
  "아끼던 것":             "예: 할아버지한테 물려받은 작은 칼이요. 공책에 싸서 늘 가지고 다녔어요. 왜 그게 소중했는지, 지금도 갖고 있는지도 이야기해 주세요.",
  "학교 생활":             "예: 합창부였어요. 매일 방과 후 한 시간씩 연습했고, 3학년 때 전국대회에서 금상 받았을 때 선생님이 우셨어요. 어떤 활동을 했는지, 기억에 남는 순간도 함께 말씀해 주세요.",
  "어린 시절의 꿈":        "예: 의사가 되고 싶었어요. 드라마 속 의사가 멋있어 보여서요. 지금은 완전 다른 일을 하지만, 그 꿈이 언제 바뀌었는지도 기억나시면 말씀해 주세요.",
  "첫 사회생활":           "예: 공장 경리로 첫 출근한 날이요. 교복 입다가 처음으로 정장 입었는데 너무 어색했어요. 몇 살 때였는지, 어떤 일을 했는지, 첫날 어땠는지 이야기해 주세요.",
  "첫 도전":               "예: 처음으로 혼자 서울 올라가서 면접 본 날이요. 기차표 살 때 손이 떨렸어요. 왜 그 도전을 했는지, 결과가 어땠는지도 말씀해 주세요.",
  "오래된 인연":           "예: 중학교 입학날 옆자리에 앉았던 친구예요. 처음 말을 걸었던 계기가 뭔지, 지금도 연락하는지, 어떤 추억이 있는지 이야기해 주세요.",
  "소중한 인연":           "예: 입사 첫날 밥 사줬던 선배예요. 그분이 어떤 분이었는지, 어떻게 친해졌는지, 함께한 기억 중 하나를 골라 이야기해 주세요.",
  "삶의 전환점":           "예: 30살에 회사 그만두고 가게 차렸을 때요. 가족들이 다 반대했는데 결국 했어요. 왜 그 선택을 했는지, 그 후 어떻게 됐는지 말씀해 주세요.",
  "만약에":                "예: 그때 그냥 회사 다녔으면 지금쯤 팀장은 됐겠죠. 근데 후회는 없어요. 지금 생각으로 그 선택이 맞았다고 보시는지도 이야기해 주세요.",
  "버티던 시절":           "예: 셋째 낳고 일까지 병행하던 3년이요. 잠을 4시간도 못 잔 것 같아요. 어떻게 견디셨는지, 그때 힘이 됐던 것이 있었는지도 말씀해 주세요.",
  "내가 제일 빛났을 때":   "예: 팀장 됐을 때요. 아무도 안 믿어줬는데 제가 직접 설득해서 만든 프로젝트였거든요. 그 순간이 왜 특별했는지, 어떤 기분이었는지 이야기해 주세요.",
  "나에게 영향을 준 사람": "예: 고등학교 3학년 담임 선생님이요. 포기하려던 저한테 '넌 할 수 있다'고 하셨는데, 그 말이 지금도 생각나요. 어떤 영향을 받으셨는지 구체적으로 말씀해 주세요.",
  "가족과 함께":           "예: 첫째 돌잔치 날이요. 온 가족이 다 모였고, 아이가 실을 잡았어요. 그 자리에 누가 있었는지, 어떤 분위기였는지도 이야기해 주세요.",
  "인생 철학":             "예: '남한테 폐 끼치지 말자'는 게 신조예요. 어머니한테 들은 말인데 평생 지키고 있어요. 그 원칙이 언제부터였는지, 지키기 어려웠던 순간도 있었나요?",
  "앞으로의 나":           "예: 매일 새벽 수영 다니고, 여행 한 달에 한 번씩 다니고 싶어요. 10년 뒤 어떤 모습이면 좋을지, 지금과 뭐가 달라지길 바라는지 이야기해 주세요.",
  "앞으로의 꿈":           "예: 손자들 데리고 제주도 한 달 살기 해보고 싶어요. 꼭 해보고 싶은 것이 있으시면 왜 그게 하고 싶은지도 함께 말씀해 주세요.",
  "젊은이에게":            "예: 지금 힘든 게 다 쌓여서 나중에 자랑거리가 돼요. 버티세요. 살면서 배운 것 중 가장 중요하다고 생각하는 것을 솔직하게 말씀해 주세요.",
};

function getQuestions(birthDate: string): Question[] {
  if (!birthDate) return QUESTIONS_3040S;
  const birth = new Date(birthDate);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  ) age--;
  if (age < 30) return QUESTIONS_20S;
  if (age < 50) return QUESTIONS_3040S;
  if (age < 70) return QUESTIONS_5060S;
  return QUESTIONS_70PLUS;
}

function getPeriods(birthDate: string): string[] {
  if (!birthDate) return ["유년기", "청소년기", "청년기", "지금"];
  const birth = new Date(birthDate);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  ) age--;
  if (age < 30) return ["유년기", "청소년기", "지금"];
  if (age < 50) return ["유년기", "청소년기", "청년기", "지금"];
  return ["유년기", "청소년기", "청년기", "장년기", "지금"];
}

function fmtSeconds(s: number) {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

const emptyRecording = (): RecordingState => ({ status: "idle", blob: null, url: null, duration: 0 });

// ── Main ───────────────────────────────────────────────────────────────────────
export default function AutobiographyPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("intro");

  // Info
  const [name, setName]           = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [hometown, setHometown]   = useState("");

  // Image
  const [images, setImages]   = useState<File[]>([]);
  const imageInputRef         = useRef<HTMLInputElement>(null);

  // Font selection
  const [fontList, setFontList]             = useState<{fontId: string; fontName: string; type: string}[]>([]);
  const [selectedFontId, setSelectedFontId] = useState<string | null>(null);
  const [fontsLoading, setFontsLoading]     = useState(false);
  const [localFontFile, setLocalFontFile]   = useState<File | null>(null);
  const localFontInputRef                   = useRef<HTMLInputElement>(null);

  // Questions
  const [activeQuestions, setActiveQuestions] = useState<Question[]>(QUESTIONS_3040S);
  const [currentQIdx, setCurrentQIdx]         = useState(0);
  const [recordings, setRecordings]           = useState<RecordingState[]>(
    () => QUESTIONS_3040S.map(emptyRecording)
  );
  const [transcriptions, setTranscriptions]   = useState<string[]>(Array(QUESTIONS_3040S.length).fill(""));
  const [transcribing, setTranscribing]       = useState(false);
  const [qPlaying, setQPlaying]               = useState(false);
  const qAudioRef                             = useRef<HTMLAudioElement | null>(null);

  // Free entries (after structured questions)
  const [freeEntries, setFreeEntries]               = useState<FreeEntry[]>([]);
  const [currentFreeRecordIdx, setCurrentFreeRecordIdx] = useState<number | null>(null);
  const [freeTranscribing, setFreeTranscribing]     = useState(false);

  // Followup
  const [followupQuestions, setFollowupQuestions]           = useState<string[]>([]);
  const [followupRecordings, setFollowupRecordings]         = useState<RecordingState[]>([]);
  const [followupTranscriptions, setFollowupTranscriptions] = useState<string[]>([]);
  const [followupTranscribing, setFollowupTranscribing]     = useState(false);
  const [currentFIdx, setCurrentFIdx]                       = useState(0);
  const [loadingFollowup, setLoadingFollowup]               = useState(false);
  const [fPlaying, setFPlaying]                             = useState(false);
  const fAudioRef                                           = useRef<HTMLAudioElement | null>(null);

  // Keywords
  const [keywordCandidates, setKeywordCandidates] = useState<string[]>([]);
  const [selectedKeywords, setSelectedKeywords]   = useState<string[]>([]);
  const [keywordsLoading, setKeywordsLoading]     = useState(false);

  // Title
  const [titleInput, setTitleInput]       = useState("");
  const [titleGenerating, setTitleGenerating] = useState(false);

  // Generating
  const [progress, setProgress]       = useState(0);
  const progressIntervalRef           = useRef<NodeJS.Timeout | null>(null);

  // Recording engine
  const [isRecording, setIsRecording] = useState(false);
  const [recSeconds, setRecSeconds]   = useState(0);
  const recSecondsRef                 = useRef(0);
  const mediaRecorderRef              = useRef<MediaRecorder | null>(null);
  const chunksRef                     = useRef<Blob[]>([]);
  const timerRef                      = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => () => { timerRef.current && clearInterval(timerRef.current); }, []);

  // Update question set when birthDate changes
  useEffect(() => {
    if (!birthDate) return;
    const qs = getQuestions(birthDate);
    setActiveQuestions(qs);
    setRecordings(qs.map(emptyRecording));
    setTranscriptions(Array(qs.length).fill(""));
    setCurrentQIdx(0);
    setFreeEntries([]);
  }, [birthDate]);

  // ── Navigation helpers ────────────────────────────────────────────────────────
  const getNextQIdx = (fromIdx: number): number => {
    let next = fromIdx + 1;
    while (next < activeQuestions.length) {
      const q = activeQuestions[next];
      if (q.conditionalOn !== undefined && !transcriptions[q.conditionalOn]?.trim()) {
        next++;
      } else {
        return next;
      }
    }
    return activeQuestions.length; // free text screen
  };

  const getPrevQIdx = (fromIdx: number): number => {
    let prev = Math.min(fromIdx, activeQuestions.length) - 1;
    while (prev >= 0) {
      const q = activeQuestions[prev];
      if (q.conditionalOn !== undefined && !transcriptions[q.conditionalOn]?.trim()) {
        prev--;
      } else {
        return prev;
      }
    }
    return -1;
  };

  const isQSkipped = (idx: number): boolean => {
    const q = activeQuestions[idx];
    return q?.conditionalOn !== undefined && !transcriptions[q.conditionalOn]?.trim();
  };

  // ── Recording ────────────────────────────────────────────────────────────────
  const startRecording = async (onDone: (blob: Blob, url: string, duration: number) => void) => {
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
      const res = await api.post("/autobiography/transcribe", fd, { timeout: 0 });
      onResult(res.data.text ?? "");
    } catch {
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
    setRecordings((prev) => { const a = [...prev]; a[currentQIdx] = emptyRecording(); return a; });
    setTranscriptions((prev) => { const a = [...prev]; a[currentQIdx] = ""; return a; });
    setQPlaying(false);
  };

  const handleQFileUpload = (blob: Blob, url: string) => {
    const audio = new Audio(url);
    audio.addEventListener("loadedmetadata", () => {
      const duration = isFinite(audio.duration) ? Math.round(audio.duration) : 0;
      setRecordings((prev) => { const a = [...prev]; a[currentQIdx] = { status: "done", blob, url, duration }; return a; });
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

  // ── Free entry 핸들러 ─────────────────────────────────────────────────────────
  const addFreeEntry = () => {
    const periods = getPeriods(birthDate);
    setFreeEntries((prev) => [...prev, { period: periods[0], recording: emptyRecording(), transcription: "" }]);
  };

  const removeFreeEntry = (idx: number) => {
    setFreeEntries((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleFreeStart = (idx: number) => {
    setCurrentFreeRecordIdx(idx);
    setFreeEntries((prev) => {
      const a = [...prev];
      a[idx] = { ...a[idx], recording: { ...a[idx].recording, status: "recording" } };
      return a;
    });
    startRecording((blob, url, duration) => {
      setFreeEntries((prev) => {
        const a = [...prev];
        a[idx] = { ...a[idx], recording: { status: "done", blob, url, duration } };
        return a;
      });
      transcribeBlob(
        blob,
        (text) => setFreeEntries((prev) => {
          const a = [...prev];
          a[idx] = { ...a[idx], transcription: text };
          return a;
        }),
        setFreeTranscribing
      );
    });
  };

  const handleFreeReset = (idx: number) => {
    setFreeEntries((prev) => {
      const a = [...prev];
      a[idx] = { ...a[idx], recording: emptyRecording(), transcription: "" };
      return a;
    });
  };

  const handleFreeFileUpload = (idx: number, blob: Blob, url: string) => {
    const audio = new Audio(url);
    audio.addEventListener("loadedmetadata", () => {
      const duration = isFinite(audio.duration) ? Math.round(audio.duration) : 0;
      setFreeEntries((prev) => {
        const a = [...prev];
        a[idx] = { ...a[idx], recording: { status: "done", blob, url, duration } };
        return a;
      });
    });
    transcribeBlob(
      blob,
      (text) => setFreeEntries((prev) => {
        const a = [...prev];
        a[idx] = { ...a[idx], transcription: text };
        return a;
      }),
      setFreeTranscribing
    );
  };

  const getFormattedFreeText = () =>
    freeEntries
      .filter((e) => e.transcription.trim())
      .map((e) => `[${e.period}]\n${e.transcription}`)
      .join("\n\n");

  // ── Followup 녹음 핸들러 ──────────────────────────────────────────────────────
  const handleFStart = () => {
    setFollowupRecordings((prev) => {
      const a = [...prev]; a[currentFIdx] = { ...a[currentFIdx], status: "recording" }; return a;
    });
    startRecording((blob, url, duration) => {
      setFollowupRecordings((prev) => { const a = [...prev]; a[currentFIdx] = { status: "done", blob, url, duration }; return a; });
      transcribeBlob(
        blob,
        (text) => setFollowupTranscriptions((prev) => { const a = [...prev]; a[currentFIdx] = text; return a; }),
        setFollowupTranscribing
      );
    });
  };

  const handleFReset = () => {
    setFollowupRecordings((prev) => { const a = [...prev]; a[currentFIdx] = emptyRecording(); return a; });
    setFollowupTranscriptions((prev) => { const a = [...prev]; a[currentFIdx] = ""; return a; });
    setFPlaying(false);
  };

  const handleFFileUpload = (blob: Blob, url: string) => {
    const audio = new Audio(url);
    audio.addEventListener("loadedmetadata", () => {
      const duration = isFinite(audio.duration) ? Math.round(audio.duration) : 0;
      setFollowupRecordings((prev) => { const a = [...prev]; a[currentFIdx] = { status: "done", blob, url, duration }; return a; });
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
      const res = await api.post("/autobiography/generate-followups", {
        name, birthDate, hometown,
        freeText: getFormattedFreeText(),
        qas: activeQuestions.map((q, i) => ({
          question: q.text,
          category: q.category,
          answer: transcriptions[i],
        })),
      }, { timeout: 0 });
      const questions: string[] = res.data.followups ?? [];
      if (questions.length === 0) { goToKeyword(); return; }
      setFollowupQuestions(questions);
      setFollowupRecordings(questions.map(emptyRecording));
      setFollowupTranscriptions(Array(questions.length).fill(""));
      setCurrentFIdx(0);
    } catch {
      goToKeyword();
    } finally {
      setLoadingFollowup(false);
    }
  };

  const goToKeyword = async () => {
    setKeywordsLoading(true);
    setSelectedKeywords([]);
    setStep("keyword");
    try {
      const res = await api.post("/autobiography/suggest", {
        name, birth: birthDate,
        transcriptions,
        followup_transcriptions: followupTranscriptions,
      }, { timeout: 0 });
      setKeywordCandidates(res.data.keywords ?? []);
    } catch {
      setKeywordCandidates([]);
    } finally {
      setKeywordsLoading(false);
    }
  };

  const goToTitle = () => {
    setTitleInput("");
    setStep("keyword");
  };

  const generateTitle = async (keywords?: string[]) => {
    setTitleGenerating(true);
    try {
      const res = await api.post("/autobiography/suggest", {
        name, birth: birthDate,
        transcriptions,
        followup_transcriptions: followupTranscriptions,
        selected_keywords: keywords ?? selectedKeywords,
      }, { timeout: 0 });
      setTitleInput(res.data.title ?? "");
    } catch {
      /* 실패 시 빈 상태 유지 */
    } finally {
      setTitleGenerating(false);
    }
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
      fd.append("questions", JSON.stringify(activeQuestions.map((q) => q.text)));
      fd.append("transcriptions", JSON.stringify(transcriptions));
      fd.append("followup_transcriptions", JSON.stringify(followupTranscriptions));
      fd.append("free_text", getFormattedFreeText());
      fd.append("keywords", JSON.stringify(selectedKeywords));
      fd.append("title", titleInput);
      if (localFontFile) fd.append("font_file", localFontFile);
      else if (selectedFontId) fd.append("font_id", selectedFontId);
      images.forEach((img) => fd.append("images", img));

      const res = await api.post("/autobiography/generate", fd, { timeout: 0 });
      if (res.status === 200) {
        progressIntervalRef.current && clearInterval(progressIntervalRef.current);
        if (res.data.id) sessionStorage.setItem("autobiography_id", String(res.data.id));
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

  const fetchFonts = async () => {
    setFontsLoading(true);
    try {
      const res = await api.get("/fonts/list");
      setFontList(res.data ?? []);
    } catch {
      setFontList([]);
    } finally {
      setFontsLoading(false);
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
      <PrimaryButton disabled={!name || !birthDate || !hometown} onClick={() => { setStep("image"); fetchFonts(); }}>다음</PrimaryButton>
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
            className="w-full h-44 flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-brand-400 transition">
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
            <button onClick={() => imageInputRef.current?.click()} className="text-xs text-brand-400 mt-2">+ 더 추가</button>
          </div>
        )}
      </FieldCard>
      <input
        type="file"
        accept=".ttf,.otf"
        className="hidden"
        ref={localFontInputRef}
        onChange={(e) => {
          const file = e.target.files?.[0] ?? null;
          setLocalFontFile(file);
          if (file) setSelectedFontId(null);
          e.target.value = "";
        }}
      />
      <div className="bg-gray-100 rounded-2xl p-6 mb-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-bold text-gray-600">자서전에 사용할 폰트</p>
          {!fontsLoading && fontList.length === 0 && (
            <button onClick={fetchFonts} className="text-xs text-brand-400 hover:underline">불러오기</button>
          )}
        </div>
        {fontsLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
            <div className="w-4 h-4 border-2 border-brand-300 border-t-brand-500 rounded-full animate-spin" />
            불러오는 중...
          </div>
        ) : (
          <div className="space-y-2">
            <button
              onClick={() => { setSelectedFontId(null); setLocalFontFile(null); }}
              className={`w-full text-left px-4 py-3 rounded-xl text-sm font-medium transition ${
                selectedFontId === null && !localFontFile
                  ? "bg-brand-500 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
              }`}
            >
              기본 폰트 사용
            </button>
            {fontList.map((f) => (
              <button
                key={f.fontId}
                onClick={() => { setSelectedFontId(f.fontId); setLocalFontFile(null); }}
                className={`w-full text-left px-4 py-3 rounded-xl text-sm font-medium transition ${
                  selectedFontId === f.fontId
                    ? "bg-brand-500 text-white"
                    : "bg-white text-gray-600 hover:bg-gray-50 border border-gray-200"
                }`}
              >
                {f.fontName}
                <span className={`ml-2 text-xs ${selectedFontId === f.fontId ? "text-brand-100" : "text-gray-400"}`}>
                  {f.type === "AI" ? "AI 생성" : "직접 제작"}
                </span>
              </button>
            ))}
            {localFontFile ? (
              <div className={`w-full px-4 py-3 rounded-xl text-sm font-medium bg-brand-500 text-white flex items-center justify-between`}>
                <span className="truncate">{localFontFile.name}</span>
                <button onClick={() => setLocalFontFile(null)} className="ml-2 text-brand-200 hover:text-white shrink-0">
                  <X size={14} />
                </button>
              </div>
            ) : (
              <button
                onClick={() => localFontInputRef.current?.click()}
                className="w-full text-left px-4 py-3 rounded-xl text-sm font-medium bg-white text-gray-600 hover:bg-gray-50 border border-dashed border-gray-300 hover:border-brand-300 transition flex items-center gap-2"
              >
                <Upload size={14} className="text-gray-400" />
                내 컴퓨터에서 TTF/OTF 업로드
              </button>
            )}
            <p className="text-xs text-gray-400 pt-1">업로드한 폰트의 저작권 및 사용 권한은 사용자 본인에게 있습니다.</p>
          </div>
        )}
      </div>

      <div className="flex gap-3 mt-8">
        <SecondaryButton className="flex-1" onClick={() => setStep("info")}>이전</SecondaryButton>
        <PrimaryButton className="flex-1" onClick={() => { setCurrentQIdx(0); setStep("questions"); }}>다음</PrimaryButton>
      </div>
    </PageShell>
  );

  if (step === "questions") {
    const isFreeTextScreen = currentQIdx === activeQuestions.length;
    const nextIdx = isFreeTextScreen ? activeQuestions.length + 1 : getNextQIdx(currentQIdx);
    const prevIdx = isFreeTextScreen ? getPrevQIdx(activeQuestions.length) : getPrevQIdx(currentQIdx);
    const periods = getPeriods(birthDate);

    const dots = (
      <div className="flex gap-1">
        {[...activeQuestions, null].map((_, i) => {
          const skipped = i < activeQuestions.length && isQSkipped(i);
          return (
            <button
              key={i}
              onClick={() => !skipped && setCurrentQIdx(i)}
              className={`w-2 h-2 rounded-full transition ${
                i === currentQIdx       ? "bg-brand-400" :
                skipped                 ? "bg-gray-100" :
                i < activeQuestions.length && recordings[i]?.status === "done" ? "bg-brand-200" :
                i === activeQuestions.length && freeEntries.some((e) => e.transcription.trim()) ? "bg-brand-200" :
                "bg-gray-200"
              }`}
            />
          );
        })}
      </div>
    );

    if (isFreeTextScreen) return (
      <PageShell>
        <StepIndicator step={step} />
        <div className="flex items-center justify-between mb-6">
          <span className="text-sm text-gray-400 font-medium">자유 입력</span>
          {dots}
        </div>

        <p className="text-xl font-bold text-gray-800 mb-2">꼭 담고 싶은 이야기가 있으신가요?</p>
        <p className="text-sm text-gray-400 mb-6">시기를 선택하고 음성으로 말하거나 직접 입력해 주세요. (선택 사항)</p>

        {freeEntries.map((entry, idx) => (
          <div key={idx} className="bg-white border border-gray-100 rounded-2xl p-6 mb-4 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <select
                value={entry.period}
                onChange={(e) => setFreeEntries((prev) => {
                  const a = [...prev]; a[idx] = { ...a[idx], period: e.target.value }; return a;
                })}
                className="text-sm font-bold text-brand-500 bg-transparent outline-none cursor-pointer"
              >
                {periods.map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
              <button onClick={() => removeFreeEntry(idx)} className="text-gray-300 hover:text-red-400 transition">
                <X size={16} />
              </button>
            </div>
            <FreeEntryArea
              entry={entry}
              isRecordingThis={isRecording && currentFreeRecordIdx === idx}
              recSeconds={recSeconds}
              transcribing={freeTranscribing && currentFreeRecordIdx === idx}
              onStart={() => handleFreeStart(idx)}
              onStop={stopRecording}
              onReset={() => handleFreeReset(idx)}
              onTranscriptChange={(v) => setFreeEntries((prev) => {
                const a = [...prev]; a[idx] = { ...a[idx], transcription: v }; return a;
              })}
              onFileUpload={(blob, url) => handleFreeFileUpload(idx, blob, url)}
            />
          </div>
        ))}

        <button
          onClick={addFreeEntry}
          className="w-full py-4 border-2 border-dashed border-gray-200 rounded-2xl text-gray-400 hover:border-brand-300 hover:text-brand-400 transition flex items-center justify-center gap-2 mb-6"
        >
          <Plus size={16} />
          이야기 추가
        </button>

        <div className="flex gap-3">
          <SecondaryButton className="flex-1" onClick={() => {
            if (prevIdx === -1) setStep("image");
            else setCurrentQIdx(prevIdx);
          }}>
            이전
          </SecondaryButton>
          <PrimaryButton className="flex-1" onClick={handleQuestionsNext}>
            완료
          </PrimaryButton>
        </div>
      </PageShell>
    );

    const q   = activeQuestions[currentQIdx];
    const rec = recordings[currentQIdx] ?? emptyRecording();
    const tx  = transcriptions[currentQIdx] ?? "";

    return (
      <PageShell>
        <StepIndicator step={step} />
        <div className="flex items-center justify-between mb-8">
          <span className="text-sm text-gray-400 font-medium">질문 {currentQIdx + 1} / {activeQuestions.length}</span>
          {dots}
        </div>

        <div className="bg-gray-100 rounded-2xl p-8 mb-6">
          <p className="text-xs font-bold text-brand-400 uppercase tracking-widest mb-3">{q.category}</p>
          <p className="text-xl font-bold text-gray-800 leading-relaxed">{q.text}</p>
        </div>

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
          placeholder={QUESTION_HINTS[q.category]}
        />

        <div className="flex gap-3 mt-8">
          <SecondaryButton className="flex-1" onClick={() => {
            if (prevIdx === -1) setStep("image");
            else setCurrentQIdx(prevIdx);
          }}>
            이전
          </SecondaryButton>
          <PrimaryButton className="flex-1" onClick={() => setCurrentQIdx(nextIdx)}>
            {nextIdx >= activeQuestions.length ? "다음" : "다음 질문"}
          </PrimaryButton>
        </div>
      </PageShell>
    );
  }

  if (step === "followup") {
    if (loadingFollowup) return (
      <PageShell>
        <div className="flex flex-col items-center py-24 gap-4 text-gray-400">
          <div className="w-8 h-8 border-2 border-brand-300 border-t-brand-500 rounded-full animate-spin" />
          <span className="text-sm">부족한 답변을 분석하고 있어요...</span>
        </div>
      </PageShell>
    );

    const fq    = followupQuestions[currentFIdx];
    const frec  = followupRecordings[currentFIdx] ?? emptyRecording();
    const ftx   = followupTranscriptions[currentFIdx] ?? "";
    const isLast = currentFIdx === followupQuestions.length - 1;

    return (
      <PageShell>
        <StepIndicator step={step} />
        <div className="flex items-center justify-between mb-8">
          <span className="text-sm text-gray-400 font-medium">추가 질문 {currentFIdx + 1} / {followupQuestions.length}</span>
          <div className="flex gap-1">
            {followupQuestions.map((_, i) => (
              <button key={i} onClick={() => setCurrentFIdx(i)}
                className={`w-2 h-2 rounded-full transition ${i === currentFIdx ? "bg-brand-400" : followupRecordings[i]?.status === "done" ? "bg-brand-200" : "bg-gray-200"}`} />
            ))}
          </div>
        </div>

        <div className="bg-gray-100 rounded-2xl p-8 mb-6">
          <p className="text-xs font-bold text-brand-400 uppercase tracking-widest mb-3">추가 질문</p>
          <p className="text-xl font-bold text-gray-800 leading-relaxed">{fq}</p>
        </div>

        <RecordingArea
          recording={frec}
          isRecording={isRecording}
          recSeconds={recSeconds}
          transcribing={followupTranscribing}
          transcript={ftx}
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
          <PrimaryButton className="flex-1" onClick={() => isLast ? goToKeyword() : setCurrentFIdx((i) => i + 1)}>
            {isLast ? "완료" : "다음 질문"}
          </PrimaryButton>
        </div>
      </PageShell>
    );
  }

  if (step === "keyword") return (
    <PageShell>
      <StepIndicator step={step} />
      <h1 className="text-2xl font-bold mb-2">핵심 키워드 선택</h1>
      <p className="text-sm text-gray-400 mb-8">자서전의 분위기를 결정할 키워드를 2~3개 골라주세요.</p>
      {keywordsLoading ? (
        <div className="flex items-center justify-center py-16 text-gray-400 gap-3">
          <div className="w-5 h-5 border-2 border-gray-300 border-t-brand-500 rounded-full animate-spin" />
          <span className="text-sm">키워드 분석 중...</span>
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-3 mb-8">
            {keywordCandidates.map((kw) => {
              const active = selectedKeywords.includes(kw);
              return (
                <button
                  key={kw}
                  onClick={() => {
                    let next: string[];
                    if (active) {
                      next = selectedKeywords.filter((k) => k !== kw);
                    } else if (selectedKeywords.length < 3) {
                      next = [...selectedKeywords, kw];
                    } else {
                      return;
                    }
                    setSelectedKeywords(next);
                    if (next.length >= 2) generateTitle(next);
                  }}
                  className={`px-5 py-2.5 rounded-full text-sm font-medium border transition ${
                    active
                      ? "bg-brand-500 text-white border-brand-500"
                      : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
                  } ${!active && selectedKeywords.length >= 3 ? "opacity-40 cursor-not-allowed" : ""}`}
                >
                  {kw}
                </button>
              );
            })}
          </div>

          <div className="bg-gray-100 rounded-2xl p-6 mb-4">
            <p className="text-sm font-bold text-gray-600 mb-3">자서전 제목</p>
            {titleGenerating ? (
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <div className="w-4 h-4 border-2 border-gray-300 border-t-brand-500 rounded-full animate-spin" />
                제목 생성 중...
              </div>
            ) : (
              <input
                type="text"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                placeholder="직접 입력하거나 키워드 2개 이상 선택 시 자동 생성돼요"
                className="w-full bg-transparent outline-none text-gray-800 text-base placeholder-gray-300"
              />
            )}
          </div>

          {selectedKeywords.length >= 2 && (
            <button
              onClick={() => generateTitle()}
              disabled={titleGenerating}
              className="w-full py-4 rounded-2xl border border-brand-300 text-brand-500 font-bold hover:bg-brand-50 transition disabled:opacity-50 flex items-center justify-center gap-2 mb-6"
            >
              <Sparkles size={16} />
              {titleGenerating ? "생성 중..." : "AI로 제목 다시 생성"}
            </button>
          )}
        </>
      )}
      <div className="flex gap-3">
        <SecondaryButton className="flex-1" onClick={() => followupQuestions.length > 0 ? setStep("followup") : setStep("questions")}>
          이전
        </SecondaryButton>
        <PrimaryButton className="flex-1" onClick={handleGenerate} disabled={selectedKeywords.length < 2 && !titleInput.trim()}>
          자서전 생성 시작
        </PrimaryButton>
      </div>
    </PageShell>
  );

  if (step === "generating") {
    const steps = ["인터뷰 분석 중", "챕터 구성 중", "본문 작성 중", "표지 생성 중", "PDF 완성 중"];
    const stepIdx = Math.min(Math.floor(progress / 20), steps.length - 1);
    return (
      <div className="min-h-screen bg-gradient-to-b from-brand-50 to-white flex flex-col items-center justify-center px-6">
        <div className="w-full max-w-md text-center">
          <div className="relative w-24 h-24 mx-auto mb-10">
            <div className="absolute inset-0 rounded-full bg-brand-100 animate-ping opacity-40" />
            <div className="relative w-24 h-24 rounded-full bg-brand-500 flex items-center justify-center shadow-lg shadow-brand-200">
              <BookOpen size={36} className="text-white" />
            </div>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2">자서전을 만들고 있어요</h1>
          <p className="text-gray-400 text-sm mb-10">{name}님의 소중한 이야기를 담고 있습니다</p>

          <div className="relative w-full h-3 bg-gray-100 rounded-full overflow-hidden mb-3">
            <div className="absolute left-0 top-0 h-full bg-gradient-to-r from-brand-400 to-brand-600 rounded-full transition-all duration-500"
              style={{ width: `${progress}%` }} />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mb-8">
            <span>{steps[stepIdx]}</span>
            <span>{progress}%</span>
          </div>

          <div className="flex justify-center gap-2 mb-10">
            {steps.map((s, i) => (
              <div key={s} className={`flex flex-col items-center gap-1.5 ${i <= stepIdx ? "opacity-100" : "opacity-30"}`}>
                <div className={`w-2 h-2 rounded-full transition-all ${i < stepIdx ? "bg-brand-500" : i === stepIdx ? "bg-brand-400 scale-125" : "bg-gray-300"}`} />
              </div>
            ))}
          </div>

          <button onClick={() => { progressIntervalRef.current && clearInterval(progressIntervalRef.current); setStep("keyword"); }}
            className="text-sm text-gray-400 hover:text-gray-600 transition underline underline-offset-2">
            생성 취소
          </button>
        </div>
      </div>
    );
  }

  return null;
}

// ── FreeEntryArea ──────────────────────────────────────────────────────────────
function FreeEntryArea({
  entry, isRecordingThis, recSeconds, transcribing,
  onStart, onStop, onReset, onTranscriptChange, onFileUpload,
}: {
  entry: FreeEntry;
  isRecordingThis: boolean;
  recSeconds: number;
  transcribing: boolean;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
  onTranscriptChange: (v: string) => void;
  onFileUpload: (blob: Blob, url: string) => void;
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else { audioRef.current.play(); setIsPlaying(true); audioRef.current.onended = () => setIsPlaying(false); }
  };

  return (
    <RecordingArea
      recording={entry.recording}
      isRecording={isRecordingThis}
      recSeconds={recSeconds}
      transcribing={transcribing}
      transcript={entry.transcription}
      isPlaying={isPlaying}
      audioRef={audioRef}
      onStart={onStart}
      onStop={onStop}
      onReset={onReset}
      onTogglePlay={togglePlay}
      onTranscriptChange={onTranscriptChange}
      onFileUpload={onFileUpload}
    />
  );
}

// ── RecordingArea ──────────────────────────────────────────────────────────────
function RecordingArea({
  recording, isRecording, recSeconds, transcribing, transcript,
  isPlaying, audioRef, onStart, onStop, onReset, onTogglePlay, onTranscriptChange, onFileUpload,
  placeholder,
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
  placeholder?: string;
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
      <div className="bg-gray-100 rounded-2xl p-6">
        {recording.status === "idle" && !active && (
          <div className="flex justify-center gap-3">
            <button onClick={onStart}
              className="px-6 py-3 bg-brand-300 text-white font-bold rounded-xl hover:bg-brand-400 transition flex items-center gap-2">
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
              className="w-10 h-10 flex items-center justify-center bg-brand-300 text-white rounded-full hover:bg-brand-400 transition shrink-0">
              {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            </button>
            <audio ref={audioRef} src={recording.url} />
            <span className="text-sm text-gray-500 flex-1">녹음 완료 ({fmtSeconds(recording.duration)})</span>
            <button onClick={onReset} className="text-xs text-gray-400 hover:text-red-400 transition">
              다시 녹음
            </button>
          </div>
        )}
      </div>

      <div className="bg-gray-100 rounded-2xl p-6">
        <p className="text-xs font-bold text-gray-500 mb-3">
          답변 입력 <span className="text-gray-400 font-normal">(음성 변환 후 수정하거나 직접 입력하세요)</span>
        </p>
        {transcribing ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <div className="w-4 h-4 border-2 border-brand-300 border-t-brand-500 rounded-full animate-spin" />
            변환 중...
          </div>
        ) : (
          <textarea
            value={transcript}
            onChange={(e) => onTranscriptChange(e.target.value)}
            rows={5}
            placeholder={placeholder ?? "여기에 직접 입력하거나 위에서 녹음하세요."}
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
    { icon: <Mic2 size={20} />,     label: "음성으로 답변",    desc: "나이에 맞는 질문에 음성으로 답해요" },
    { icon: <FileText size={20} />, label: "즉시 텍스트 변환",  desc: "AI가 음성을 글로 바꾸고 수정할 수 있어요" },
    { icon: <Sparkles size={20} />, label: "AI 자서전 생성",    desc: "Claude가 나만의 자서전을 완성해요" },
    { icon: <BookOpen size={20} />, label: "폰트 적용 PDF",     desc: "손글씨 폰트가 담긴 PDF로 완성돼요" },
  ];

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-3xl mx-auto px-6 pt-16 pb-20">
        <div className="bg-gray-100 rounded-3xl p-10 mb-8">
          <p className="text-xs font-bold text-brand-400 uppercase tracking-widest mb-4">AI 자서전 시스템</p>
          <h2 className="text-3xl font-bold text-gray-900 leading-tight mb-4">
            당신의 이야기를<br />세상에 남겨보세요
          </h2>
          <p className="text-gray-500 text-sm leading-relaxed">
            음성으로 이야기하면 AI가 글로 정리하고, 나만의 손글씨 폰트가 담긴
            소중한 자서전 PDF를 만들어 드립니다.
          </p>
        </div>

        <div className="space-y-3 mb-8">
          {steps.map((s, i) => (
            <div key={i} className="flex items-center gap-4 bg-gray-50 rounded-2xl px-6 py-4">
              <div className="w-10 h-10 bg-brand-200 text-brand-600 rounded-xl flex items-center justify-center shrink-0">
                {s.icon}
              </div>
              <div className="flex-1">
                <p className="text-sm font-bold text-gray-800">{s.label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="border-2 border-amber-300 bg-amber-50 rounded-2xl p-6 mb-8">
          <p className="text-sm font-bold text-amber-800 mb-4">
            자서전 품질을 높이는 답변 방법
          </p>
          <div className="space-y-4">
            <div className="flex gap-3">
              <span className="w-5 h-5 rounded-full bg-amber-300 text-amber-900 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">1</span>
              <div>
                <p className="text-sm font-bold text-amber-900">구체적인 이름·장소·연도를 함께 말씀해 주세요</p>
                <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                  <span className="line-through opacity-60">"어릴 때 자주 놀러 갔어요"</span>
                  <br />
                  → "1975년 충남 공주 금강 둔치에서 친구 길수랑 물고기 잡던 기억이 나요"
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <span className="w-5 h-5 rounded-full bg-amber-300 text-amber-900 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">2</span>
              <div>
                <p className="text-sm font-bold text-amber-900">그때 어떤 기분이었는지도 함께 말씀해 주세요</p>
                <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                  <span className="line-through opacity-60">"합격했어요"</span>
                  <br />
                  → "합격 전화 받고 눈물이 났어요. 3년을 준비했거든요"
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <span className="w-5 h-5 rounded-full bg-amber-300 text-amber-900 text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">3</span>
              <div>
                <p className="text-sm font-bold text-amber-900">짧아도 괜찮아요 — 진짜 기억이면 충분합니다</p>
                <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                  길게 잘 정리하지 않아도 돼요. AI가 이야기를 글로 다듬어 드립니다.
                </p>
              </div>
            </div>
          </div>
        </div>

        <button onClick={onNext}
          className="w-full py-5 bg-brand-400 text-white font-bold rounded-2xl hover:bg-brand-500 transition text-lg">
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
          : "bg-brand-500 text-white hover:bg-brand-600 shadow-sm shadow-brand-100"
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
const MACRO_STEPS = ["기본 정보", "인터뷰", "제목", "생성"];

function stepIndexOf(step: Step): number {
  if (step === "info" || step === "image") return 0;
  if (step === "questions" || step === "followup") return 1;
  if (step === "keyword") return 2;
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
              i <= current ? "bg-brand-500 text-white" : "bg-gray-100 text-gray-400"
            }`}>
              {i < current ? <Check size={18} /> : i + 1}
            </div>
            <span className={`text-xs font-medium ${i <= current ? "text-gray-800" : "text-gray-400"}`}>
              {label}
            </span>
          </div>
          {i < MACRO_STEPS.length - 1 && (
            <div className={`flex-1 h-[1px] mx-3 mb-5 transition-colors ${i < current ? "bg-brand-500" : "bg-gray-200"}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}
