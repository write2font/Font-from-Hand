"use client";

import React, { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Mic, Square, Play, Pause, Upload, X, BookOpen, Mic2, FileText, Sparkles, Check, Plus } from "lucide-react";
import axios from "axios";
import api from "@/app/lib/axios";

// ── Types ──────────────────────────────────────────────────────────────────────
type Step = "intro" | "info" | "image" | "questions" | "keyword" | "generating";

interface RecordingState {
  status: "idle" | "recording" | "done";
  blob: Blob | null;
  url: string | null;
  duration: number;
}

interface Question {
  num: number;
  text: string;
  hint?: string;
  conditionalOn?: number;
}

interface FreeEntry {
  period: string;
  recording: RecordingState;
  transcription: string;
}

interface ImageItem {
  file: File;
  period: string;
  memo: string;
}

const IMAGE_PERIODS = ["어린 시절", "학창시절", "청년기", "직장·사회생활", "결혼·가정·육아", "현재"] as const;

// ── Question Pool (text + hint만, num 없음) ────────────────────────────────────
type QBase = Omit<Question, "num">;

// Q1: 이름
const QP_NAME: QBase = {
  text: "어릴 적 이름의 뜻을 알고 계신가요? 누가 지어주셨는지 혹시 들으신 적 있으신가요?",
  hint: "예: 이름에 '빛날 환'자가 들어간다고 들었어요. 할아버지가 직접 지어주셨다는데, 별명은 전혀 달랐어요…",
};

// Q2: 살던 집 · 동네
const QP_HOME_Y: QBase = {
  text: "어릴 때 살던 집이나 동네는 어떤 모습이었나요? 기억에 남는 장면이 있으신가요?",
  hint: "예: 골목 안쪽 작은 집이었는데, 대문 앞에 큰 나무가 있었어요. 여름에 그 그늘에서 친구들이랑 자주 놀았고…",
};
const QP_HOME_S: QBase = {
  text: "예전에 사셨던 집은 어떤 모습이었나요? 마당이나 부엌도 기억나시나요?",
  hint: "예: 대문 들어서면 큰 마당이 있었고, 우물도 있었어요. 부엌은 아궁이가 있어서 겨울에 거기 앉으면 너무 따뜻했어요…",
};

// Q3: 부모님
const QP_PARENTS_Y: QBase = {
  text: "부모님은 어떤 분들이셨나요? 지금도 기억에 남는 모습이 있으신가요?",
  hint: "예: 아버지는 말씀이 많지 않으셨는데 새벽마다 일찍 일어나셨어요. 어머니는 항상 무언가를 만드시는 분이셨고…",
};
const QP_PARENTS_S: QBase = {
  text: "부모님은 어떤 분들이셨나요? 어떤 일을 하셨고, 성격은 어떠셨나요?",
  hint: "예: 아버지는 말씀이 적으셨지만 새벽마다 일어나 논에 나가셨어요. 어머니는 노래를 잘 하셔서 일하시면서 항상 흥얼거리셨죠…",
};

// Q4: 형제자매
const QP_SIBLINGS_Y: QBase = {
  text: "형제자매가 있으신가요? 함께 자라면서 기억에 남는 일이 있으신가요?",
  hint: "예: 오빠가 한 명 있었는데 맨날 싸우면서도 학교는 항상 같이 다녔어요. 지금 생각하면 그 시절이 제일 좋았던 것 같아요…",
};
const QP_SIBLINGS_S: QBase = {
  text: "형제자매가 몇 분이셨나요? 그중 제일 친하셨던 분 이야기도 해주세요.",
  hint: "예: 다섯 남매였는데 제가 셋째였어요. 첫째 언니가 항상 저를 챙겨줬는데, 지금 생각하면 그게 얼마나 고마운 일인지…",
};

// Q5: 초등학교
const QP_ELEMENTARY_Y: QBase = {
  text: "초등학교 시절 이야기를 들려주세요. 좋아하셨던 선생님이나 친구, 즐겨 하시던 놀이가 있으셨나요?",
  hint: "예: 미술 선생님이 제 그림을 칠판에 붙여주셨는데 그게 너무 기뻤어요. 하굣길에 친구들이랑 구슬치기 하던 것도 생각나고…",
};
const QP_ELEMENTARY_S: QBase = {
  text: "초등학교 시절 이야기를 들려주세요. 학교까지 어떻게 다니셨고, 좋아하셨던 선생님이나 친구들 이야기가 있으신가요?",
  hint: "예: 4킬로를 걸어서 다녔어요. 한문 선생님이 칠판에 글씨 쓰시던 모습이 아직도 눈에 선해요. 도시락 나눠 먹던 친구도 생각나고…",
};

