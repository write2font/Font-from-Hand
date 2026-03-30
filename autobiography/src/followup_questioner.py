"""
src/followup_questioner.py
2차 질문 생성기

- 1차 인터뷰(15개) 답변을 분석
- 답변이 짧거나 애매한 질문에 대해 추가 질문 생성
- 사용자에게 대화형으로 답변 받아 segments 보강
"""

import os, sys, re
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config
from openai import OpenAI

client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

# 답변이 너무 짧다고 판단하는 최소 글자 수
MIN_ANSWER_LENGTH = 30


class FollowupQuestioner:

    def analyze_and_ask(self, segments: list) -> list:
        """
        각 세그먼트를 분석해서 보강이 필요한 항목에 2차 질문을 생성하고
        사용자에게 받아 segments를 업데이트해서 반환합니다.
        """
        followups = self._generate_followups(segments)

        if not followups:
            print("[2차 질문] 모든 답변이 충분합니다. 추가 질문 없음.")
            return segments

        print("\n" + "=" * 55)
        print("  📝 2차 질문 (더 풍부한 자서전을 위해)")
        print("  답변하기 어려우면 Enter만 눌러 건너뛸 수 있어요")
        print("=" * 55)

        seg_map = {seg["question"].split(".")[0].strip(): i
                   for i, seg in enumerate(segments)}

        for fq in followups:
            q_key   = fq["q_key"]   # 예: "Q3"
            fq_text = fq["question"]
            context = fq["context"]

            print(f"\n[{q_key} 관련]  {context}")
            print(f"  → {fq_text}")
            answer = input("  답변 > ").strip()

            if not answer:
                continue

            # 해당 세그먼트에 답변 추가
            idx = seg_map.get(q_key)
            if idx is not None:
                existing = segments[idx].get("answer", "")
                segments[idx]["answer"] = existing + "\n" + answer if existing else answer
                segments[idx]["followup_added"] = True

        print("\n[2차 질문] 완료 ✓")
        return segments

    def _generate_followups(self, segments: list) -> list:
        """LLM으로 추가 질문 생성"""
        # 짧거나 비어있는 답변만 추려서 LLM에 넘김
        thin = []
        for seg in segments:
            ans = seg.get("answer", "").strip()
            q   = seg.get("question", "")
            if len(ans) < MIN_ANSWER_LENGTH:
                thin.append(f"{q}\n답변: {ans if ans else '(없음)'}")

        if not thin:
            return []

        thin_str = "\n\n".join(thin[:8])  # 최대 8개

        prompt = (
            f"다음은 자서전 인터뷰에서 답변이 짧거나 없는 항목들이다:\n\n"
            f"{thin_str}\n\n"
            f"각 항목에 대해 더 구체적인 이야기를 끌어낼 수 있는 2차 질문을 만들어라.\n"
            f"형식 (각 줄):\n"
            f"Q번호|기존 질문 요약|2차 질문\n"
            f"예시:\n"
            f"Q3|좋아했던 장소|그 냇가에서 친구들과 어떤 놀이를 주로 했나요?\n"
            f"Q5|어린 시절 꿈|꿈을 이루기 위해 어떤 노력을 했나요?\n\n"
            f"최대 6개. 각 질문은 반드시 완전한 문장으로 끝내라. 절대 중간에 자르지 마라."
        )

        try:
            resp = client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
            )
            raw = resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[2차 질문] ⚠️  생성 실패: {e}")
            return []

        followups = []
        for line in raw.split("\n"):
            parts = line.strip().split("|")
            if len(parts) == 3:
                q_key   = parts[0].strip().upper()
                context = parts[1].strip()
                fq_text = parts[2].strip()
                if re.match(r"Q\d+", q_key):
                    followups.append({
                        "q_key":    q_key,
                        "context":  context,
                        "question": fq_text,
                    })

        print(f"[2차 질문] {len(followups)}개 생성됨")
        return followups
