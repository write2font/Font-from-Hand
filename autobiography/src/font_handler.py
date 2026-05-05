"""
src/font_handler.py
폰트 핸들러 - 사용자 전용 TTF 폰트 로드 및 관리
- MX-Font / FontDiffuser로 생성된 .ttf 파일 검증
- FPDF2에 등록 가능한 형태로 래핑
- 폰트 부재 시 폴백(NanumGothic 등) 자동 적용
"""

import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config


class FontHandler:
    """
    사용자 전용 폰트(.ttf)를 로드하고,
    PDF 생성 시 FPDF2에 등록할 수 있는 메타 정보를 제공합니다.
    """

    def __init__(self, user_id: str):
        self.user_id      = user_id
        self.font_dir     = config.FONT_DIR
        self.font_path    = self._resolve_font_path()
        self.font_name    = self._derive_font_name()
        self.is_custom    = self._check_is_custom()

        self._log_status()

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def get_font_info(self) -> dict:
        """
        PDF 생성 모듈에 전달할 폰트 정보 딕셔너리를 반환합니다.

        Returns:
            {
                "font_path": str,      # TTF 절대 경로
                "font_name": str,      # FPDF2에 등록할 폰트명
                "is_custom": bool,     # 사용자 전용 폰트 여부
            }
        """
        return {
            "font_path": self.font_path,
            "font_name": self.font_name,
            "is_custom": self.is_custom,
        }

    def validate(self) -> bool:
        """폰트 파일이 실제로 존재하고 읽기 가능한지 검증합니다."""
        path = Path(self.font_path)
        if not path.exists():
            print(f"[Font] ⚠️  폰트 파일 없음: {self.font_path}")
            return False
        if not path.suffix.lower() == ".ttf":
            print(f"[Font] ⚠️  TTF 형식이 아닙니다: {self.font_path}")
            return False
        if path.stat().st_size < 1024:
            print(f"[Font] ⚠️  폰트 파일이 너무 작습니다 (손상 가능성): {self.font_path}")
            return False
        print(f"[Font] ✓ 폰트 검증 성공: {self.font_path}")
        return True

    # ──────────────────────────────────────────
    # Private Helpers
    # ──────────────────────────────────────────

    def _resolve_font_path(self) -> str:
        """
        사용자 전용 폰트를 탐색하고, 없으면 폴백 폰트 경로를 반환합니다.
        탐색 우선순위:
          1. data/04_user_fonts/{user_id}.ttf
          2. data/04_user_fonts/{user_id}_font.ttf
          3. config.PDF_FALLBACK_FONT (기본 폰트)
        """
        candidates = [
            os.path.join(self.font_dir, f"{self.user_id}.ttf"),
            os.path.join(self.font_dir, f"{self.user_id}_font.ttf"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return os.path.abspath(path)

        # 폴백
        fallback = os.path.join(config.BASE_DIR, config.PDF_FALLBACK_FONT)
        return os.path.abspath(fallback)

    def _derive_font_name(self) -> str:
        """FPDF2 내부에서 사용할 폰트 등록명을 생성합니다."""
        basename = Path(self.font_path).stem  # 확장자 제거
        # FPDF2는 공백 없는 알파벳/숫자 폰트명 권장
        return basename.replace(" ", "_").replace("-", "_")

    def _check_is_custom(self) -> bool:
        """현재 로드된 폰트가 사용자 전용인지 여부를 반환합니다."""
        return self.user_id in Path(self.font_path).stem

    def _log_status(self):
        if self.is_custom:
            print(f"[Font] 사용자 전용 폰트 로드됨: {os.path.basename(self.font_path)}")
        else:
            print(f"[Font] 사용자 폰트 없음 → 폴백 폰트 사용: {os.path.basename(self.font_path)}")


# ──────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────
if __name__ == "__main__":
    handler = FontHandler(user_id="test_user")
    info    = handler.get_font_info()
    valid   = handler.validate()
    print(f"\n폰트 정보: {info}")
    print(f"검증 결과: {'통과' if valid else '실패'}")
