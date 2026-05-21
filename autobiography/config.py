"""
config.py
전역 설정 파일 - API 키, 경로, 페르소나 임계값 등
"""

import os
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_BASE_DIR, ".env"), override=True)

# ─────────────────────────────────────────
# 1. API 키
# ─────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY") or os.getenv("CNU_API_KEY", "")  # 충남대 Gateway 키
OPENAI_BASE_URL = "https://factchat-cloud.mindlogic.ai/v1/gateway"  # 충남대 Gateway

# ─────────────────────────────────────────
# 2. 모델 설정
# ─────────────────────────────────────────
WHISPER_MODEL  = "large-v2"
LLM_MODEL      = "claude-sonnet-4-6"  # 충남대 Gateway - Claude Sonnet
LLM_MAX_TOKENS = 5000  # 챕터 2500자 이상 완성 보장

# ─────────────────────────────────────────
# 3. 나이대별 페르소나 임계값
# ─────────────────────────────────────────
AGE_THRESHOLDS = {
    "senior":     50,   # 50대 이상
    "middle":     35,   # 35~49세
    "young_adult": 25,  # 25~34세
    # 25 미만 → Youth
}

PERSONA_PROMPTS = {
    "Senior": (
        "당신은 50대 이상 중장년의 이야기를 집필하는 작가입니다. "
        "인생의 무게와 연륜이 느껴지는 회고록 스타일로, 삶의 깊이와 진솔함을 담아 서술하세요. "
        "반드시 '-다', '-었다', '-이다' 체의 평서형 문어체로만 서술하세요. "
        "존댓말(-습니다)은 절대 사용하지 마세요."
    ),
    "Middle": (
        "당신은 35~49세 직장인·전문직의 이야기를 정리하는 작가입니다. "
        "커리어와 개인적 성장, 일과 삶의 균형을 중심으로 담백하고 솔직한 에세이 스타일로 서술하세요. "
        "과거 향수나 고전적 감성보다는 현재 시점의 성찰과 경험을 중심으로 쓰세요. "
        "반드시 '-다', '-었다', '-이다' 체의 평서형 문어체로만 서술하세요. "
        "존댓말(-습니다)은 절대 사용하지 마세요."
    ),
    "YoungAdult": (
        "당신은 25~34세 청년의 이야기를 기록하는 작가입니다. "
        "성장과 도전, 방황과 발견이 교차하는 시기를 생생하고 직접적인 문체로 서술하세요. "
        "감각적이고 구체적인 에피소드 중심으로, 젊은 세대의 언어와 감성을 살려 쓰세요. "
        "반드시 '-다', '-었다', '-이다' 체의 평서형 문어체로만 서술하세요. "
        "존댓말(-습니다)은 절대 사용하지 마세요."
    ),
    "Youth": (
        "당신은 20대 초반 청년의 이야기를 기록하는 작가입니다. "
        "꿈과 열정, 설렘과 불안이 공존하는 시기를 패기 있고 솔직한 문체로 서술하세요. "
        "반드시 '-다', '-었다', '-이다' 체의 평서형 문어체로만 서술하세요. "
        "존댓말(-습니다)은 절대 사용하지 마세요."
    ),
}

# ─────────────────────────────────────────
# 4. 디렉토리 경로
# ─────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATA_DIR       = os.path.join(BASE_DIR, "data")
RAW_AUDIO_DIR  = os.path.join(DATA_DIR, "01_raw_audio")
TRANSCRIPT_DIR = os.path.join(DATA_DIR, "02_transcripts")
SUMMARY_DIR    = os.path.join(DATA_DIR, "03_summaries")
FONT_DIR       = os.path.join(DATA_DIR, "04_user_fonts")
ASSETS_DIR     = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR     = os.path.join(BASE_DIR, "output")

# ─────────────────────────────────────────
# 5. PDF 레이아웃 설정
# ─────────────────────────────────────────
PDF_PAGE_SIZE       = "A6"
PDF_MARGIN_MM       = 8
PDF_TITLE_FONT_SIZE = 13
PDF_BODY_FONT_SIZE  = 10
PDF_LINE_HEIGHT     = 8
PDF_FALLBACK_FONT   = "assets/templates/NanumGothic.ttf"
PDF_KOPUB_FONT      = "assets/templates/KoPubBatangMedium.ttf"

USE_DEFAULT_FONT = True   # True: 기본 폰트 사용, False: 사용자 폰트

# ─────────────────────────────────────────
# 6. 자서전 챕터 구조 (나이대별)
# title은 AI가 자유 생성 — 여기선 폴백용 빈 문자열
# q_numbers는 프론트엔드 질문 순서(1-based)
# ─────────────────────────────────────────