// Q6: 중학교
const QP_MIDDLE_Y: QBase = {
  text: "중학교 시절로 돌아가 보면 어떤 모습이 먼저 떠오르시나요? 그때 가장 가깝게 지내셨던 친구나 인상에 남은 선생님이 있으셨나요?",
  hint: "예: 중학교 때 처음으로 진짜 친한 친구가 생겼어요. 그 친구랑 매일 같이 하굣길을 걸었는데, 체육 선생님도 유독 기억에 남고…",
};
const QP_MIDDLE_S: QBase = {
  text: "중학교 시절로 돌아가 보면 어떤 모습이 먼저 떠오르시나요? 가깝게 지내셨던 친구나 선생님이 있으셨나요?",
  hint: "예: 그 시절엔 학교까지 멀었는데도 친구들이랑 같이 다니니까 멀게 느껴지지 않았어요. 선생님 기억도 선하고…",
};

// Q7: 고등학교
const QP_HIGH_Y: QBase = {
  text: "고등학교 때는 어떠셨나요? 공부, 진로 고민, 혹은 그 시절 푹 빠지셨던 것이 있으셨나요?",
  hint: "예: 입시 압박이 심했는데 그래도 점심시간에 친구들이랑 놀던 기억이 제일 선해요. 야간자율학습 끝나고 편의점 가던 것도…",
};
const QP_HIGH_S: QBase = {
  text: "고등학교 시절은 어떠셨나요? 힘드셨던 점이나 반대로 신나셨던 기억이 있으신가요?",
  hint: "예: 집이 멀어서 학교 근처 하숙을 했는데 처음으로 혼자 지내는 게 외롭기도 하고 자유롭기도 했어요…",
};

// Q8: 꿈 · 장래희망
const QP_DREAM_Y: QBase = {
  text: "어릴 때 어떤 꿈이나 장래희망을 가지고 계셨나요? 그 꿈은 어디서 생겨났나요?",
  hint: "예: 수의사가 되고 싶었는데, 동물을 무척 좋아했어요. 그 꿈이 나중에 어떻게 됐는지도 이야기해 주세요…",
};
const QP_DREAM_S: QBase = {
  text: "어릴 때 어떤 꿈이나 장래희망을 가지고 계셨나요? 그 꿈은 어떻게 됐나요?",
  hint: "예: 선생님이 되고 싶었는데 형편이 여의치 않아 다른 길을 걸었어요. 그 꿈이 지금의 삶 어딘가에 남아있는 것 같기도 하고…",
};

// ── 군복무 질문 ────────────────────────────────────────────────────────────────
const Q_MILITARY_20S: Question = {
  text: "군 복무를 하셨거나 하고 계신가요? 군 생활 중 마음에 남는 순간이나 전우 이야기를 들려주세요.",
  hint: "예: 자대 배치 받고 나서 처음으로 혼자라는 걸 실감했어요. 같이 야간 보초를 서던 전우 이야기도 아직 생각나고…",
} as unknown as Question;

const Q_MILITARY_SENIOR: Question = {
  text: "군 복무를 하셨나요? 훈련소 시절이나 자대에서 있었던 일, 함께하셨던 전우 이야기를 들려주세요.",
  hint: "예: 논산 훈련소에서 처음 삭발할 때 눈물이 날 뻔했어요. 야간 보초 서면서 별을 보며 전우랑 이야기 많이 했죠…",
} as unknown as Question;

// ── 대학 시절 질문 2개 (학력 선택 시 조건부 삽입) ──────────────────────────
const Q_COLLEGE_1: Question = {
  text: "대학에 진학하셨을 때 전공은 어떻게 선택하게 됐나요? 처음 캠퍼스에 들어서시던 날이 떠오르시나요?",
  hint: "예: 처음엔 다른 전공을 생각했는데 우연한 계기로 이쪽에 오게 됐어요. 첫날 강의실 찾다가 길을 잃었던 게 생각나고…",
} as unknown as Question;

const Q_COLLEGE_2: Question = {
  text: "대학 시절 가장 빠져드셨던 것이 있으셨나요? 동아리, 교수님, 친구들과의 이야기가 있다면 들려주세요.",
  hint: "예: 밴드 동아리에 들어갔는데 거기서 평생 친구를 만났어요. 특별히 영향받은 교수님이나 수업이 있었는지도요…",
} as unknown as Question;

