"""
followup_cli.py - Spring Boot subprocess용 추가질문 생성 CLI 래퍼
사용법: python3 followup_cli.py <json_file_path>
입력 JSON: {"qas": [{"question": "...", "category": "...", "answer": "..."}]}
출력:      {"followups": ["질문1", "질문2", ...]}  (JSON, stdout)
"""

import json
import sys
from cli_utils import exit_error, load_json_file, setup_path

setup_path()


def main():
    if len(sys.argv) < 2:
        exit_error("사용법: followup_cli.py <json_file_path>")

    try:
        data = load_json_file(sys.argv[1])
        qas  = data.get("qas", [])

        segments = [
            {
                "question": f"Q{i+2}. {qa.get('question', '')}",
                "answer":   qa.get("answer", ""),
                "category": qa.get("category", ""),
            }
            for i, qa in enumerate(qas)
        ]

        from src.followup_questioner import FollowupQuestioner
        questioner   = FollowupQuestioner()
        followup_list = questioner._generate_followups(segments)

        questions = [fq.get("question", "") for fq in followup_list if fq.get("question")]
        print(json.dumps({"followups": questions}, ensure_ascii=False))

    except Exception as e:
        exit_error(str(e))


if __name__ == "__main__":
    main()
