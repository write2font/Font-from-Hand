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
        """
        Args:
            extended: True면 15챕터 확장 구조 사용 (80페이지용)
        """
        self.thresholds = config.AGE_THRESHOLDS
        self.chapter_structure = (
            config.CHAPTER_STRUCTURE_EXTENDED if extended
            else config.CHAPTER_STRUCTURE
        )
        os.makedirs(config.SUMMARY_DIR, exist_ok=True)

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
        """키워드 후보 12개를 추출해서 사용자 선택용으로 반환합니다."""
        prompt = (
            f"다음 인터뷰에서 이 사람의 삶을 대표하는 명사 키워드 12개를 추출하라.\n"
            f"장소, 인물, 사물, 사건, 감정, 활동 등을 포함하라.\n"
            f"반드시 인터뷰에 실제로 언급된 내용만 사용하라. 없는 내용을 만들지 마라.\n"
            f"출력 형식: 키워드1,키워드2,...,키워드12 (한국어만, 쉼표 구분, 중복 없음)\n\n"
            f"인터뷰:\n{transcript_text[:2000]}"
        )
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()
        raw_clean = re.sub(r"[^가-힣,]", "", raw)
        seen = set()
        candidates = []
        for k in raw_clean.split(","):
            k = k.strip()
            if len(k) >= 2 and k not in seen:
                seen.add(k)
                candidates.append(k)
        candidates = candidates[:12]
        if len(candidates) < 3:
            candidates = ["가족", "고향", "청춘", "추억", "성실", "꿈"]
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
        THRESHOLD = 50  # 섹션 내 총 답변 길이 기준 (chars)
        base = config.CHAPTER_STRUCTURE
        result = []

        for section in base:
            is_anchor = section["title"] in ("프롤로그", "에필로그")
            total_chars = sum(len(seg_map.get(qn, "")) for qn in section.get("q_numbers", []))

            if is_anchor or total_chars >= THRESHOLD:
                result.append(dict(section))
            else:
                # 내용 부족 → 에필로그 앞의 챕터에 병합
                if result and result[-1]["title"] != "에필로그":
                    prev = result[-1]
                    result[-1] = {
                        **prev,
                        "q_numbers": prev["q_numbers"] + section.get("q_numbers", []),
                        "questions": prev["questions"] + section.get("questions", []),
                    }
                else:
                    result.append(dict(section))

        return result if len(result) >= 4 else base

    def generate_chapter_titles(self, transcript_text: str, birth_date_str: str,
                                 selected_keywords: list = None,
                                 n: int = None, chapter_structure: list = None) -> list:
        birth_year = birth_date_str.split("-")[0]
        chapter_structure = chapter_structure or self.chapter_structure
        n = n or len(chapter_structure)

        # 핵심 키워드 3개 (사용자 선택 or 자동 추출)
        top_keywords = selected_keywords if selected_keywords else self.extract_top_keywords(transcript_text)
        top_keywords = top_keywords[:3]
        keywords_str = ", ".join(top_keywords)

        # 챕터별 핵심 내용 한 줄 요약
        chapter_guides = [c.get("guide", "")[:30] for c in chapter_structure]
        guides_str = "\n".join([f"{i+1}번 챕터: {g}" for i, g in enumerate(chapter_guides)])

        prompt = (
            f"자서전 챕터 제목 {n}개를 만들어라.\n\n"
            f"저자 핵심 소재: {keywords_str}\n"
            f"인터뷰: {transcript_text[:400]}\n\n"
            f"각 챕터 내용:\n{guides_str}\n\n"
            f"좋은 제목 예시 (이런 스타일로):\n"
            f"- 냇가에서 / 달리던 소녀 / 화롯불 곁에서 / 도둑맞은 봄\n"
            f"- 어머니의 손 / 흙냄새 나는 꿈 / 불씨 하나 / 두 손으로\n"
            f"- 소가 없던 겨울 / 달려라 달려 / 그래도 봄이 왔다\n\n"
            f"나쁜 제목 예시 (이런 스타일 금지):\n"
            f"- 성실의 뿌리 / 가정의 강물 / 진실된 성공의 길 (추상적이고 뻔함)\n"
            f"- 챕터1 / 프롤로그 / 에필로그 (번호/접두어 금지)\n\n"
            f"규칙: 순수 한글만, 2~10자, 구체적 명사나 동사 포함, 한 줄에 하나, 정확히 {n}줄."
        )

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
        )
        raw = response.choices[0].message.content.strip()
        print(f"[NLP] 챕터 제목 응답: {repr(raw[:200])}")

        titles = [line.strip() for line in raw.split("\n") if line.strip()]
        cleaned = []
        for t in titles:
            t = re.sub(r"\*+", "", t)                          # ** 제거
            t = re.sub(r"^[\d\.\-\*\s\|=]+", "", t).strip()
            t = re.sub(r"^(챕터\s*\d+|프롤로그|에필로그)\s*[:\s]\s*", "", t).strip()
            if ":" in t and len(t.split(":")[0]) <= 5:
                t = t.split(":", 1)[1].strip()
            t = t.strip("* \"'")
            korean_chars = len(re.findall(r"[가-힣]", t))
            total_chars  = len(t.replace(" ", ""))
            if t and total_chars > 0 and korean_chars / total_chars >= 0.5:
                cleaned.append(t)

        print(f"[NLP] 파싱된 제목 ({len(cleaned)}개): {cleaned}")

        defaults = [c["title"] for c in chapter_structure]
        while len(cleaned) < n:
            cleaned.append(defaults[len(cleaned)])
        return cleaned[:n]

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

        # 답변 밀도 기반으로 챕터 구조 동적 생성
        chapter_structure = self._build_chapter_structure(seg_map)

        print("[NLP] 챕터 제목 생성 중...")
        chapter_titles = self.generate_chapter_titles(
            transcript_text, birth_date_str, selected_keywords=selected_keywords,
            n=len(chapter_structure), chapter_structure=chapter_structure,
        )

        print(f"[NLP] 페르소나: {persona_key} (만 {age}세) → {len(chapter_structure)}개 챕터 생성 중...")

        chapters = []
        written_summaries = []

        for i, chapter in enumerate(chapter_structure):
            title      = chapter_titles[i]
            use_region = chapter.get("region_context", False) and region_info
            use_era    = chapter.get("era_context",   False) and region_info

            # 이 챕터에 해당하는 Q 번호 (q_numbers 우선, 없으면 questions 파싱)
            chapter_qs = chapter.get("q_numbers", [])
            if not chapter_qs:
                for q_str in chapter.get("questions", []):
                    m = re.match(r"Q(\d+)", q_str.strip())
                    if m:
                        chapter_qs.append(int(m.group(1)))

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

            written_summaries.append(f"[{title}]: {content[:300]}...")
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

        prompt = (
            f"다음 인터뷰를 읽고 자서전 제목을 지어라.\n"
            f"인터뷰: {transcript_text[:600]}\n"
            f"이 사람의 삶을 대표하는 핵심 소재: {kw_str}\n\n"
            f"좋은 제목 예시 (감정/행동/장소가 결합된 구체적 문장형):\n"
            f"- 달리고 또 달렸다\n"
            f"- 냇가에서 보낸 여름\n"
            f"- 성실하게, 끝까지\n"
            f"- 화롯불 곁의 겨울\n"
            f"- 두 손으로 쌓아 올린 집\n\n"
            f"나쁜 제목 (금지):\n"
            f"- 키워드 나열 (달리기, 성실함, 주택)\n"
            f"- 추상적 (삶의 여정, 인생의 발자취)\n\n"
            f"규칙: 한국어만, 5~15자, 위 예시 스타일로. 제목 하나만 출력."
        )
        try:
            response = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=40,
            )
            title = response.choices[0].message.content.strip()
            title = title.replace("'", "").replace('"', "").replace(".", "").replace("。", "").strip()
            title = re.sub(r"[A-Za-z]", "", title).strip()
            if len(title) >= 4:
                print(f"[NLP] 표지 제목: {title}")
                return title
        except Exception as e:
            print(f"[NLP] ⚠️  표지 제목 생성 실패: {e}")
        return f"{user_name}의 이야기"

    def _generate_chapter(self, chapter, title, transcript_text, keywords,
                           persona_label, user_name, age, birth_year,
                           written_summaries=None, region_info=None):

        questions_str = "\n".join(chapter["questions"])

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
                "\n\n【이미 작성된 챕터 요약 - 아래에 나온 사건/표현/소재는 이 챕터에서 단 한 줄도 반복 금지】\n"
                + "\n".join(written_summaries)
                + "\n\n→ 위 챕터들과 완전히 다른 소재와 감정으로 채워라. 같은 사건을 다른 각도로 쓰는 것도 금지."
            )

        region_context = ""
        if region_info:
            region_context = (
                "\n\n[지역/시대 배경 참고]\n"
                f"지역: {region_info.get('region_history', '')[:150]}\n"
                f"시대: {region_info.get('era_background', '')[:150]}\n"
                f"문화: {region_info.get('local_culture', '')[:100]}"
            )

        system_prompt = (
            f"{persona_label}\n"
            "【절대 규칙 - 위반 시 전체 실패】\n"
            "1. 인터뷰 답변에 명시된 사실만 써라. 언급되지 않은 직업·장소·사건·인물·감정을 절대 창작하지 마라.\n"
            "2. 인터뷰에 없는 내용을 추론하거나 상상으로 채우지 마라. 모르면 쓰지 마라.\n"
            "3. 순수 한국어만. 영어·한자·외국어 절대 금지.\n"
            "4. 서술체(-다, -었다, -이었다)로만. 존댓말(-습니다)/번역투 금지.\n"
            "5. 챕터 제목·소제목을 본문에 절대 쓰지 마라. 마크다운(#,*,**) 금지.\n"
            "6. 이전 챕터에 나온 사건·문장 반복 절대 금지.\n"
            f"7. {war_note}\n"
            "8. 반드시 1인칭('나')으로만 서술. 저자 이름이나 '그', '그녀' 절대 금지.\n"
            "9. 1200자 이상 완성된 문장으로 마무리."
        )

        transcript_trimmed = transcript_text[:1500] + ("...(이하 생략)" if len(transcript_text) > 1500 else "")

        user_prompt = (
            f"저자: {user_name} ({birth_year}년생, 만 {age}세)\n"
            f"챕터 제목: {title}\n\n"
            f"이 챕터에서 다룰 질문:\n{questions_str}\n\n"
            f"작성 가이드: {chapter['guide']}\n\n"
            f"【아래 인터뷰 답변만 사용하라. 여기에 없는 내용은 절대 쓰지 마라】\n"
            f"\"\"\"\n{transcript_trimmed}\n\"\"\""
            f"{region_context}"
            f"{prev_context}\n\n"
            f"위 답변에 있는 사실만으로 '{title}' 챕터를 1500자 내외로 작성하라. "
            f"답변의 내용을 1인칭 서술체로 풀어쓰고, 감정 표현은 답변에서 드러난 것만 살려라."
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