// ── 20대 (Q1-Q8 공통 + Q9-Q16) ───────────────────────────────────────────────
const QUESTIONS_20S: Question[] = [
  { num: 1,  ...QP_NAME },
  { num: 2,  ...QP_HOME_Y },
  { num: 3,  ...QP_PARENTS_Y },
  { num: 4,  ...QP_SIBLINGS_Y },
  { num: 5,  ...QP_ELEMENTARY_Y },
  { num: 6,  ...QP_MIDDLE_Y },
  { num: 7,  ...QP_HIGH_Y },
  { num: 8,  ...QP_DREAM_Y },
  { num: 9,  text: "처음으로 혼자서 뭔가를 해내셨던 경험이 있으신가요? 어떤 도전이었고, 힘드셨던 부분도 있으셨나요?",
    hint: "예: 처음 혼자 기차 타고 여행 간 날이요. 표 끊는 것도 서툴렀고 포기하고 싶은 순간도 있었는데, 막상 해보니 할 수 있더라고요…" },
  { num: 10, text: "지금 하고 계신 일이나 공부는 어떻게 선택하게 됐나요? 어떤 계기가 있으셨나요?",
    hint: "예: 사실 처음엔 전혀 다른 걸 생각했는데, 어느 날 우연히 접하고 나서 방향이 바뀌었어요. 그때 어떤 생각이었는지도요…" },
  { num: 11, text: "그 일이나 공부에서 '내가 잘하고 있구나' 싶었던 순간이 있으신가요?",
    hint: "예: 처음 혼자 뭔가를 끝냈을 때요. 결과물이 작아도 뭔가 해냈다는 느낌이 그렇게 뿌듯할 수가 없었어요…" },
  { num: 12, text: "연애 이야기를 들려주세요. 첫사랑이나 지금 곁에 계신 분이 있으신가요?",
    hint: "예: 첫사랑은 중학교 때였는데 말 한마디 못 해봤어요. 지금 사귀는 분이 있다면 어떻게 만나셨는지도 이야기해 주세요…" },
  { num: 13, text: "요즘 푹 빠져계신 취미나 꼭 해보고 싶으신 것이 있으신가요?",
    hint: "예: 요즘 필름 카메라에 빠졌는데, 혼자 사진 찍으러 나가는 시간이 제일 좋아요. 아니면 언젠가 꼭 해보고 싶은 것도요…" },
  { num: 14, text: "나에게 가장 큰 영향을 주신 분은 누구인가요? 어떤 영향을 받으셨나요?",
    hint: "예: 고2 담임 선생님이요. 그분이 하신 말 한마디가 지금도 방향을 잡아줄 때가 있어요…" },
  { num: 15, text: "지금 가장 고민되거나 마음에 걸리는 게 있으신가요?",
    hint: "예: 진로 방향이 맞는 건지 자꾸 흔들려요. 관계나 앞으로의 삶에 대해 고민하는 것도 이야기해 주셔도 돼요…" },
  { num: 16, text: "10년 뒤 어떤 모습이면 좋겠나요? 꼭 해보고 싶으신 일이 있으신가요?",
    hint: "예: 하고 싶은 일로 먹고살 수 있으면 좋겠어요. 거창한 게 아니라 그냥 좋아하는 것 하면서 지내는 삶…" },
];

// ── 30~40대 (Q1-Q8 공통 + Q9-Q19) ───────────────────────────────────────────
const QUESTIONS_3040S: Question[] = [
  { num: 1,  ...QP_NAME },
  { num: 2,  ...QP_HOME_Y },
  { num: 3,  ...QP_PARENTS_Y },
  { num: 4,  ...QP_SIBLINGS_Y },
  { num: 5,  ...QP_ELEMENTARY_Y },
  { num: 6,  ...QP_MIDDLE_Y },
  { num: 7,  ...QP_HIGH_Y },
  { num: 8,  ...QP_DREAM_Y },
  { num: 9,  text: "처음 사회에 나오셨을 때 어떤 일을 하셨나요? 첫 직장이나 첫 면접 이야기가 있으신가요?",
    hint: "예: 첫 면접 보러 정장을 처음 맞췄어요. 입사 첫날 어디서 밥을 먹어야 할지 몰라서 혼자 편의점에서…" },
  { num: 10, text: "일하면서 가장 고됐던 시기가 언제였나요? 그때 어떻게 버티셨나요?",
    hint: "예: 연속으로 야근하던 그 해가 제일 힘들었어요. 아무것도 안 되는 것 같았는데, 그래도 버틸 수 있었던 건…" },
  { num: 11, text: "커리어에서 가장 뿌듯하셨던 성취나 순간을 꼽아주세요.",
    hint: "예: 몇 년을 준비한 프로젝트가 처음으로 결실을 맺던 날이요. 그날 퇴근길이 유난히 가볍게 느껴졌어요…" },
  { num: 12, text: "지금 하시는 일이나 커리어 방향에 대해 이야기해 주세요. 어떻게 여기까지 오게 됐나요?",
    hint: "예: 처음 생각했던 길이랑 많이 달라졌어요. 돌아보면 그 변화들이 어떤 의미가 있는지…" },
  { num: 13, text: "연애·결혼 이야기를 들려주세요. 배우자나 파트너를 어떻게 만나셨나요?",
    hint: "예: 회사 동료였는데 야근하다가 처음 제대로 이야기를 나눴어요. 그날 이후로 자연스럽게 친해졌고…" },
  { num: 14, text: "가정을 꾸리면서 달라진 점이 있으신가요? 자녀 분이 계신다면 아이 이야기도 들려주세요.",
    hint: "예: 아이가 생기고 나서 우선순위가 완전히 바뀌었어요. 처음 안았을 때 그 느낌이 아직도 생생해요…" },
  { num: 15, text: "지금과 전혀 다른 길을 가실 뻔하셨던 순간이 있으신가요?",
    hint: "예: 서른 살에 회사 그만두고 유학을 갈까 진지하게 고민했어요. 결국 남기로 했는데, 그 선택이 맞았는지…" },
  { num: 16, text: "만약 그 선택을 하지 않으셨다면, 지금은 어떤 모습일 것 같으세요?",
    hint: "예: 유학 갔으면 지금 전혀 다른 사람이 됐을 것 같아요. 후회는 없지만 가끔 상상해보게 돼요…",
    conditionalOn: 15 },
  { num: 17, text: "요즘 즐기시는 취미나 꼭 해보고 싶으신 것이 있으신가요?",
    hint: "예: 주말마다 등산을 다니는데 그 시간이 제일 저만의 시간이에요. 언젠가 꼭 해보고 싶은 것도 있으시면요…" },
  { num: 18, text: "살면서 꼭 지키려 하셨던 원칙이나 가치관이 있으신가요?",
    hint: "예: '내가 한 말은 꼭 지킨다'는 게 오래된 원칙이에요. 그게 흔들린 순간도 있었는데, 그때가 생각나요…" },
  { num: 19, text: "앞으로 가장 해보고 싶으신 것이 있으신가요? 10년 뒤 어떤 모습이면 좋겠나요?",
    hint: "예: 가족이랑 오래 여행을 해보고 싶어요. 10년 뒤엔 지금보다 조금 더 여유 있는 사람이면 좋겠고…" },
];

