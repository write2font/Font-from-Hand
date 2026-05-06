"""
src/evaluator.py
자서전 품질 자동 평가 모듈

지표:
  1. 한국어 순도        - 비한국어 문자 비율
  2. 챕터 중복도        - 챕터 간 평균 유사도 (낮을수록 좋음)
  3. 사실 근거율        - 인터뷰 내용 기반 서술 비율 (LLM 판단)
  4. 할루시네이션 점수  - 인터뷰에 없는 내용이 포함된 정도 (LLM 판단)
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

    def evaluate(self, chapters: list[dict], interview_text: str) -> dict:
        """
        Args:
            chapters: [{"title": str, "content": str}, ...]
            interview_text: 원본 인터뷰 전체 텍스트

        Returns:
            {
                "korean_purity":      float,  # 0~1, 높을수록 좋음
                "chapter_diversity":  float,  # 0~1, 높을수록 좋음
                "factual_grounding":  float,  # 0~5, 높을수록 좋음
                "hallucination_score": float, # 0~5, 낮을수록 좋음
                "overall":            float,  # 0~100 종합 점수
                "chapter_details":    list,
            }
        """
        print("[평가] 자서전 품질 평가 시작...")

        korean_purity     = self._korean_purity([c["content"] for c in chapters])
        chapter_diversity = self._chapter_diversity([c["content"] for c in chapters])
        llm_scores        = self._llm_evaluate(chapters, interview_text)

        factual_grounding  = llm_scores["factual_grounding"]
        hallucination_score = llm_scores["hallucination_score"]

        # 종합 점수 (0~100)
        # 한국어 순도 20점 + 챕터 다양성 20점 + 사실 근거율 30점 + 할루시네이션 역점수 30점
        overall = (
            korean_purity     * 20 +
            chapter_diversity * 20 +
            (factual_grounding  / 5) * 30 +
            ((5 - hallucination_score) / 5) * 30
        )

        result = {
            "korean_purity":       round(korean_purity,      3),
            "chapter_diversity":   round(chapter_diversity,  3),
            "factual_grounding":   round(factual_grounding,  2),
            "hallucination_score": round(hallucination_score, 2),
            "overall":             round(overall,             1),
            "chapter_details":     llm_scores["chapter_details"],
        }

        print(f"[평가] 완료: 종합 {overall:.1f}점")
        return result

    # ── 1. 한국어 순도 ────────────────────────────────────────────────────────────

    def _korean_purity(self, contents: list[str]) -> float:
        full = " ".join(contents)
        if not full.strip():
            return 0.0
        korean   = len(re.findall(r"[가-힣]", full))
        non_space = len(re.sub(r"\s", "", full))
        return korean / max(1, non_space)

    # ── 2. 챕터 다양성 (중복도 역수) ──────────────────────────────────────────────

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
                jaccard = len(a & b) / len(a | b)
                similarities.append(jaccard)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        return round(1 - avg_similarity, 3)

    # ── 3. LLM 기반 사실 근거율 + 할루시네이션 ───────────────────────────────────

    def _llm_evaluate(self, chapters: list[dict], interview_text: str) -> dict:
        interview_excerpt = interview_text[:2000]
        chapter_details = []

        factual_scores       = []
        hallucination_scores = []

        for ch in chapters:
            prompt = (
                f"아래 [인터뷰]를 보고, [자서전 챕터]를 두 가지 기준으로 평가하라.\n\n"
                f"[인터뷰]\n\"\"\"\n{interview_excerpt}\n\"\"\"\n\n"
                f"[자서전 챕터: {ch['title']}]\n\"\"\"\n{ch['content'][:800]}\n\"\"\"\n\n"
                f"평가 기준:\n"
                f"1. 사실 근거율: 챕터 내용이 인터뷰에 근거한 정도 (1=거의 없음, 5=대부분 근거 있음)\n"
                f"2. 할루시네이션: 인터뷰에 없는 내용이 포함된 정도 (1=없음, 5=심각)\n\n"
                f"반드시 아래 JSON 형식으로만 출력하라:\n"
                f"{{\"factual\": 점수, \"hallucination\": 점수, \"reason\": \"한 줄 근거\"}}"
            )
            try:
                resp = client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=120,
                    timeout=30,
                )
                raw = resp.choices[0].message.content.strip()
                raw = re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()
                data = json.loads(raw)
                f_score = float(data.get("factual", 3))
                h_score = float(data.get("hallucination", 3))
                reason  = data.get("reason", "")
            except Exception as e:
                print(f"  ⚠️  [{ch['title']}] LLM 평가 실패: {e}")
                f_score, h_score, reason = 3.0, 3.0, "(평가 실패)"
                time.sleep(2)

            factual_scores.append(f_score)
            hallucination_scores.append(h_score)
            chapter_details.append({
                "title":        ch["title"],
                "factual":      f_score,
                "hallucination": h_score,
                "reason":       reason,
            })
            print(f"  [{ch['title']}] 사실근거 {f_score}/5, 할루시네이션 {h_score}/5")

        return {
            "factual_grounding":   sum(factual_scores)       / max(1, len(factual_scores)),
            "hallucination_score": sum(hallucination_scores) / max(1, len(hallucination_scores)),
            "chapter_details":     chapter_details,
        }
