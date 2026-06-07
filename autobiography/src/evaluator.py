"""
src/evaluator.py
자서전 품질 자동 평가 모듈

평가 체계 (총 100점):
  [정량 자동 10점]
    - 한국어 순도        5점
    - 챕터 다양성        5점

  [LLM 정성 90점]
    - 원자료 충실        15점  — 인터뷰 내용이 자서전에 충실히 반영됐는가
    - 할루시네이션 위험도 15점  — 없는 내용이 사실처럼 삽입됐는가
    - 감정 표현 적합성   10점  — 감정·경험이 적절하게 표현됐는가
    - 화자 고유성        15점  — 이 사람만의 이야기인가
    - 챕터 구성과 연결성 15점  — 챕터 간 흐름이 자연스러운가
    - 문장 자연스러움    10점  — 글이 자연스럽게 읽히는가
    - 제목·목차 전달력   10점  — 제목과 목차가 자서전을 잘 전달하는가
"""

import os
import sys
import re
import json
import time

from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config

client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)


class AutobiographyEvaluator:

    def evaluate(self, chapters: list[dict], interview_text: str,
                 cover_title: str = "", toc_titles: list[str] = None) -> dict:
        """
        Args:
            chapters:       [{"title": str, "content": str}, ...]
            interview_text: 원본 인터뷰 전체 텍스트
            cover_title:    자서전 표지 제목
            toc_titles:     목차 제목 리스트 (없으면 chapters에서 추출)

        Returns:
            종합 점수, 항목별 점수, 총평 포함 dict
        """
        print("[평가] 자서전 품질 평가 시작...")

        toc   = toc_titles or [ch["title"] for ch in chapters]
        title = cover_title or (chapters[0]["title"] if chapters else "")

        # ── 정량 자동 (10점) ──
        auto_korean    = self._korean_purity([c["content"] for c in chapters])
        auto_diversity = self._chapter_diversity([c["content"] for c in chapters])
        score_korean    = round(auto_korean    * 5, 2)
        score_diversity = round(auto_diversity * 5, 2)

        # ── LLM 정성 (90점) ──
        llm = self._llm_evaluate(chapters, interview_text, title, toc)

        overall = round(
            score_korean + score_diversity
            + llm["fidelity_score"]
            + llm["hallucination_score"]
            + llm["emotion_score"]
            + llm["uniqueness_score"]
            + llm["structure_score"]
            + llm["fluency_score"]
            + llm["presentation_score"],
            1
        )

        result = {
            "overall": overall,
            "breakdown": {
                "한국어순도":    {"score": score_korean,               "max": 5,  "note": f"{auto_korean:.1%}"},
                "챕터다양성":    {"score": score_diversity,            "max": 5,  "note": ""},
                "원자료충실":    {"score": llm["fidelity_score"],      "max": 15, "note": llm["fidelity_note"]},
                "할루시네이션":  {"score": llm["hallucination_score"], "max": 15, "note": llm["hallucination_note"]},
                "감정표현적합성": {"score": llm["emotion_score"],       "max": 10, "note": llm["emotion_note"]},
                "화자고유성":    {"score": llm["uniqueness_score"],    "max": 15, "note": llm["uniqueness_note"]},
                "챕터구성연결성": {"score": llm["structure_score"],    "max": 15, "note": llm["structure_note"]},
                "문장자연스러움": {"score": llm["fluency_score"],      "max": 10, "note": llm["fluency_note"]},
                "제목목차전달력": {"score": llm["presentation_score"], "max": 10, "note": llm["presentation_note"]},
            },
            "overall_comment":   llm["overall_comment"],
            "improvement_tips":  llm.get("improvement_tips", []),
        }

        print(f"[평가] 완료: 종합 {overall:.1f}/100점")
        return result

    # ── 정량: 한국어 순도 ─────────────────────────────────────────────────────

    def _korean_purity(self, contents: list[str]) -> float:
        full = " ".join(contents)
        if not full.strip():
            return 0.0
        korean    = len(re.findall(r"[가-힣]", full))
        non_space = len(re.sub(r"\s", "", full))
        return korean / max(1, non_space)

    # ── 정량: 챕터 다양성 ─────────────────────────────────────────────────────

    def _chapter_diversity(self, contents: list[str]) -> float:
        if len(contents) < 2:
            return 1.0

        def ngrams(text: str, n: int = 3) -> set:
            cleaned = re.sub(r"\s+", "", text)
            return {cleaned[i:i+n] for i in range(len(cleaned) - n + 1)}

        similarities = []
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                a = ngrams(contents[i])
                b = ngrams(contents[j])
                if not a or not b:
                    continue
                similarities.append(len(a & b) / len(a | b))

        avg = sum(similarities) / len(similarities) if similarities else 0
        return round(1 - avg, 3)

    # ── LLM 정성 평가 ─────────────────────────────────────────────────────────

    def _llm_evaluate(self, chapters: list[dict], interview_text: str,
                      cover_title: str, toc: list[str]) -> dict:
        """7개 정성 기준을 LLM 1회 호출로 평가한다."""
        interview_excerpt = interview_text[:2500]
        toc_str = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(toc))

        idxs = [0]
        if len(chapters) > 2:
            idxs.append(len(chapters) // 2)
        idxs.append(len(chapters) - 1)
        sample = "\n\n".join(
            f"[{chapters[i]['title']}]\n{chapters[i]['content'][:600]}..."
            for i in idxs
        )

        prompt = f"""당신은 자서전 전문 편집자입니다. 아래 자서전을 7가지 기준으로 평가하십시오.

━━━━━━━━ 자서전 정보 ━━━━━━━━
표지 제목: {cover_title}

목차:
{toc_str}

본문 발췌 (1장 · 중간 · 마지막):
{sample}

━━━━━━━━ 원본 인터뷰 ━━━━━━━━
{interview_excerpt}

━━━━━━━━ 평가 기준 ━━━━━━━━

1. 원자료 충실 (0~15점)
   인터뷰에서 말한 사건·인물·장소·감정이 자서전에 충실하게 반영됐는가?
   중요한 이야기가 빠졌거나 축소됐다면 감점.

2. 할루시네이션 위험도 (0~15점)
   인터뷰에 없는 내용이 사실처럼 삽입됐는가?
   없는 내용이 많을수록 낮은 점수. 인터뷰 내용만으로 채워졌다면 만점.

3. 감정 표현 적합성 (0~10점)
   인터뷰에서 드러난 감정·경험이 자서전에서 적절하게 표현됐는가?
   감정을 직접 선언하지 않고 장면·행동으로 보여주면 높은 점수.

4. 화자 고유성 (0~15점)
   이 사람만의 구체적 이야기인가, 아니면 누구에게나 해당될 법한 범용 서술인가?
   고유한 장소명·인물명·사건이 살아있으면 높은 점수.

5. 챕터 구성과 연결성 (0~15점)
   챕터 간 흐름이 자연스럽게 이어지는가?
   각 챕터가 독립적으로 따로 놀지 않고 하나의 이야기로 연결되는가?

6. 문장 자연스러움 (0~10점)
   글이 자연스럽게 읽히는가?
   번역투·어색한 표현·문단 구조 문제가 있으면 감점.

7. 제목·목차 전달력 (0~10점)
   표지 제목과 목차 챕터 제목들이 이 자서전의 내용과 분위기를 잘 전달하는가?
   명사형 나열이 아닌 서사적·시적 문장이면 높은 점수.

━━━━━━━━ 출력 형식 ━━━━━━━━
JSON만 출력하라. 마크다운·설명문 금지.
{{
  "fidelity_score": 0~15,
  "fidelity_note": "원자료 충실도에 대한 한 줄 평",
  "hallucination_score": 0~15,
  "hallucination_note": "할루시네이션에 대한 한 줄 평",
  "emotion_score": 0~10,
  "emotion_note": "감정 표현에 대한 한 줄 평",
  "uniqueness_score": 0~15,
  "uniqueness_note": "화자 고유성에 대한 한 줄 평",
  "structure_score": 0~15,
  "structure_note": "챕터 구성과 연결성에 대한 한 줄 평",
  "fluency_score": 0~10,
  "fluency_note": "문장 자연스러움에 대한 한 줄 평",
  "presentation_score": 0~10,
  "presentation_note": "제목·목차 전달력에 대한 한 줄 평",
  "overall_comment": "편집자 총평 (3문장 이내)",
  "improvement_tips": ["개선점1", "개선점2", "개선점3"]
}}"""

        defaults = {
            "fidelity_score": 8,      "fidelity_note": "(평가 실패)",
            "hallucination_score": 8, "hallucination_note": "(평가 실패)",
            "emotion_score": 5,       "emotion_note": "(평가 실패)",
            "uniqueness_score": 8,    "uniqueness_note": "(평가 실패)",
            "structure_score": 8,     "structure_note": "(평가 실패)",
            "fluency_score": 5,       "fluency_note": "(평가 실패)",
            "presentation_score": 5,  "presentation_note": "(평가 실패)",
            "overall_comment": "(평가 실패)",
            "improvement_tips": [],
        }

        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=config.EVAL_LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                    timeout=120,
                )
                raw = resp.choices[0].message.content.strip()
                raw = re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()
                start = raw.find("{")
                end   = raw.rfind("}") + 1
                if start != -1 and end > start:
                    raw = raw[start:end]
                data = json.loads(raw)

                result = {**defaults, **data}
                for key in ["fidelity_score", "hallucination_score", "emotion_score",
                            "uniqueness_score", "structure_score", "fluency_score", "presentation_score"]:
                    result[key] = float(result[key])

                print(f"  원자료충실 {result['fidelity_score']}/15  할루시네이션 {result['hallucination_score']}/15  감정표현 {result['emotion_score']}/10")
                print(f"  화자고유성 {result['uniqueness_score']}/15  챕터구성 {result['structure_score']}/15  문장자연 {result['fluency_score']}/10  제목목차 {result['presentation_score']}/10")
                return result

            except Exception as e:
                print(f"  ⚠️  평가 시도 {attempt+1}/3 실패: {e}")
                if attempt < 2:
                    time.sleep(5)

        return defaults