// ── 50~60대 (Q1-Q8 시니어 공통 + Q9-Q23) ────────────────────────────────────
const QUESTIONS_5060S: Question[] = [
  { num: 1,  ...QP_NAME },
  { num: 2,  ...QP_HOME_S },
  { num: 3,  ...QP_PARENTS_S },
  { num: 4,  ...QP_SIBLINGS_S },
  { num: 5,  ...QP_ELEMENTARY_S },
  { num: 6,  ...QP_MIDDLE_S },
  { num: 7,  ...QP_HIGH_S },
  { num: 8,  ...QP_DREAM_S },
  { num: 9,  text: "처음 사회에 나오셨을 때 어떤 일을 하셨나요? 첫 출근이나 첫 직장 이야기를 들려주세요.",
    hint: "예: 공장 경리로 첫 출근한 날이요. 교복 입다가 처음으로 정장 입었는데 너무 어색했어요…" },
  { num: 10, text: "일하면서 가장 고됐던 시기가 언제였나요? 그때 어떻게 버티셨나요?",
    hint: "예: 사업이 어려웠던 몇 년이요. 가족한테 내색도 못하고 혼자 버텼는데, 그때 힘이 됐던 건…" },
  { num: 11, text: "일이나 커리어에서 가장 뿌듯하셨던 성취나 순간이 있으신가요?",
    hint: "예: 몇 년을 갈고닦은 일이 인정받던 날이요. 아니면 후배들이 잘 성장하는 걸 지켜봤을 때도요…" },
  { num: 12, text: "지금까지 가장 오래 함께하신 친구나 동료가 계신가요? 어떻게 인연이 됐나요?",
    hint: "예: 입사 첫날 밥 사줬던 선배예요. 그분이 어떤 분이었는지, 어떻게 친해졌는지 이야기해 주세요…" },
  { num: 13, text: "배우자 분은 어떻게 만나셨나요? 연애였는지 중매였는지도 궁금해요.",
    hint: "예: 동네 친구 결혼식에서 처음 봤어요. 한눈에 알아봤는지 자꾸 눈이 마주쳤죠…" },
  { num: 14, text: "결혼식 하셨을 때 이야기를 들려주세요. 긴장됐던 순간이나 재미난 에피소드가 있으셨나요?",
    hint: "예: 결혼식 날 너무 긴장해서 주례 말씀이 하나도 안 들렸어요. 피로연에서 어머니가 우셨는데 그게 지금도 생각나요…" },
  { num: 15, text: "자녀들이 어릴 때 이야기를 해주세요. 육아하면서 가장 힘드셨던 때도 함께 들려주시겠어요?",
    hint: "예: 첫째 낳던 날 너무 기뻐서 울었어요. 그런데 밤새 울어대던 때는 정말 한계였죠. 그때 어떻게 버티셨는지도요…" },
  { num: 16, text: "'이제 우리 아이가 다 컸구나' 하고 느끼셨던 순간이 언제였나요?",
    hint: "예: 고등학교 졸업식 날 양복 입은 아들 보고 '이제 어른이 됐구나' 싶었어요. 어느 순간 그런 느낌이 드셨나요?…" },
  { num: 17, text: "살아오시면서 가장 큰 위기가 있으셨다면 어떤 시기였나요? 어떻게 넘기셨나요?",
    hint: "예: 경제적으로 제일 어려웠던 시기가 있었어요. 아니면 건강이나 가족 때문에 힘드셨던 적도요…" },
  { num: 18, text: "건강 면에서 달라지심을 느끼신 건 언제부터였나요?",
    hint: "예: 마흔 넘어서 갑자기 체력이 예전 같지 않다는 걸 느꼈어요. 그때부터 뭔가 챙기시게 된 것도 있으신가요…" },
  { num: 19, text: "요즘 즐기시는 취미나 빠져계신 것이 있으신가요?",
    hint: "예: 텃밭 가꾸는 게 요즘 낙이에요. 아니면 예전부터 꼭 해보고 싶었는데 이제야 하게 된 것도요…" },
  { num: 20, text: "요즘 하루하루를 어떻게 보내고 계신가요? 가장 즐거우신 시간이 있으신가요?",
    hint: "예: 새벽에 산책하는 게 요즘 낙이에요. 그 시간에 무슨 생각을 하시는지도 이야기해 주세요…" },
  { num: 21, text: "살면서 가장 중요하게 지켜오신 가치나 마음가짐이 있으셨나요?",
    hint: "예: '남한테 폐 끼치지 말자'는 게 신조예요. 어머니한테 들은 말인데 평생 지키고 있어요…" },
  { num: 22, text: "앞으로 가장 해보고 싶으신 것이 있으신가요?",
    hint: "예: 손자들 데리고 제주도 한 달 살기 해보고 싶어요. 아직 못 이룬 꿈이 있으시면 이야기해 주세요…" },
  { num: 23, text: "자녀나 소중한 분께 꼭 남기고 싶은 말이 있다면요?",
    hint: "예: 말로는 잘 못 했는데, 늘 고맙고 자랑스럽다는 걸 전하고 싶어요…" },
];

