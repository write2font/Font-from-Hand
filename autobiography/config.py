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
WHISPER_MODEL  = "large-v3"
LLM_MODEL      = "claude-sonnet-4-6"  # 충남대 Gateway - Claude Sonnet
LLM_MAX_TOKENS = 2000  # 타임아웃 방지

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
# 6. 자서전 챕터 구조
# ─────────────────────────────────────────
CHAPTER_STRUCTURE = [
    {
        "title":     "프롤로그",
        "q_numbers": [1],
        "questions": ["Q1. 성함과 생년월일, 유년 시절을 보낸 고향은 어디인가요?"],
        "guide":     "독자에게 이 사람이 누구인지 소개하는 도입부. 이름, 고향, 시대적 배경을 따뜻하게 풀어주세요.",
    },
    {
        "title":     "뿌리",
        "q_numbers": [2, 3, 4],
        "questions": [
            "Q2. 부모님은 어떤 분이셨으며, 형제들 사이에서 주로 어떤 역할이었나요?",
            "Q3. 어린 시절 가장 좋아했던 장소와 그곳의 분위기를 묘사해 주세요.",
            "Q4. 유년 시절을 떠올리면 가장 먼저 생각나는 상징적인 사건이나 장면은?",
        ],
        "guide": "가족, 동네 풍경, 기억 속 한 장면 등 유년의 감각적인 이미지를 중심으로 서술하세요.",
    },
    {
        "title":     "꿈의 씨앗",
        "q_numbers": [5, 6],
        "questions": [
            "Q5. 어린 시절의 꿈은 무엇이었으며, 현재의 직업/전공을 선택한 결정적 계기는?",
            "Q6. 학창 시절 가장 열정적으로 몰두했던 공부나 활동은 무엇이었나요?",
        ],
        "guide": "꿈이 싹트고 정체성이 형성되는 시기. 열정과 방향성을 중심으로 서술하세요.",
    },
    {
        "title":     "세상 속으로",
        "q_numbers": [7, 8],
        "questions": [
            "Q7. 청년 시절 가장 뜨거웠던 기억(첫 취업, 시대적 사건 등)은 무엇인가요?",
            "Q8. 인생의 방향을 바꿔놓을 만큼 큰 영향을 준 스승이나 친구, 동료가 있나요?",
        ],
        "guide": "사회에 첫발을 내딛고 인연을 맺는 시기. 생동감 있는 에피소드 중심으로 서술하세요.",
    },
    {
        "title":     "겨울을 지나며",
        "q_numbers": [9, 10],
        "questions": [
            "Q9. 인생에서 가장 힘들었던 시기는 언제였으며, 무엇이 가장 괴롭혔나요?",
            "Q10. 그 시련을 어떻게 버텨내셨으며, 그 과정에서 무엇을 배우셨나요?",
        ],
        "guide": "인생의 가장 어두운 순간과 그것을 이겨낸 힘. 독자에게 감동과 울림을 주도록 서술하세요.",
    },
    {
        "title":     "빛나는 날들",
        "q_numbers": [11, 12],
        "questions": [
            "Q11. '이것만큼은 정말 잘했다'고 자부하는 가장 큰 업적이나 결과물은?",
            "Q12. 인생의 경로가 180도 바뀌었던 결정적인 선택의 순간과 그 이유는?",
        ],
        "guide": "자부심과 전환점. 삶의 절정을 이루는 순간들을 힘 있게 서술하세요.",
    },
    {
        "title":     "에필로그",
        "q_numbers": [13, 14, 15],
        "questions": [
            "Q13. 평생을 지탱해 온 좌우명이나 꼭 지키고자 했던 원칙은 무엇인가요?",
            "Q14. 다시 태어난다면 해보고 싶은 일, 후배 세대에게 전하고 싶은 한마디는?",
            "Q15. 훗날 사람들이 당신을 어떤 사람으로 기억해주길 바라시나요?",
        ],
        "guide": "삶의 지혜와 유산을 남기는 마무리. 따뜻하고 묵직한 울림으로 마무리하세요.",
    },
]

