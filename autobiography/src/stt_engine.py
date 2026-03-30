"""
src/stt_engine.py
Whisper 기반 STT(Speech-to-Text) 엔진
- 음성 파일 → 텍스트 변환
- 타임스탬프 포함 세그먼트 추출
- 결과를 JSON / TXT 양식으로 저장
"""

import os
import sys
import json
import whisper
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config


class STTEngine:
    def __init__(self):
        print(f"[STT] Whisper 모델 로딩 중: {config.WHISPER_MODEL}")
        self.model = whisper.load_model(config.WHISPER_MODEL)
        os.makedirs(config.TRANSCRIPT_DIR, exist_ok=True)

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def transcribe(self, audio_path: str, user_id: str) -> dict:
        """
        음성 파일을 텍스트로 변환하고 결과를 저장합니다.

        Args:
            audio_path: 원본 음성 파일 경로 (.mp3 / .m4a / .wav)
            user_id:    사용자 고유 ID (파일명 구분용)

        Returns:
            {
                "full_text": str,          # 전체 변환 텍스트
                "segments":  list[dict],   # 타임스탬프 포함 세그먼트
                "language":  str,          # 감지된 언어
                "saved_json": str,         # 저장된 JSON 경로
                "saved_txt":  str,         # 저장된 TXT 경로
            }
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"음성 파일을 찾을 수 없습니다: {audio_path}")

        print(f"[STT] 변환 시작: {os.path.basename(audio_path)}")
        result = self.model.transcribe(
            audio_path,
            language="ko",          # 한국어 고정
            verbose=False,
            word_timestamps=False,
        )

        transcript_data = self._build_transcript(result, audio_path, user_id)
        saved_json = self._save_json(transcript_data, user_id)
        saved_txt  = self._save_txt(transcript_data["full_text"], user_id)

        print(f"[STT] 완료! 저장 위치: {saved_json}")
        return {
            **transcript_data,
            "saved_json": saved_json,
            "saved_txt":  saved_txt,
        }

    # ──────────────────────────────────────────
    # Private Helpers
    # ──────────────────────────────────────────

    def _build_transcript(self, whisper_result: dict, audio_path: str, user_id: str) -> dict:
        """Whisper 원시 결과를 구조화된 딕셔너리로 변환합니다."""
        segments = [
            {
                "id":    seg["id"],
                "start": round(seg["start"], 2),
                "end":   round(seg["end"],   2),
                "text":  seg["text"].strip(),
            }
            for seg in whisper_result.get("segments", [])
        ]
        return {
            "user_id":    user_id,
            "audio_file": os.path.basename(audio_path),
            "language":   whisper_result.get("language", "ko"),
            "full_text":  whisper_result["text"].strip(),
            "segments":   segments,
            "created_at": datetime.now().isoformat(),
        }

    def _save_json(self, data: dict, user_id: str) -> str:
        """트랜스크립트를 JSON으로 저장합니다."""
        path = os.path.join(config.TRANSCRIPT_DIR, user_id, "transcript.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def _save_txt(self, full_text: str, user_id: str) -> str:
        """전체 텍스트를 TXT로 저장합니다."""
        path = os.path.join(config.TRANSCRIPT_DIR, user_id, "transcript.txt")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(full_text)
        return path


# ──────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────
if __name__ == "__main__":
    engine = STTEngine()
    test_audio = os.path.join(config.RAW_AUDIO_DIR, "sample.mp3")

    # 테스트용 더미 파일이 없으면 안내만 출력
    if not os.path.exists(test_audio):
        print(f"[테스트] 음성 파일을 data/01_raw_audio/sample.mp3 에 넣고 다시 실행하세요.")
    else:
        result = engine.transcribe(test_audio, user_id="test_user")
        print(f"[결과]\n{result['full_text'][:200]}...")
