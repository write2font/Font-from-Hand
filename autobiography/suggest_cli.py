"""
suggest_cli.py - 키워드 후보 + AI 제목 추천 CLI 래퍼
사용법: python3 suggest_cli.py <json_file_path>
입력 JSON:
  {
    "name": "이름",
    "birth": "YYYY-MM-DD",
    "transcriptions": ["답변1", ...],
    "followup_transcriptions": ["추가답변1", ...]
  }
출력: {"keywords": ["키워드1", ...], "title": "AI 생성 제목"}  (JSON, stdout)
"""

import sys
import json
from cli_utils import exit_error, load_json_file, setup_path

setup_path()


def main():
    if len(sys.argv) < 2:
        exit_error("사용법: suggest_cli.py <json_file_path>")

    try:
        data = load_json_file(sys.argv[1])

        name           = data.get("name", "")
        birth          = data.get("birth", "1970-01-01")
        transcriptions = data.get("transcriptions", [])
        followup_tx    = data.get("followup_transcriptions", [])

        transcript_text = "\n\n".join(t for t in transcriptions if t.strip())
        if followup_tx:
            transcript_text += "\n\n[추가 답변]\n" + "\n".join(t for t in followup_tx if t.strip())

        from src.nlp_processor import NLPProcessor
        nlp = NLPProcessor()

        keywords = nlp.extract_keywords(transcript_text, birth)
        title    = nlp._generate_cover_title(transcript_text, {}, name, birth.split("-")[0])

        print(json.dumps({"keywords": keywords, "title": title}, ensure_ascii=False))

    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
