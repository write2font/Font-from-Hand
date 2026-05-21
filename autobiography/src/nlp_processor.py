"""
src/nlp_processor.py
NLP 프로세서 - 자서전 본문 생성 (지역 정보 + 확장 챕터 지원)
"""

import os
import sys
import json
import re
import time
from datetime import datetime

from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config

client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)


class NLPProcessor:
    def __init__(self, extended: bool = False):
        self.thresholds = config.AGE_THRESHOLDS
        self.chapter_structure = (
            config.CHAPTER_STRUCTURE_EXTENDED if extended
            else config.CHAPTER_STRUCTURE
        )
        os.makedirs(config.SUMMARY_DIR, exist_ok=True)

    def _get_chapter_structure_by_age(self, age: int) -> list:
        if age < 30:
            return config.CHAPTER_STRUCTURE_20S
        elif age < 50:
            return config.CHAPTER_STRUCTURE_3040S
        elif age < 70:
            return config.CHAPTER_STRUCTURE_5060S
        else:
            return config.CHAPTER_STRUCTURE_70PLUS

    def _generate(self, system_prompt: str, user_prompt: str, max_tokens: int = None) -> str:
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    max_tokens=max_tokens or config.LLM_MAX_TOKENS,
                    timeout=90,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"  ⚠️  시도 {attempt+1}/3 실패: {type(e).__name__} - 5초 후 재시도...")
                if attempt < 2:
                    time.sleep(5)
        return "(생성 실패)"

    def _parse_json(self, text: str) -> dict:
        raw = re.sub(r"```[a-z]*", "", text).replace("```", "").strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)

    # ──────────────────────────────────────────
    # 1. 나이 / 페르소나
    # ──────────────────────────────────────────

    def calculate_age(self, birth_date_str: str) -> int:
        return datetime.now().year - int(birth_date_str.split("-")[0])

    def determine_persona(self, birth_date_str: str) -> str:
        age = self.calculate_age(birth_date_str)
        if age >= self.thresholds["senior"]:
            return "Senior"
        elif age >= self.thresholds["middle"]:
            return "Middle"
        elif age >= self.thresholds["young_adult"]:
            return "YoungAdult"
        return "Youth"

    # ──────────────────────────────────────────
    # 2. 키워드 추출
    # ──────────────────────────────────────────

    def extract_keywords(self, transcript_text: str, birth_date_str: str) -> dict:
        birth_year = birth_date_str.split("-")[0]
        prompt = f"""다음 인터뷰 텍스트를 분석하여 아래 JSON 형식으로만 응답하세요.
코드블록 없이 순수 JSON만 출력하세요.
저자의 실제 생년은 {birth_year}년입니다.

{{
  "birth_year": "{birth_year}",
  "region": "고향 지역명",
  "events": ["사건1", "사건2"],
  "people": ["인물1", "인물2"],
  "places": ["장소1", "장소2"],
  "emotions": ["감정1", "감정2"]
}}

인터뷰 텍스트:
{transcript_text[:2000]}"""

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        try:
            return self._parse_json(response.choices[0].message.content)
        except Exception as e:
            print(f"[NLP] ⚠️  키워드 추출 실패 ({e}), 기본값 사용")
            return {"birth_year": birth_year, "region": "", "events": [], "people": [], "places": [], "emotions": []}

    # ──────────────────────────────────────────
    # 3. 챕터 제목 생성
    # ──────────────────────────────────────────

    def extract_keyword_candidates(self, transcript_text: str, birth_date_str: str) -> list:
        """카테고리별 키워드 후보를 추출해서 사용자 선택용으로 반환합니다."""
        system = (
            "분석 과정이나 카테고리 설명 없이 "
            "쉼표로 구분된 한국어 키워드만 한 줄로 출력하십시오."
        )
        prompt = (
            f"다음 인터뷰를 읽고, 이 사람의 삶을 대표하는 키워드를 아래 5개 카테고리에서 각 2~3개씩 추출하라.\n"
            f"반드시 인터뷰에 명시적으로 언급된 내용만 사용하라. 추론하거나 없는 내용을 절대 만들지 마라.\n\n"
            f"카테고리 (각 2~3개씩, 총 12개):\n"
            f"1. 장소/배경: 언급된 지명·장소 (예: 울산, 고향 마을)\n"
            f"2. 삶의 가치/좌우명: 인터뷰에 명시된 좌우명·원칙을 핵심 명사로 압축 (반드시 1개 이상, 예: 후회없음, 끈기, 정직)\n"
            f"3. 중요한 경험: 언급된 사건·도전·선택의 순간 (예: 공대 진학, 창업)\n"
            f"4. 정체성/역할: 언급된 직업·역할 (예: 공학도, 교사, 맏이)\n"
            f"5. 감정: 인터뷰에서 직접 드러난 감정 단어만 (추론 금지)\n\n"
            f"규칙:\n"
            f"- 모든 키워드는 단독 명사 1~2개로, 2~6자 이내.\n"
            f"- 형용사+명사 조합(신남 가득한 대학생, 힘든 시절 등) 절대 금지. 명사 하나로만 압축하라.\n"
            f"- 구나 서술어 형태(~결정, ~열심히) 금지.\n"
            f"- 마크다운(**,*,#) 절대 금지.\n"
            f"- 출력 형식: 키워드1,키워드2,...,키워드12 (한국어만, 쉼표 구분, 한 줄)\n\n"
            f"인터뷰:\n{transcript_text[:2500]}"
        )
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=200,
        )
        raw = response.choices[0].message.content.strip()

        # 카테고리 레이블 방식("장소: X, Y\n가치: Z") 대응 — 콜론 뒤 값만 추출
        if ":" in raw and "," not in raw.split("\n")[0]:
            parts = []
            for line in raw.split("\n"):
                after_colon = line.split(":", 1)[-1] if ":" in line else line
                parts.extend(after_colon.split(","))
            raw = ",".join(parts)

        # 공백 허용, 한국어+공백+쉼표만 남김
        raw_clean = re.sub(r"[^가-힣 ,]", "", raw)
        seen = set()
        candidates = []
        for k in raw_clean.split(","):
            k = k.strip()
            korean_len = len(re.sub(r"[^가-힣]", "", k))
            if 2 <= korean_len <= 6 and k not in seen:
                seen.add(k)
                candidates.append(k)
        candidates = candidates[:12]
        if len(candidates) < 3:
            candidates = ["고향", "성실", "도전", "청춘", "인내", "꿈"]
        print(f"[NLP] 키워드 후보 {len(candidates)}개: {candidates}")
        return candidates

    def extract_top_keywords(self, transcript_text: str) -> list:
        """인터뷰 전체에서 핵심 키워드 3개를 추출합니다."""
        prompt = (
            f"다음 인터뷰에서 이 사람의 삶을 가장 잘 대표하는 명사 키워드 3개를 추출하라.\n"
            f"반드시 인터뷰에 실제로 언급된 내용만 사용하라.\n"
            f"출력 형식: 키워드1,키워드2,키워드3 (한국어만, 쉼표 구분)\n\n"
            f"인터뷰:\n{transcript_text[:1500]}"
        )
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
        )
        raw = response.choices[0].message.content.strip()
        raw_clean = re.sub(r"[^가-힣,]", "", raw)
        keywords = [k.strip() for k in raw_clean.split(",") if k.strip() and len(k.strip()) >= 2][:3]
        if not keywords:
            keywords = ["가족", "고향", "청춘"]
        print(f"[NLP] 핵심 키워드 3개: {keywords}")
        return keywords

    def _build_chapter_structure(self, seg_map: dict) -> list:
        """답변 내용 기반으로 챕터 구조를 동적으로 생성. 부실한 섹션은 앞 챕터에 병합."""
        THRESHOLD = 50
        base = self.chapter_structure
        result = []

        for section in base:
            is_anchor = section.get("is_prologue") or section.get("is_epilogue")
            total_chars = sum(len(seg_map.get(qn, "")) for qn in section.get("q_numbers", []))

            if is_anchor or total_chars >= THRESHOLD:
                result.append(dict(section))
            else:
                # 내용 부족 → 에필로그 앞의 챕터에 병합
                if result and not result[-1].get("is_epilogue"):
                    prev = result[-1]
                    result[-1] = {
                        **prev,
                        "q_numbers": prev["q_numbers"] + section.get("q_numbers", []),
                    }
                else:
                    result.append(dict(section))

        return result if len(result) >= 4 else base

    def generate_chapter_titles(self, transcript_text: str, birth_date_str: str,
                                 selected_keywords: list = None,
                                 n: int = None, chapter_structure: list = None,
                                 seg_map: dict = None) -> list:
        chapter_structure = chapter_structure or self.chapter_structure
        n = n or len(chapter_structure)
        seg_map = seg_map or {}

        titles = []
        for i, chapter in enumerate(chapter_structure):
            title = self._generate_single_chapter_title(chapter, seg_map, transcript_text)
            titles.append(title)
            print(f"[NLP] 챕터 {i+1} 제목: {title}")

        return titles[:n]

    def _generate_single_chapter_title(self, chapter: dict, seg_map: dict, transcript_text: str) -> str:
        # 챕터 관련 Q 답변으로 요약문 구성
        chapter_qs = chapter.get("q_numbers", [])
        parts = [seg_map[qn][:250] for qn in chapter_qs if seg_map.get(qn)]
        chapter_summary = "\n".join(parts) if parts else transcript_text[:400]
        guide = chapter.get("guide", "")

        prompt = (
            f"아래 인터뷰 내용을 읽고 챕터 제목을 명사형으로 3개 생성하라.\n"
            f"챕터 주제: {guide}\n\n"
            f"규칙:\n"
            f"- 2~6자, 짧고 함축적. 감정·분위기를 압축한 단어나 짧은 구.\n"
            f"- 좋은 예: 첫 출발 / 긴 기다림 / 귀향 / 빈 의자 / 흉터 / 낯선 봄 / 오래된 약속\n"
            f"- 인터뷰에 나온 특정 사물·음식 이름을 그대로 쓰지 마라\n"
            f"- 연도·나이·시대명·교훈·결론 금지\n\n"
            f"[인터뷰 내용]\n{chapter_summary}\n\n"
            f'JSON만 출력하라: {{"명사형": ["제목1", "제목2", "제목3"]}}'
        )

        try:
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
            )
            parsed = self._parse_json(response.choices[0].message.content.strip())
            candidates = parsed.get("명사형", [])
            if candidates:
                return candidates[0]
        except Exception as e:
            print(f"[NLP] ⚠️  챕터 제목 생성 실패 ({chapter.get('title', '')}): {e}")

        return chapter.get("guide", "이야기")[:10]

    # ──────────────────────────────────────────
    # 4. 자서전 본문 생성
    # ──────────────────────────────────────────

    def generate_autobiography(self, transcript_text, birth_date_str, user_name="저자",
                                region_info: dict = None, selected_keywords: list = None,
                                segments: list = None):
        persona_key   = self.determine_persona(birth_date_str)
        persona_label = config.PERSONA_PROMPTS[persona_key]
        age           = self.calculate_age(birth_date_str)
        birth_year    = birth_date_str.split("-")[0]

        print("[NLP] 키워드 추출 중...")
        keywords = self.extract_keywords(transcript_text, birth_date_str)

        # segments를 Q번호로 인덱싱 (Q1~Q15) - 챕터 구조 결정 전에 먼저 빌드
        seg_map = {}
        if segments:
            for seg in segments:
                m = re.match(r"Q(\d+)", seg.get("question", ""))
                if m:
                    seg_map[int(m.group(1))] = seg.get("answer", "").strip()

        # 나이 기반 챕터 구조 선택 → 답변 밀도로 동적 조정
        self.chapter_structure = self._get_chapter_structure_by_age(age)
        chapter_structure = self._build_chapter_structure(seg_map)
        # 프롤로그 챕터 제외 (짧은 도입부 페이지 불필요)
        chapter_structure = [ch for ch in chapter_structure if not ch.get("is_prologue")]

        print("[NLP] 챕터 제목 생성 중...")
        chapter_titles = self.generate_chapter_titles(
            transcript_text, birth_date_str, selected_keywords=selected_keywords,
            n=len(chapter_structure), chapter_structure=chapter_structure,
            seg_map=seg_map,
        )

        print(f"[NLP] 페르소나: {persona_key} (만 {age}세) → {len(chapter_structure)}개 챕터 생성 중...")

        print("[NLP] 챕터별 에피소드 배정 중...")
        chapter_plan = self._plan_chapters(chapter_structure, seg_map, transcript_text, user_name)

        chapters = []
        written_summaries = []

        for i, chapter in enumerate(chapter_structure):
            title      = chapter_titles[i]
            use_region = chapter.get("region_context", False) and region_info
            use_era    = chapter.get("era_context",   False) and region_info

            chapter_qs = chapter.get("q_numbers", [])

            # 해당 Q 답변만 뽑아서 챕터 전용 텍스트 구성
            # seg_map 없으면 전체 transcript 사용, 있으면 해당 Q만 사용 (없는 내용 창작 방지)
            if seg_map and chapter_qs:
                chapter_text_parts = []
                for qn in chapter_qs:
                    ans = seg_map.get(qn, "")
                    if ans:
                        chapter_text_parts.append("[Q" + str(qn) + " 답변]\n" + ans)
                chapter_transcript = "\n\n".join(chapter_text_parts) if chapter_text_parts else ""
            else:
                chapter_transcript = transcript_text

            # 해당 챕터 답변이 아예 없으면 건너뜀
            if not chapter_transcript.strip():
                print(f"  ⚠️  ({i+1}/{len(chapter_structure)}) {title} - 답변 없음, 건너뜀")
                continue

            content = self._generate_chapter(
                chapter=chapter,
                title=title,
                transcript_text=chapter_transcript,
                keywords=keywords,
                persona_label=persona_label,
                user_name=user_name,
                age=age,
                birth_year=birth_year,
                written_summaries=written_summaries,
                region_info=region_info if (use_region or use_era) else None,
                assigned_episode=chapter_plan.get(i),
            )

            # 마크다운/소제목 제거
            content = re.sub(r"#{1,6}\s*", "", content)
            content = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", content)
            content = re.sub(r"^[-*]\s+", "", content, flags=re.MULTILINE)
            # "추억의 단면:", "소제목:" 패턴 제거
            content = re.sub(r"^.{1,10}:\s*", "", content, flags=re.MULTILINE)
            # 영어 제거
            content = re.sub(r"[A-Za-z]+", "", content)
            # 이상한 문자 제거 (인도어, 데바나가리 등)
            content = re.sub(r"[^\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F\s\d\.,!?~\-\"\'()]", "", content)
            # 특수문자 치환
            content = content.replace("—", "-").replace("–", "-")
            # 말투 정규화
            content = re.sub(r"했었[어다]", "했다", content)
            content = re.sub(r"하곤 했[었]?[어다]?", "했다", content)
            # '○○ 마을' → '○○' (지역명 뒤 마을 제거)
            content = re.sub(r"(\S{2,5})\s*마을", r"\1", content)
            # 이름(종희 등) → 나 (1인칭 자서전)
            name_short = user_name[-2:] if len(user_name) >= 2 else user_name
            content = re.sub(rf"{re.escape(user_name)}(은|는|이|가|을|를|의|에게|에서|도|만|께서|씨)", r"나\1", content)
            content = re.sub(rf"{re.escape(name_short)}(은|는|이|가|을|를|의|에게|에서|도|만|께서)", r"나\1", content)
            # 3인칭 → 1인칭 여성 화자 수정
            content = content.replace("그에게는", "나에게는")
            content = content.replace("그에게", "나에게")
            content = content.replace("그의", "나의")
            content = content.replace("그는", "나는")
            content = content.replace("그가", "내가")
            content = content.replace("그녀는", "나는")
            content = content.replace("그녀가", "내가")
            content = content.replace("그녀의", "나의")
            content = content.replace("그녀에게", "나에게")
            # 빈 줄 제거 (문단 사이 줄바꿈 없애기)
            content = re.sub(r"\n{2,}", "\n", content).strip()
            # 첫 줄 제목 반복 제거
            lines = content.split("\n")
            while lines and (
                title.replace(" ", "") in lines[0].replace(" ", "") or
                len(lines[0].strip()) < 5
            ):
                lines.pop(0)
            content = "\n".join(lines).strip()

            # 명사·장소·인물 등 핵심 소재 추출 (반복 방지용)
            import re as _re
            nouns = _re.findall(r"[가-힣]{2,6}", content)
            noun_freq = {}
            for w in nouns:
                noun_freq[w] = noun_freq.get(w, 0) + 1
            top_nouns = [w for w, _ in sorted(noun_freq.items(), key=lambda x: -x[1])[:20]]
            written_summaries.append(
                f"[{title}] 주요 소재: {', '.join(top_nouns)}\n요약: {content[:300]}..."
            )
            # 전체 챕터 요약 유지 (흐름/중복 방지용)
            chapters.append({"title": title, "content": content})
            print(f"  ✓ ({i+1}/{len(chapter_structure)}) {title}")

        # 표지 제목 생성 (선택된 키워드 활용)
        cover_title = self._generate_cover_title(
            transcript_text, keywords, user_name, birth_year,
            selected_keywords=selected_keywords
        )

        return {
            "persona":     persona_key,
            "age":         age,
            "birth_year":  birth_year,
            "user_name":   user_name,
            "region":      region_info.get("region", "") if region_info else "",
            "keywords":    keywords,
            "chapters":    chapters,
            "cover_title": cover_title,
            "created_at":  datetime.now().isoformat(),
        }


    def _generate_cover_title(self, transcript_text, keywords, user_name, birth_year,
                               selected_keywords=None) -> str:
        """선택된 키워드로 자서전 표지 제목을 생성합니다."""
        # 선택된 키워드 우선, 없으면 자동 추출
        if selected_keywords:
            kw_str = ", ".join(selected_keywords[:3])
        else:
            kw = keywords.get("places", []) + keywords.get("events", []) + keywords.get("emotions", [])
            kw_str = ", ".join(kw[:3]) if kw else ""

        if selected_keywords:
            prompt = (
                f"아래 키워드를 바탕으로 독창적인 자서전 제목을 지어라.\n\n"
                f"【참고 키워드】: {kw_str}\n\n"
                f"규칙:\n"
                f"1. 키워드의 정서·분위기를 살리되, 키워드를 그대로 복사하지 마라. 은유·변용 권장.\n"
                f"2. 4~10자, 한국어만.\n"
                f"3. '삶', '여정', '이야기', '발자취', '기억', '추억' 단독 사용 금지.\n"
                f"4. 범용적 관용구나 예시 문구 사용 금지. 이 사람만의 제목이어야 한다.\n"
                f"5. 제목 하나만 출력."
            )
        else:
            prompt = (
                f"다음 인터뷰를 읽고 자서전 제목을 지어라.\n\n"
                f"인터뷰: {transcript_text[:600]}\n"
                f"핵심 소재: {kw_str}\n\n"
                f"규칙:\n"
                f"1. 인터뷰에 실제로 나온 단어(장소명, 사물, 사건)를 바탕으로 은유적·시적으로 표현하라.\n"
                f"2. 4~10자, 한국어만.\n"
                f"3. '삶', '여정', '이야기', '발자취', '기억', '추억' 단독 사용 금지.\n"
                f"4. 범용적 관용구나 예시 문구 사용 금지. 이 사람만의 제목이어야 한다.\n"
                f"5. 제목 하나만 출력."
            )
        try:
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=40,
            )
            title = response.choices[0].message.content.strip()
            title = re.sub(r"\*+", "", title)  # ** 마크다운 제거
            title = title.replace("'", "").replace('"', "").replace(".", "").replace("。", "").strip()
            title = re.sub(r"[A-Za-z]", "", title).strip()
            if len(title) >= 4:
                print(f"[NLP] 표지 제목: {title}")
                return title
        except Exception as e:
            print(f"[NLP] ⚠️  표지 제목 생성 실패: {e}")
        return f"{user_name}의 이야기"

    def _plan_chapters(self, chapter_structure: list, seg_map: dict,
                       transcript_text: str, user_name: str) -> dict:
        """챕터별 독점 에피소드를 미리 배정 — 반복 방지의 핵심"""
        chapters_desc = []
        for i, ch in enumerate(chapter_structure):
            qs = ch.get("q_numbers", [])
            answers = " / ".join(seg_map[q][:150] for q in qs if seg_map.get(q))
            label = "프롤로그" if ch.get("is_prologue") else ("에필로그" if ch.get("is_epilogue") else f"챕터{i+1}")
            chapters_desc.append(f"{label} (주제: {ch['guide'][:60]})\n  관련 답변: {answers or '없음'}")

        prompt = (
            f"저자: {user_name}\n\n"
            f"아래는 자서전 챕터 목록과 각 챕터에 배정된 인터뷰 답변이다.\n"
            f"각 챕터가 다룰 '핵심 에피소드'를 한 줄씩 배정하라.\n\n"
            f"규칙:\n"
            f"- 같은 사건·인물·장소를 두 챕터에 중복 배정 금지\n"
            f"- 답변에 실제로 나온 내용만 사용\n"
            f"- 에피소드는 구체적 장면·순간으로 (예: '처음 일터에 나간 날 버스 안에서의 긴장')\n\n"
            f"챕터 목록:\n" + "\n".join(chapters_desc) + "\n\n"
            f"아래 JSON 형식으로만 출력하라:\n"
            f'{{"plan": [{{"index": 0, "episode": "에피소드 설명"}}, ...]}}'
        )
        try:
            resp = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
            )
            data = self._parse_json(resp.choices[0].message.content.strip())
            return {item["index"]: item["episode"] for item in data.get("plan", [])}
        except Exception as e:
            print(f"[NLP] ⚠️  콘텐츠 플랜 생성 실패 ({e}) → 플랜 없이 진행")
            return {}

    def _generate_chapter(self, chapter, title, transcript_text, keywords,
                           persona_label, user_name, age, birth_year,
                           written_summaries=None, region_info=None,
                           assigned_episode: str = None):

        if chapter.get("is_prologue"):
            prologue_system = (
                f"{persona_label}\n"
                "자서전의 짧은 도입부를 쓴다.\n\n"
                "【반드시 지킬 것】\n"
                "- 저자의 이름, 출생년도, 살아온 시대의 분위기만 따뜻하게 소개한다.\n"
                "- '프롤로그' 단어를 본문에 절대 쓰지 마라.\n\n"
                "【절대 금지】\n"
                "- 구체적 사건·에피소드 언급 금지 (뒤 챕터에서 다룬다)\n"
                "- 학교명·직업·특정 장소·인물·대화 언급 금지\n"
                "- 마크다운(#,*,**) 금지. 서술체(-다, -었다)로만.\n"
                "- 1인칭('나')으로만.\n\n"
                "300자 내외, 간결하게 마무리."
            )
            prologue_user = (
                f"저자: {user_name} ({birth_year}년생, 만 {age}세)\n\n"
                "이 인물의 자서전 첫 페이지를 써라. "
                "이름, 출생년도, 시대 배경만 담아라. 구체적인 경험은 절대 쓰지 마라."
            )
            return self._generate(prologue_system, prologue_user, max_tokens=500)

        birth_int  = int(birth_year) if birth_year.isdigit() else 1952
        war_note   = (
            f"저자는 {birth_int}년생이다. "
            f"한국전쟁(1950-1953)은 저자가 유아기(1~3세)에 끝났다. "
            f"청소년기는 {birth_int+10}~{birth_int+18}년대, 청년기는 {birth_int+19}~{birth_int+30}년대다. "
            f"청년기에 전쟁을 경험했다는 서술은 역사적 오류다. 절대 쓰지 마라."
        )

        prev_context = ""
        if written_summaries:
            prev_context = (
                "\n\n【이전 챕터 요약 — 아래 소재·사건·표현은 이 챕터에서 절대 재사용 금지】\n"
                + "\n".join(written_summaries)
                + "\n\n→ 이 챕터는 위 챕터들과 완전히 다른 소재·감정·장면으로만 채워야 한다. "
                "같은 사건을 다른 각도로 쓰는 것도 금지. 앞 챕터에서 한 번이라도 언급된 것은 쓰지 마라."
            )

        region_context = ""
        if region_info:
            region_context = (
                "\n\n[지역/시대 배경 참고]\n"
                f"지역: {region_info.get('region_history', '')[:150]}\n"
                f"시대: {region_info.get('era_background', '')[:150]}\n"
                f"문화: {region_info.get('local_culture', '')[:100]}"
            )

        episode_instruction = ""
        if assigned_episode:
            episode_instruction = (
                f"\n\n【이 챕터의 독점 에피소드】\n"
                f"이 챕터는 오직 다음 한 가지 장면·순간에만 집중하라: {assigned_episode}\n"
                f"다른 챕터들은 각자의 에피소드가 있으므로, 이 챕터에서 그것들을 언급하지 마라."
            )

        system_prompt = (
            f"{persona_label}\n"
            "당신은 한국 문학상을 받은 산문 작가입니다. "
            "인터뷰 내용을 바탕으로 독자의 마음을 움직이는 자서전 한 챕터를 씁니다.\n\n"
            "【절대 규칙】\n"
            "1. 인터뷰 답변에 명시된 사실만 써라. 언급되지 않은 직업·장소·사건·인물·감정을 절대 창작하지 마라.\n"
            "2. 인터뷰에 없는 내용을 추론하거나 상상으로 채우지 마라. 모르면 쓰지 마라.\n"
            "3. 순수 한국어만. 영어·한자·외국어 절대 금지.\n"
            "4. 서술체(-다, -었다, -이었다)로만. 존댓말(-습니다)/번역투 금지.\n"
            "5. 챕터 제목·소제목을 본문에 절대 쓰지 마라. 마크다운(#,*,**) 금지.\n"
            "6. 이전 챕터에 나온 소재·사건·문장은 단 하나도 반복 금지. 비슷한 표현도 금지.\n"
            f"7. {war_note}\n"
            "8. 반드시 1인칭('나')으로만 서술. 저자 이름이나 '그', '그녀' 절대 금지.\n"
            "9. 2500자 이상 완성된 문장으로 마무리.\n"
            "10. 문단 구조: 하나의 문단은 반드시 3문장 이상으로 구성하라. 문장 하나만 달랑 쓰고 줄바꿈하는 것 절대 금지. 문단 안에서는 줄바꿈 없이 이어 써라.\n"
            f"{prev_context}"
            f"{episode_instruction}\n\n"
            "【작가의 문장으로 쓰는 법】\n"
            "- 첫 문장 다양성: 아래 중 이 챕터에 가장 어울리는 방식 하나를 골라 시작하라.\n"
            "  (A) 감각 묘사로 시작: '버스 유리창에 이마를 기댔을 때, 차창 밖으로 논이 펼쳐졌다.'\n"
            "  (B) 독자에게 말 걸기: '그 기억은 항상 냄새로 먼저 온다.'\n"
            "  (C) 역설·아이러니: '가장 잘 알아야 할 사람이 나인데, 그 밤 나는 나를 몰랐다.'\n"
            "  (D) 대화·소리로 시작: '합격이요. 그 두 글자가 전화기 너머로 들어왔다.'\n"
            "  (E) 현재 시점에서 회상: '지금도 그 골목을 지나면 자연스럽게 발이 느려진다.'\n"
            "  금지: 매 챕터 같은 방식(단문 + ~했다.) 반복 금지. 이전 챕터 오프닝 스타일과 달라야 한다.\n"
            "- 사건을 나열하지 말고, 그 순간에 머물러라. 독자가 숨을 참게 만드는 장면 하나가 열 문장보다 낫다.\n"
            "- 감정은 직접 말하지 말고 행동과 감각으로 보여라. ('슬펐다' 대신 '그날 밥을 먹지 못했다')\n"
            "- 감정의 두 층위를 담아라: 그 당시 느꼈던 감정과, 지금 돌아봤을 때 느끼는 감정은 다르다. 두 시점을 자연스럽게 교차하라.\n"
            "- 문장 리듬을 살려라. 짧은 문장과 긴 문장을 섞어 호흡을 만들어라.\n"
            "- 마지막 문단: 이 경험이 나만의 이야기가 아니라 누구나 한 번쯤 겪는 순간임을 암시하며, 여운이 남는 한 문장으로 닫아라."
        )

        transcript_trimmed = transcript_text[:1500] + ("...(이하 생략)" if len(transcript_text) > 1500 else "")

        user_prompt = (
            f"저자: {user_name} ({birth_year}년생, 만 {age}세)\n"
            f"챕터 제목: {title}\n\n"
            f"작성 가이드: {chapter['guide']}\n\n"
            f"【아래 인터뷰 답변만 사용하라. 여기에 없는 내용은 절대 쓰지 마라】\n"
            f"\"\"\"\n{transcript_trimmed}\n\"\"\""
            f"{region_context}\n\n"
            f"위 답변을 바탕으로 '{title}' 챕터를 2500자 내외로 작성하라. "
            f"첫 문장은 구체적인 장면·순간으로 시작하고, 독자가 이 사람의 삶 속으로 들어올 수 있게 써라. "
            f"감정 표현은 답변에서 드러난 것만 살려라."
        )

        return self._generate(system_prompt, user_prompt, max_tokens=config.LLM_MAX_TOKENS)

    # ──────────────────────────────────────────
    # 5. 결과 저장
    # ──────────────────────────────────────────

    def save_summary(self, autobiography: dict, user_id: str) -> str:
        filename = f"{user_id}_summary.json"
        path = os.path.join(config.SUMMARY_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(autobiography, f, ensure_ascii=False, indent=2)
        print(f"[NLP] 저장 완료: {path}")
        return path
