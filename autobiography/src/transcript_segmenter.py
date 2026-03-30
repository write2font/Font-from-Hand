"""
src/transcript_segmenter.py
트랜스크립트 분할기 - 15개 질문별 답변 구분 + 편집 지원

사용법:
  1단계: 분할 실행
    python -m src.transcript_segmenter \
      --transcript data/02_transcripts/grandma_transcript.txt \
      --id grandma

  2단계: 생성된 텍스트 파일을 열어서 직접 수정
    data/02_transcripts/grandma_segmented.txt
    (오타 수정, 내용 보완 등 자유롭게 편집 후 저장)

  3단계: 편집된 파일로 자서전 생성
    python main.py --segmented data/02_transcripts/grandma_segmented.txt \
                   --birth 1952-02-22 --name "이종희" --id grandma
"""

import os
import sys
import json
import re

from openai import OpenAI

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config

client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)

QUESTIONS = [
    "Q1.  기초 정보: 성함과 생년월일, 그리고 유년 시절을 보낸 고향은 어디인가요?",
    "Q2.  가족 관계: 부모님은 어떤 분이셨으며, 형제들 사이에서 주로 어떤 역할이었나요?",
    "Q3.  유년의 풍경: 어린 시절 가장 좋아했던 장소와 그곳의 분위기를 묘사해 주세요.",
    "Q4.  기억의 조각: 유년 시절을 떠올리면 가장 먼저 생각나는 상징적인 사건이나 장면은?",
    "Q5.  꿈의 시작: 어린 시절의 꿈은 무엇이었으며, 현재의 직업/전공을 선택한 결정적 계기는?",
    "Q6.  학교 생활: 학창 시절 가장 열정적으로 몰두했던 공부나 활동은 무엇이었나요?",
    "Q7.  시대의 공기: 청년 시절 가장 뜨거웠던 기억(첫 취업, 시대적 사건 등)은 무엇인가요?",
    "Q8.  인연: 인생의 방향을 바꿔놓을 만큼 큰 영향을 준 스승이나 친구, 동료가 있나요?",
    "Q9.  시련의 순간: 인생에서 가장 힘들었던 시기는 언제였으며, 무엇이 가장 괴롭혔나요?",
    "Q10. 극복의 동력: 그 시련을 어떻게 버텨내셨으며, 그 과정에서 무엇을 배우셨나요?",
    "Q11. 빛나는 성취: '이것만큼은 정말 잘했다'고 자부하는 가장 큰 업적이나 결과물은?",
    "Q12. 삶의 전환점: 인생의 경로가 180도 바뀌었던 결정적인 선택의 순간과 그 이유는?",
    "Q13. 인생 철학: 평생을 지탱해 온 좌우명이나 꼭 지키고자 했던 원칙은 무엇인가요?",
    "Q14. 후회와 조언: 다시 태어난다면 해보고 싶은 일, 후배 세대에게 전하고 싶은 한마디는?",
    "Q15. 마지막 인사: 훗날 사람들이 당신을 어떤 사람으로 기억해주길 바라시나요?",
]