# ─────────────────────────────────────────
# 7. 확장 챕터 구조 (80페이지용, 15챕터)
# ─────────────────────────────────────────
CHAPTER_STRUCTURE_EXTENDED = [
    {
        "title": "프롤로그",
        "questions": ["Q1. 성함과 생년월일, 유년 시절을 보낸 고향은 어디인가요?"],
        "guide": "독자에게 이 사람이 누구인지 소개하는 도입부. 이름, 고향, 시대적 배경을 따뜻하게 풀어주세요.",
        "region_context": True,   # 지역 정보 활용
        "era_context":   True,    # 시대 배경 활용
    },
    {
        "title": "고향의 풍경",
        "questions": ["Q1. 성함과 생년월일, 유년 시절을 보낸 고향은 어디인가요?",
                      "Q3. 어린 시절 가장 좋아했던 장소와 그곳의 분위기를 묘사해 주세요."],
        "guide": "고향 마을의 자연환경, 계절, 냄새, 소리 등 감각적 묘사. 지역 역사와 지리 정보를 녹여주세요.",
        "region_context": True,
        "era_context":   False,
    },
    {
        "title": "가족의 초상",
        "questions": ["Q2. 부모님은 어떤 분이셨으며, 형제들 사이에서 주로 어떤 역할이었나요?"],
        "guide": "가족 한 명 한 명을 생생하게 묘사. 부모님의 직업, 성격, 가족 간의 관계와 따뜻한 에피소드.",
        "region_context": False,
        "era_context":   True,
    },
    {
        "title": "기억의 조각들",
        "questions": ["Q4. 유년 시절을 떠올리면 가장 먼저 생각나는 상징적인 사건이나 장면은?"],
        "guide": "선명하게 기억나는 한 장면을 영화처럼 묘사. 오감을 활용한 감각적 서술.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "시대의 물결",
        "questions": ["Q1. 성함과 생년월일, 유년 시절을 보낸 고향은 어디인가요?"],
        "guide": "저자가 태어난 시대의 역사적 배경과 사회상. 6.25 전후, 산업화, 시대적 사건들을 개인의 삶과 연결.",
        "region_context": True,
        "era_context":   True,
    },
    {
        "title": "첫 꿈",
        "questions": ["Q5. 어린 시절의 꿈은 무엇이었으며, 현재의 직업/전공을 선택한 결정적 계기는?"],
        "guide": "처음으로 꿈을 가졌던 순간. 그 꿈의 배경과 당시의 감정을 섬세하게.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "배움의 날들",
        "questions": ["Q6. 학창 시절 가장 열정적으로 몰두했던 공부나 활동은 무엇이었나요?"],
        "guide": "학교생활의 구체적인 에피소드. 선생님, 친구들, 특별한 수업, 운동회 등.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "청춘의 온도",
        "questions": ["Q7. 청년 시절 가장 뜨거웠던 기억(첫 취업, 시대적 사건 등)은 무엇인가요?"],
        "guide": "청년기의 뜨거운 감정과 에너지. 설렘, 두려움, 희망이 공존하는 시절.",
        "region_context": False,
        "era_context":   True,
    },
    {
        "title": "인연",
        "questions": ["Q8. 인생의 방향을 바꿔놓을 만큼 큰 영향을 준 스승이나 친구, 동료가 있나요?"],
        "guide": "삶을 바꾼 만남. 그 사람과의 구체적인 에피소드와 그가 남긴 영향.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "가장 긴 겨울",
        "questions": ["Q9. 인생에서 가장 힘들었던 시기는 언제였으며, 무엇이 가장 괴롭혔나요?"],
        "guide": "시련의 구체적인 상황과 감정. 독자가 함께 고통을 느낄 수 있도록 생생하게.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "다시 일어서며",
        "questions": ["Q10. 그 시련을 어떻게 버텨내셨으며, 그 과정에서 무엇을 배우셨나요?"],
        "guide": "시련을 극복하는 과정의 내면 변화. 포기하고 싶었던 순간과 다시 일어선 계기.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "내 손으로 만든 것",
        "questions": ["Q11. '이것만큼은 정말 잘했다'고 자부하는 가장 큰 업적이나 결과물은?"],
        "guide": "삶의 가장 큰 성취를 자랑스럽게 서술. 구체적인 과정과 결과.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "갈림길에서",
        "questions": ["Q12. 인생의 경로가 180도 바뀌었던 결정적인 선택의 순간과 그 이유는?"],
        "guide": "인생의 전환점이 된 선택. 그 선택 앞에서의 고민과 용기.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "내가 믿는 것들",
        "questions": ["Q13. 평생을 지탱해 온 좌우명이나 꼭 지키고자 했던 원칙은 무엇인가요?"],
        "guide": "삶의 철학을 깊이 있게. 그 원칙이 형성된 배경과 실제 삶에서의 적용.",
        "region_context": False,
        "era_context":   False,
    },
    {
        "title": "에필로그",
        "questions": ["Q14. 다시 태어난다면 해보고 싶은 일, 후배 세대에게 전하고 싶은 한마디는?",
                      "Q15. 훗날 사람들이 당신을 어떤 사람으로 기억해주길 바라시나요?"],
        "guide": "다음 세대에게 전하는 따뜻한 유언. 삶의 지혜와 사랑을 담은 마무리.",
        "region_context": False,
        "era_context":   False,
    },
]
