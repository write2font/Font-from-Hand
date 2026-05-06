"""
eval_cli.py - 자서전 품질 자동 평가 CLI 래퍼
사용법: python3 eval_cli.py <json_file_path>
입력 JSON:
  {
    "chapters": [{"title": "...", "content": "..."}, ...],
    "interview_text": "전체 인터뷰 텍스트"
  }
출력: 평가 결과 JSON (stdout)
"""

import sys
import json
from cli_utils import exit_error, load_json_file, setup_path

setup_path()


def main():
    if len(sys.argv) < 2:
        exit_error("사용법: eval_cli.py <json_file_path>")

    try:
        data = load_json_file(sys.argv[1])

        chapters       = data.get("chapters", [])
        interview_text = data.get("interview_text", "")

        if not chapters:
            exit_error("chapters가 비어있습니다.")

        from src.evaluator import AutobiographyEvaluator
        evaluator = AutobiographyEvaluator()
        result = evaluator.evaluate(chapters, interview_text)

        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        import traceback
        print(json.dumps({"error": str(e), "trace": traceback.format_exc()}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