// ── 70대 이상 (Q1-Q8 시니어 공통 + Q9-Q26) ───────────────────────────────────
const QUESTIONS_70PLUS: Question[] = [
  { num: 1,  ...QP_NAME },
  { num: 2,  ...QP_HOME_S },
  { num: 3,  ...QP_PARENTS_S },
  { num: 4,  ...QP_SIBLINGS_S },
  { num: 5,  ...QP_ELEMENTARY_S },
  { num: 6,  ...QP_MIDDLE_S },
  { num: 7,  ...QP_HIGH_S },
  { num: 8,  ...QP_DREAM_S },
  { num: 9,  text: "사회에 처음 나가셨을 때 어떤 일을 하셨나요? 그때 이야기 들려주세요.",
    hint: "예: 공장에서 일을 시작했는데 첫날 기계 소리에 너무 놀랐어요. 그 시절 동료 이야기도 생각나시면요…" },
  { num: 10, text: "일하면서 가장 고됐던 시기가 언제였나요? 그때 어떻게 버티셨나요?",
    hint: "예: 가장 힘들었던 그 시절, 가족한테 내색도 못하고 혼자 버텼어요. 그래도 버틸 수 있었던 건…" },
  { num: 11, text: "일하시면서 가장 뿌듯하셨던 성취나 보람 있으셨던 순간이 있으신가요?",
    hint: "예: 평생 일하면서 가장 잘했다고 생각하는 것, 혹은 인정받으셨던 기억이 있으시면요…" },
  { num: 12, text: "배우자 분은 어떻게 만나셨나요? 연애였는지 중매였는지도 궁금해요.",
    hint: "예: 동네 친구 결혼식에서 처음 봤어요. 한눈에 알아봤는지 자꾸 눈이 마주쳤죠…" },
  { num: 13, text: "결혼식 하셨을 때 이야기를 들려주세요. 긴장됐던 순간이나 재미난 에피소드가 있으셨나요?",
    hint: "예: 결혼식 날 너무 긴장해서 주례 말씀이 하나도 안 들렸어요. 피로연에서 어머니가 우셨는데 그게 지금도 생각나요…" },
  { num: 14, text: "아이들 낳으셨을 때 첫 느낌이 어떠셨는지 들려주세요.",
    hint: "예: 첫째 낳던 날 남편이 병원 복도에서 서성이다 실신했다는 이야기를 나중에 들었어요…" },
  { num: 15, text: "아이들 키우시면서 가장 즐거우셨던 일과 가장 힘드셨던 일이 있으셨나요?",
    hint: "예: 밤새 기침하는 아이 등을 두드리다 보면 새벽이 됐어요. 그래도 그 시절이 지금은 가장 행복했던 것 같아요…" },
  { num: 16, text: "'이제 우리 아이가 다 컸구나' 하고 느끼셨던 순간이 언제였나요?",
    hint: "예: 고등학교 졸업식 날 양복 입은 아들 보고 '이제 어른이 됐구나' 싶었어요. 어느 순간 그 느낌이 드셨나요?…" },
  { num: 17, text: "살아오시면서 가장 큰 위기가 있으셨다면 어떤 시기였나요? 어떻게 넘기셨나요?",
    hint: "예: 경제적으로 가장 어려웠던 때, 혹은 건강이나 가족 때문에 무너질 것 같았던 시기가 있으셨나요…" },
  { num: 18, text: "건강 면에서 달라지심을 느끼신 건 언제부터였나요?",
    hint: "예: 예순 넘어서 갑자기 체력이 예전 같지 않다는 걸 느꼈어요. 그때부터 챙기시게 된 것들이 있으신가요…" },
  { num: 19, text: "지금 살고 계신 동네나 집은 어떤가요? 편안하신가요?",
    hint: "예: 30년째 이 동네 살고 있어요. 골목 어귀 느티나무가 봄에 싹이 트면 또 한 해가 시작됐구나 싶어요…" },
  { num: 20, text: "요즘 즐기시는 취미나 낙이 있으신가요?",
    hint: "예: 화초 가꾸는 게 요즘 낙이에요. 아니면 손주들이랑 노는 시간, 오랫동안 하고 싶었는데 이제야 하는 것도요…" },
  { num: 21, text: "하루 일과는 보통 어떻게 보내세요? 아침엔 뭘 하시나요?",
    hint: "예: 새벽 5시에 일어나서 라디오 듣고, 6시에 산책 나가요. 돌아와서 미음 끓여 먹고 손자들 전화 기다리는 게 요즘 낙이에요…" },
  { num: 22, text: "살아오시면서 가장 중요하게 지켜오신 가치나 마음가짐이 있으셨나요?",
    hint: "예: '남한테 폐 끼치지 말자'는 게 신조예요. 어머니한테 들은 말인데 평생 지키고 있어요…" },
  { num: 23, text: "살아오면서 가장 감사하신 분이나 일이 있다면요?",
    hint: "예: 평생 건강하게 살아온 것만으로도 감사해요. 그리고 옆에서 묵묵히 함께해준 배우자요…" },
  { num: 24, text: "자녀나 손주에게 꼭 남기고 싶으신 말씀이 있다면요?",
    hint: "예: '지금 이 순간을 소중히 여겨라'고 말해주고 싶어요. 내가 젊었을 때 그게 얼마나 중요한지 몰랐거든요…" },
  { num: 25, text: "배우자에게 하고 싶으신 말씀은 무엇인가요?",
    hint: "예: 고생 많았다는 말을 평생 제대로 못 했어요. 이 자리에서라도 말하고 싶어요…" },
  { num: 26, text: "지금 젊은 분들에게 꼭 하고 싶으신 말씀이 있으신가요?",
    hint: "예: 지금 힘든 게 다 쌓여서 나중에 자랑거리가 돼요. 버티세요. 살면서 배운 것 중 가장 중요하다고 생각하는 것을 솔직하게요…" },
];