# 20대 (9문항)
CHAPTER_STRUCTURE_20S = [
    {"q_numbers": [],     "guide": "독자에게 이 사람이 누구인지 소개하는 도입부. 이름, 고향, 태어난 배경을 따뜻하게 풀어주세요.", "is_prologue": True},
    {"q_numbers": [1, 2], "guide": "유년 시절의 감각적인 장면 중심으로 서술하세요. 자주 가던 장소, 집에서 먹던 음식, 동네 풍경 등 구체적인 이미지로 그 시절을 살려내세요."},
    {"q_numbers": [3, 5], "guide": "학창 시절과 꿈이 형성되는 시기. 가장 열정을 쏟았던 것, 어린 시절의 꿈, 지금의 자신과 연결되는 선택의 씨앗을 서술하세요."},
    {"q_numbers": [4],    "guide": "지금도 이어지는 소중한 인연의 시작. 그 첫 만남의 순간을 생생한 장면으로 서술하세요."},
    {"q_numbers": [6],    "guide": "무언가를 위해 정말 고생했던 기억. 그것을 버텨낸 힘과 그 과정에서 얻은 것을 독자에게 울림 있게 서술하세요."},
    {"q_numbers": [7],    "guide": "주변에 자랑하고 싶었던 빛나는 순간. 뿌듯함을 힘 있게 서술하세요."},
    {"q_numbers": [8, 9], "guide": "닮고 싶은 사람과 10년 뒤의 나. 앞을 향한 바람과 삶의 지혜로 따뜻하게 마무리하세요.", "is_epilogue": True},
]

# 30~40대 (11문항)
CHAPTER_STRUCTURE_3040S = [
    {"q_numbers": [],        "guide": "독자에게 이 사람이 누구인지 소개하는 도입부. 이름, 고향, 태어난 배경을 따뜻하게 풀어주세요.", "is_prologue": True},
    {"q_numbers": [1],       "guide": "유년 시절의 감각적인 장면 중심으로 서술하세요. 기억에 남는 장소와 풍경, 그 시절의 냄새와 소리를 살려내세요."},
    {"q_numbers": [2],       "guide": "학창 시절의 열정. 가장 몰두했던 것, 지금의 자신과 연결되는 선택의 씨앗을 서술하세요."},
    {"q_numbers": [3, 4],    "guide": "사회에 첫발을 내딛고 인연을 맺는 시기. 첫 도전과 소중한 만남을 생동감 있는 에피소드로 서술하세요."},
    {"q_numbers": [5, 6],    "guide": "인생의 전환점과 '만약에'의 순간. 그 선택이 지금의 나를 어떻게 만들었는지 서술하세요."},
    {"q_numbers": [7],       "guide": "가장 고되고 버거웠던 시기. 어떻게 버텼는지, 그 과정에서 얻은 것을 독자에게 울림 있게 서술하세요."},
    {"q_numbers": [8, 9],    "guide": "가장 뿌듯했던 순간과 가족과 함께한 소중한 기억. 자부심과 따뜻함이 함께 느껴지게 서술하세요."},
    {"q_numbers": [10, 11],  "guide": "살면서 지켜온 원칙과 앞으로의 꿈. 삶의 지혜와 바람으로 묵직하게 마무리하세요.", "is_epilogue": True},
]

# 50~60대 (11문항)
# Q7(만약에)는 Q6(삶의전환점) 조건부 → Q6·Q7 같은 챕터
CHAPTER_STRUCTURE_5060S = [
    {"q_numbers": [],        "guide": "독자에게 이 사람이 누구인지 소개하는 도입부. 이름, 고향, 태어난 시대 배경을 따뜻하게 풀어주세요.", "is_prologue": True},
    {"q_numbers": [1, 2],    "guide": "유년 시절의 감각적인 장면 중심으로 서술하세요. 자주 가던 장소, 집에서 먹던 음식 등 구체적인 이미지로 그 시절을 살려내세요."},
    {"q_numbers": [3],       "guide": "학창 시절의 열정. 가장 몰두했던 것, 지금의 자신과 연결되는 선택의 씨앗을 서술하세요."},
    {"q_numbers": [4, 5],    "guide": "첫 사회생활과 오랜 인연. 사회에 첫발을 내딛던 순간과 소중한 만남을 생동감 있게 서술하세요."},
    {"q_numbers": [6, 7],    "guide": "인생의 전환점과 '만약에'의 순간. 그 선택이 지금의 나를 어떻게 만들었는지 서술하세요."},
    {"q_numbers": [8],       "guide": "가장 고되고 버겁던 시기. 어떻게 버텼는지, 그 과정에서 얻은 것을 독자에게 울림 있게 서술하세요."},
    {"q_numbers": [9],       "guide": "가장 뿌듯했던 빛나는 순간. 자부심을 힘 있게 서술하세요."},
    {"q_numbers": [10, 11],  "guide": "살면서 지켜온 원칙과 앞으로의 꿈. 삶의 지혜와 바람으로 묵직하게 마무리하세요.", "is_epilogue": True},
]

