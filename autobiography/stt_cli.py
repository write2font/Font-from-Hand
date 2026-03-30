"""
stt_cli.py - Spring Boot subprocess용 STT CLI 래퍼
사용법: python3 stt_cli.py <audio_path> <user_id>
출력:   {"text": "변환된 텍스트"}  (JSON, stdout)
"""

import json
import sys
from cli_utils import exit_error, setup_path

setup_path()


def main():
    if len(sys.argv) < 3:
        exit_error("사용법: stt_cli.py <audio_path> <user_id>")

    audio_path = sys.argv[1]
    user_id    = sys.argv[2]

    try:
        from src.stt_engine import STTEngine
        engine = STTEngine()
        result = engine.transcribe(audio_path, user_id)
        print(json.dumps({"text": result.get("full_text", "")}, ensure_ascii=False))
    except Exception as e:
        exit_error(str(e))


if __name__ == "__main__":
    main()