function insertAfterQ(
  base: Question[],
  newQ: Question,
  insertAfterNum: number
): Question[] {
  const insertIdx = base.findIndex((q) => q.num === insertAfterNum) + 1;
  const before = base.slice(0, insertIdx);
  const after = base.slice(insertIdx).map((q) => ({
    ...q,
    num: q.num + 1,
    ...(q.conditionalOn !== undefined ? { conditionalOn: q.conditionalOn + 1 } : {}),
  }));
  return [...before, { ...newQ, num: insertAfterNum + 1 }, ...after];
}

// kept for backwards-compatibility at call sites
const insertMilitaryQuestion = insertAfterQ;

const COLLEGE_EDUCATION_VALUES = ["대학교 졸업", "대학원 이상", "대학교 재학 중"];

function getQuestions(birthDate: string, militaryService: string = "", education: string = ""): Question[] {
  if (!birthDate) return QUESTIONS_3040S;
  const birth = new Date(birthDate);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  if (
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  ) age--;

  const military = militaryService === "군필";
  const hasCollege = COLLEGE_EDUCATION_VALUES.includes(education);

  let base: Question[];
  let militaryQ: Question;
  if (age < 30) { base = QUESTIONS_20S;    militaryQ = Q_MILITARY_20S; }
  else if (age < 50) { base = QUESTIONS_3040S; militaryQ = Q_MILITARY_SENIOR; }
  else if (age < 70) { base = QUESTIONS_5060S; militaryQ = Q_MILITARY_SENIOR; }
  else { base = QUESTIONS_70PLUS; militaryQ = Q_MILITARY_SENIOR; }

  // 대학 질문 2개를 Q8(꿈) 뒤에 삽입 (학력 해당자만)
  if (hasCollege) {
    base = insertAfterQ(base, Q_COLLEGE_1, 8);   // → Q9
    base = insertAfterQ(base, Q_COLLEGE_2, 9);   // → Q10
  }

  // 군복무 질문을 대학 질문 뒤(또는 Q8 뒤)에 삽입
  if (military) base = insertAfterQ(base, militaryQ, hasCollege ? 10 : 8);

  return base;
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
  const [gender, setGender]       = useState<"남성" | "여성" | "">("");
  const [education, setEducation] = useState("");
  const [religion, setReligion]   = useState("");

  // Military service
  const [militaryService, setMilitaryService] = useState<"군필" | "미필" | "해당없음" | "">("");

  // Writing style
  const [writingStyle, setWritingStyle] = useState<"서술체" | "경어체">("서술체");

  // Image (파일 + 시기 + 메모)
  const [images, setImages]   = useState<ImageItem[]>([]);
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

  // Update question set when birthDate, militaryService, or education changes
  useEffect(() => {
    if (!birthDate) return;
    const qs = getQuestions(birthDate, militaryService, education);
    setActiveQuestions(qs);
    setRecordings(qs.map(emptyRecording));
    setTranscriptions(Array(qs.length).fill(""));
    setCurrentQIdx(0);
    setFreeEntries([]);
  }, [birthDate, militaryService, education]);

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

  // ── Step transitions ──────────────────────────────────────────────────────────
  const goToKeyword = async () => {
    setKeywordsLoading(true);
    setSelectedKeywords([]);
    setStep("keyword");
    try {
      const res = await api.post("/autobiography/suggest", {
        name, birth: birthDate,
        transcriptions,
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
        selected_keywords: keywords ?? selectedKeywords,
      }, { timeout: 0 });
      setTitleInput(res.data.title ?? "");
    } catch {
      /* 실패 시 빈 상태 유지 */
    } finally {
      setTitleGenerating(false);
    }
  };

  const [generateError, setGenerateError] = useState("");

  const handleGenerate = async () => {
    setStep("generating");
    setProgress(0);
    setGenerateError("");
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
      fd.append("followup_transcriptions", "[]");
      fd.append("free_text", getFormattedFreeText());
      fd.append("keywords", JSON.stringify(selectedKeywords));
      fd.append("title", titleInput);
      fd.append("writing_style", writingStyle);
      fd.append("gender", gender);
      fd.append("military_service", militaryService);
      fd.append("education", education);
      fd.append("religion", religion);
      if (localFontFile) fd.append("font_file", localFontFile);
      else if (selectedFontId) fd.append("font_id", selectedFontId);
      images.forEach(({ file }) => fd.append("images", file));
      fd.append("image_tags", JSON.stringify(images.map(({ period, memo }) =>
        period + (memo.trim() ? ` — ${memo.trim()}` : "")
      )));

      const res = await api.post("/autobiography/generate", fd, { timeout: 0 });
      if (res.status === 200) {
        progressIntervalRef.current && clearInterval(progressIntervalRef.current);
        if (res.data.id) sessionStorage.setItem("autobiography_id", String(res.data.id));
        setProgress(100);
        setTimeout(() => router.push("/autobiography/result"), 800);
      }
    } catch (err: unknown) {
      progressIntervalRef.current && clearInterval(progressIntervalRef.current);
      const msg =
        (err as { response?: { data?: { error?: string } } })?.response?.data?.error
        || "자서전 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.";
      setGenerateError(msg);
      setProgress(0);
      setStep("keyword");
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
      <FieldCard label="성별">
        <div className="flex gap-3">
          {(["남성", "여성"] as const).map((g) => (
            <button key={g} onClick={() => setGender(g)}
              className={`flex-1 py-2 rounded-xl text-sm font-medium border transition ${
                gender === g ? "bg-brand-500 text-white border-brand-500" : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
              }`}>
              {g}
            </button>
          ))}
        </div>
      </FieldCard>
      <FieldCard label="병역 여부">
        <div className="flex gap-3">
          {(["군필", "미필", "해당없음"] as const).map((v) => (
            <button key={v} onClick={() => setMilitaryService(v)}
              className={`flex-1 py-2 rounded-xl text-sm font-medium border transition ${
                militaryService === v ? "bg-brand-500 text-white border-brand-500" : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
              }`}>
              {v}
            </button>
          ))}
        </div>
      </FieldCard>
      <FieldCard label="출신지">
        <input type="text" placeholder="예: 충남 공주시" value={hometown}
          onChange={(e) => setHometown(e.target.value)}
          className="w-full bg-transparent outline-none text-gray-800 placeholder-gray-400 text-base" />
      </FieldCard>
      <FieldCard label="최종 학력">
        <select value={education} onChange={(e) => setEducation(e.target.value)}
          className="w-full bg-transparent outline-none text-gray-800 text-base">
          <option value="">선택 안 함</option>
          <option value="무학">무학</option>
          <option value="초등학교 졸업">초등학교 졸업</option>
          <option value="중학교 졸업">중학교 졸업</option>
          <option value="고등학교 졸업">고등학교 졸업</option>
          <option value="대학교 재학 중">대학교 재학 중</option>
          <option value="대학교 졸업">대학교 졸업</option>
          <option value="대학원 이상">대학원 이상</option>
        </select>
      </FieldCard>
      <FieldCard label="종교 (선택)">
        <input type="text" placeholder="예: 불교, 기독교, 천주교, 무교 등"
          value={religion} onChange={(e) => setReligion(e.target.value)}
          className="w-full bg-transparent outline-none text-gray-800 placeholder-gray-400 text-base" />
      </FieldCard>
      <PrimaryButton disabled={!name || !birthDate || !gender || !militaryService || !hometown} onClick={() => { setStep("image"); fetchFonts(); }}>다음</PrimaryButton>
    </PageShell>
  );

  if (step === "image") return (
    <PageShell>
      <StepIndicator step={step} />
      <h1 className="text-2xl font-bold mb-8">기본 정보 입력</h1>
      <FieldCard label="자서전에 넣고픈 이미지 업로드">
        <input type="file" accept="image/*" multiple className="hidden" ref={imageInputRef}
          onChange={(e) => {
            if (e.target.files)
              setImages((p) => [...p, ...Array.from(e.target.files!).map((f) => ({ file: f, period: "", memo: "" }))]);
          }} />
        {images.length === 0 ? (
          <button onClick={() => imageInputRef.current?.click()}
            className="w-full h-44 flex flex-col items-center justify-center gap-2 text-gray-400 hover:text-brand-400 transition">
            <Upload size={32} />
            <span className="text-sm">클릭하여 이미지 추가</span>
          </button>
        ) : (
          <div className="space-y-3">
            {images.map((item, i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-xl p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-700 truncate flex-1 mr-2">{item.file.name}</span>
                  <button onClick={() => setImages((p) => p.filter((_, j) => j !== i))}>
                    <X size={16} className="text-gray-400 hover:text-red-400" />
                  </button>
                </div>
                <p className="text-xs text-gray-400 mb-1.5">어떤 시기의 사진인가요?</p>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {IMAGE_PERIODS.map((p) => (
                    <button
                      key={p}
                      onClick={() => setImages((prev) => prev.map((it, j) =>
                        j === i ? { ...it, period: it.period === p ? "" : p } : it
                      ))}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium border transition ${
                        item.period === p
                          ? "bg-brand-500 text-white border-brand-500"
                          : "bg-white text-gray-500 border-gray-200 hover:border-brand-300"
                      }`}
                    >
                      {p}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="추가 설명 (선택) 예: 첫 직장 동료들과"
                  value={item.memo}
                  onChange={(e) => setImages((p) => p.map((it, j) => j === i ? { ...it, memo: e.target.value } : it))}
                  className="w-full text-xs text-gray-600 bg-gray-50 rounded-lg px-3 py-2 outline-none focus:ring-1 focus:ring-brand-300 placeholder-gray-300"
                />
              </div>
            ))}
            <button onClick={() => imageInputRef.current?.click()} className="text-xs text-brand-400 mt-1">+ 더 추가</button>
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
          <PrimaryButton className="flex-1" onClick={goToKeyword}>
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
          placeholder={q.hint}
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

  if (step === "keyword") return (
    <PageShell>
      <StepIndicator step={step} />
      <h1 className="text-2xl font-bold mb-2">핵심 키워드 선택</h1>
      <p className="text-sm text-gray-400 mb-8">자서전의 분위기를 결정할 키워드를 2~3개 골라주세요.</p>
      {generateError && (
        <div className="bg-red-50 border border-red-200 rounded-2xl px-5 py-4 mb-6 text-sm text-red-600">
          ⚠️ {generateError}
        </div>
      )}
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

          <div className="bg-gray-100 rounded-2xl p-6 mb-4">
            <p className="text-sm font-bold text-gray-600 mb-3">자서전 문체 선택</p>
            <p className="text-xs text-gray-400 mb-3">생성될 자서전의 말투를 선택해주세요.</p>
            <div className="flex gap-3">
              {(["서술체", "경어체"] as const).map((style) => (
                <button key={style} onClick={() => setWritingStyle(style)}
                  className={`flex-1 py-3 rounded-xl text-sm font-medium border transition ${
                    writingStyle === style ? "bg-brand-500 text-white border-brand-500" : "bg-white text-gray-600 border-gray-200 hover:border-brand-300"
                  }`}>
                  {style === "서술체" ? "서술체 (~했다)" : "경어체 (~했습니다)"}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
      <div className="flex gap-3">
        <SecondaryButton className="flex-1" onClick={() => setStep("questions")}>
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
  if (step === "questions") return 1;
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