class TranscriptSegmenter:

    def segment(self, transcript_text: str) -> list:
        """전체 트랜스크립트를 15개 질문별 답변으로 분리합니다."""
        questions_str = "\n".join(QUESTIONS)
        prompt = f"""다음은 15개의 질문 순서로 진행된 인터뷰 녹취록입니다.
각 질문에 해당하는 답변 부분을 찾아 분리해주세요.

질문 목록:
{questions_str}

인터뷰 녹취록:
\"\"\"
{transcript_text}
\"\"\"

아래 JSON 형식으로만 응답하세요. 코드블록 없이 순수 JSON만 출력하세요.
답변을 찾을 수 없으면 빈 문자열로 남기세요:
{{
  "segments": [
    {{"question": "Q1.  기초 정보: ...", "answer": "답변 내용"}},
    ...
  ]
}}"""

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4000,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        result = json.loads(raw)

        segments = result.get("segments", [])
        while len(segments) < 15:
            idx = len(segments)
            segments.append({"question": QUESTIONS[idx], "answer": ""})
        return segments[:15]

    def save_txt(self, segments: list, user_id: str) -> str:
        """
        편집 가능한 텍스트 파일로 저장합니다.

        파일 형식:
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        Q1. 기초 정보: ...
        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        (답변 내용을 여기에 직접 수정하세요)

        Q2. ...
        """
        separator = "━" * 50
        lines = []
        lines.append("# 이 파일을 텍스트 에디터로 열어 답변 내용을 직접 수정할 수 있습니다.")
        lines.append("# 구분선(━)과 질문 줄은 수정하지 마세요. 답변 내용만 수정하세요.")
        lines.append("")

        for seg in segments:
            lines.append(separator)
            lines.append(seg["question"])
            lines.append(separator)
            lines.append(seg["answer"] if seg["answer"] else "(답변 없음 - 여기에 내용을 입력하세요)")
            lines.append("")

        path = os.path.join(config.TRANSCRIPT_DIR, user_id, "segmented.txt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    def save_json(self, segments: list, user_id: str) -> str:
        """JSON 백업으로도 저장합니다."""
        data = {"user_id": user_id, "segments": segments}
        path = os.path.join(config.TRANSCRIPT_DIR, user_id, "segmented.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    @staticmethod
    def load_txt(txt_path: str) -> list:
        """
        편집된 텍스트 파일을 읽어 segments 리스트로 반환합니다.
        """
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()

        separator = "━" * 50
        segments = []
        blocks = content.split(separator)

        # blocks: [주석, 질문1, 답변1, 질문2, 답변2, ...]
        i = 0
        while i < len(blocks):
            block = blocks[i].strip()
            # 질문 줄 찾기 (Q로 시작하는 블록)
            if re.match(r"^Q\d+", block):
                question = block
                answer   = blocks[i + 1].strip() if i + 1 < len(blocks) else ""
                # 주석 줄 제거
                answer = "\n".join(
                    line for line in answer.split("\n")
                    if not line.startswith("#")
                ).strip()
                if answer == "(답변 없음 - 여기에 내용을 입력하세요)":
                    answer = ""
                segments.append({"question": question, "answer": answer})
                i += 2
            else:
                i += 1

        return segments

    @staticmethod
    def to_full_text(segments: list) -> str:
        """분할된 세그먼트를 챕터 생성에 쓸 전체 텍스트로 합칩니다."""
        parts = []
        for seg in segments:
            if seg.get("answer", "").strip():
                parts.append(f"[{seg['question'].strip()}]\n{seg['answer'].strip()}")
        return "\n\n".join(parts)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--id",         required=True)
    args = parser.parse_args()

    with open(args.transcript, "r", encoding="utf-8") as f:
        text = f.read()

    segmenter = TranscriptSegmenter()
    print("[Segmenter] 질문별 분할 중... (약 10~20초)")
    segments = segmenter.segment(text)

    txt_path  = segmenter.save_txt(segments,  args.id)
    json_path = segmenter.save_json(segments, args.id)

    print(f"\n✅ 완료!")
    print(f"📝 편집용 텍스트: {txt_path}")
    print(f"💾 JSON 백업:     {json_path}")
    print(f"\n────────────────────────────────────")
    print(f"텍스트 파일을 열어 오타/내용을 수정한 뒤:")
    print(f"python main.py --segmented {txt_path} \\")
    print(f"               --birth 생년월일 --name 이름 --id {args.id}")
    print(f"────────────────────────────────────")

    print("\n====== 분할 미리보기 ======")
    for seg in segments:
        preview = seg["answer"][:50].replace("\n", " ") if seg["answer"] else "(없음)"
        print(f"{seg['question'][:35]:<37} → {preview}")