# 70대 이상 (11문항)
# Q9(만약에)는 Q8(내가제일빛났을때) 조건부 → Q8·Q9 같은 챕터
# Q5(첫사회생활)/Q7(오래된인연) → 세상속으로 / Q6 → 시련 챕터
CHAPTER_STRUCTURE_70PLUS = [
    {"q_numbers": [],        "guide": "독자에게 이 사람이 누구인지 소개하는 도입부. 이름, 고향, 태어난 시대 배경을 따뜻하게 풀어주세요.", "is_prologue": True},
    {"q_numbers": [1, 2, 3], "guide": "유년 시절의 감각적인 장면 중심으로 서술하세요. 고향, 음식, 아끼던 물건 등 구체적인 이미지로 그 시절을 살려내세요."},
    {"q_numbers": [4],       "guide": "학창 시절 좋아했던 것과 열정. 꿈이 싹트던 시절, 지금의 자신과 연결되는 씨앗을 서술하세요."},
    {"q_numbers": [5, 7],    "guide": "첫 사회생활과 중요한 인연. 생동감 있는 에피소드로 서술하세요."},
    {"q_numbers": [6],       "guide": "가장 힘들었던 시기와 그것을 버텨낸 힘. 고생했던 기억과 그 과정에서 얻은 것을 울림 있게 서술하세요."},
    {"q_numbers": [8, 9],    "guide": "인생에서 가장 잘했다고 자부하는 성취와, 만약 다른 선택을 했다면의 순간. 자부심과 여운 있게 서술하세요."},
    {"q_numbers": [10, 11],  "guide": "평생 지켜온 원칙과 젊은이에게 전하고 싶은 말. 따뜻하고 묵직하게 마무리하세요.", "is_epilogue": True},
]

# 폴백 — 70대 이상 구조와 동일
CHAPTER_STRUCTURE = CHAPTER_STRUCTURE_70PLUS

# ─────────────────────────────────────────
# 7. 확장 챕터 구조 (80페이지용, 15챕터)
# ─────────────────────────────────────────
CHAPTER_STRUCTURE_EXTENDED = [
    {"q_numbers": [],        "guide": "독자에게 이 사람이 누구인지 소개하는 도입부. 이름, 고향, 시대적 배경을 따뜻하게 풀어주세요.", "region_context": True,  "era_context": True,  "is_prologue": True},
    {"q_numbers": [1, 3],    "guide": "고향 마을의 자연환경, 계절, 냄새, 소리 등 감각적 묘사. 지역 역사와 지리 정보를 녹여주세요.",                     "region_context": True,  "era_context": False},
    {"q_numbers": [2],       "guide": "가족 한 명 한 명을 생생하게 묘사. 부모님의 직업, 성격, 가족 간의 관계와 따뜻한 에피소드.",                       "region_context": False, "era_context": True},
    {"q_numbers": [4],       "guide": "선명하게 기억나는 한 장면을 영화처럼 묘사. 오감을 활용한 감각적 서술.",                                           "region_context": False, "era_context": False},
    {"q_numbers": [],        "guide": "저자가 태어난 시대의 역사적 배경과 사회상. 시대적 사건들을 개인의 삶과 연결.",                                      "region_context": True,  "era_context": True},
    {"q_numbers": [5],       "guide": "처음으로 꿈을 가졌던 순간. 그 꿈의 배경과 당시의 감정을 섬세하게.",                                               "region_context": False, "era_context": False},
    {"q_numbers": [6],       "guide": "학교생활의 구체적인 에피소드. 선생님, 친구들, 특별한 수업, 운동회 등.",                                            "region_context": False, "era_context": False},
    {"q_numbers": [7],       "guide": "청년기의 뜨거운 감정과 에너지. 설렘, 두려움, 희망이 공존하는 시절.",                                              "region_context": False, "era_context": True},
    {"q_numbers": [8],       "guide": "삶을 바꾼 만남. 그 사람과의 구체적인 에피소드와 그가 남긴 영향.",                                                 "region_context": False, "era_context": False},
    {"q_numbers": [9],       "guide": "시련의 구체적인 상황과 감정. 독자가 함께 고통을 느낄 수 있도록 생생하게.",                                          "region_context": False, "era_context": False},
    {"q_numbers": [10],      "guide": "시련을 극복하는 과정의 내면 변화. 포기하고 싶었던 순간과 다시 일어선 계기.",                                        "region_context": False, "era_context": False},
    {"q_numbers": [11],      "guide": "삶의 가장 큰 성취를 자랑스럽게 서술. 구체적인 과정과 결과.",                                                      "region_context": False, "era_context": False},
    {"q_numbers": [12],      "guide": "인생의 전환점이 된 선택. 그 선택 앞에서의 고민과 용기.",                                                           "region_context": False, "era_context": False},
    {"q_numbers": [13],      "guide": "삶의 철학을 깊이 있게. 그 원칙이 형성된 배경과 실제 삶에서의 적용.",                                               "region_context": False, "era_context": False},
    {"q_numbers": [14, 15],  "guide": "다음 세대에게 전하는 따뜻한 유언. 삶의 지혜와 사랑을 담은 마무리.",                                                "region_context": False, "era_context": False, "is_epilogue": True},
]
