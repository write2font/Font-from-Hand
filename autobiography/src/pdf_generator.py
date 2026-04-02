"""
src/pdf_generator.py
PDF 생성기 - FPDF2 기반 자서전 레이아웃 구성 및 PDF 출력
"""

import os
import sys
from fpdf import FPDF
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config
from src.font_handler import FontHandler


class AutobiographyPDF(FPDF):
    def __init__(self, font_name: str, user_name: str):
        # A6 = 105x148mm (fpdf2가 A6 문자열 미지원 → 직접 크기 지정)
        fmt = config.PDF_PAGE_SIZE.upper()
        page_format = (105, 148) if fmt == "A6" else fmt
        super().__init__(orientation="P", unit="mm", format=page_format)
        self.font_name = font_name
        self.user_name = user_name
        self.set_margins(
            left=config.PDF_MARGIN_MM,
            top=config.PDF_MARGIN_MM,
            right=config.PDF_MARGIN_MM,
        )
        self.set_auto_page_break(auto=True, margin=config.PDF_MARGIN_MM + 5)

    def header(self):
        pass  # 헤더 없음

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        try:
            self.set_font(self.font_name, size=9)
        except Exception:
            self.set_font("Helvetica", size=9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, str(self.page_no()), align="C")
        self.set_text_color(0, 0, 0)


class PDFGenerator:
    def __init__(self, user_id: str):
        self.user_id    = user_id
        font_handler    = FontHandler(user_id)
        self.font_info  = font_handler.get_font_info()
        self.output_dir = os.path.join(config.OUTPUT_DIR, user_id)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, autobiography: dict, cover_image_path: str = None) -> str:
        user_name  = autobiography.get("user_name", "저자")
        chapters   = autobiography.get("chapters", [])
        persona    = autobiography.get("persona",  "Adult")
        age        = autobiography.get("age",       0)
        birth_year = autobiography.get("birth_year", str(datetime.now().year - age))

        pdf = AutobiographyPDF(font_name=self.font_info["font_name"], user_name=user_name)
        self._register_font(pdf)

        # 1. 표지
        pdf.add_page()
        self._draw_cover(pdf, user_name, persona, birth_year, cover_image_path, autobiography)

        # 2. 목차
        pdf.add_page()
        self._draw_toc(pdf, chapters)

        # 3. 챕터 본문
        for chapter in chapters:
            pdf.add_page()
            self._draw_chapter(pdf, chapter["title"], chapter["content"])

        output_path = os.path.join(
            self.output_dir,
            f"{self.user_id}_autobiography.pdf",
        )
        pdf.output(output_path)
        print(f"[PDF] 생성 완료: {output_path}")
        return output_path

    def _register_font(self, pdf: FPDF):
        # KoPub Batang 우선 시도
        kopub_path = getattr(config, "PDF_KOPUB_FONT", "")
        if kopub_path and os.path.exists(kopub_path):
            try:
                pdf.add_font("kopub", fname=kopub_path)
                self.font_info["font_name"] = "kopub"
                pdf.font_name = "kopub"
                print(f"[PDF] KoPub Batang 폰트 사용")
                return
            except Exception as e:
                print(f"[PDF] ⚠️  KoPub 실패 ({e})")
        # USE_DEFAULT_FONT or 사용자 폰트
        if getattr(config, "USE_DEFAULT_FONT", False):
            try:
                pdf.add_font("default_font", fname=config.PDF_FALLBACK_FONT)
                self.font_info["font_name"] = "default_font"
                pdf.font_name = "default_font"
                print(f"[PDF] 기본 폰트 사용")
                return
            except Exception as e:
                print(f"[PDF] ⚠️  기본 폰트 실패 ({e})")
        try:
            pdf.add_font(self.font_info["font_name"], fname=self.font_info["font_path"])
            pdf.font_name = self.font_info["font_name"]
            print(f"[PDF] 폰트 등록: {self.font_info['font_name']}")
        except Exception as e:
            print(f"[PDF] ⚠️  폰트 등록 실패 ({e}) → NanumGothic")
            try:
                pdf.add_font("default_font", fname=config.PDF_FALLBACK_FONT)
                self.font_info["font_name"] = "default_font"
                pdf.font_name = "default_font"
            except Exception as e:
                print(f"[PDF] ⚠️  기본 폰트 등록 실패 ({e}) → Helvetica")
                self.font_info["font_name"] = "Helvetica"
                pdf.font_name = "Helvetica"

    def _draw_cover(self, pdf, user_name, persona, birth_year, image_path, autobiography={}):
        # 배경색 (이미지 없을 때)
        pdf.set_fill_color(245, 240, 230)
        pdf.rect(0, 0, pdf.w, pdf.h, "F")

        if image_path and os.path.exists(image_path):
            # 이미지 원본 비율 유지하면서 최대 너비/높이 안에 맞추기
            from PIL import Image as PILImage
            try:
                with PILImage.open(image_path) as im:
                    orig_w, orig_h = im.size
            except Exception:
                orig_w, orig_h = 1, 1

            max_w = pdf.w                  # 페이지 너비
            max_h = pdf.h * 0.62           # 상단 62% 영역

            ratio = min(max_w / orig_w, max_h / orig_h)
            img_w = orig_w * ratio
            img_h = orig_h * ratio

            # 수평 중앙 정렬
            img_x = (pdf.w - img_w) / 2
            pdf.image(image_path, x=img_x, y=0, w=img_w, h=img_h)

            # 이미지 아래 배경
            img_bottom = img_h
            pdf.set_fill_color(245, 240, 230)
            pdf.rect(0, img_bottom, pdf.w, pdf.h - img_bottom, "F")
            title_y = img_bottom + 4
        else:
            # 이미지 없으면 장식용 선만
            pdf.set_draw_color(180, 160, 130)
            pdf.set_line_width(0.5)
            pdf.line(10, pdf.h * 0.62, pdf.w - 10, pdf.h * 0.62)
            title_y = pdf.h * 0.45

        # 본제목
        cover_title = autobiography.get("cover_title") or f"{user_name}의 이야기"
        pdf.set_y(title_y)
        pdf.set_font(self.font_info["font_name"], size=config.PDF_TITLE_FONT_SIZE + 2)
        pdf.set_text_color(40, 30, 20)
        pdf.multi_cell(0, 10, cover_title, align="C")
        pdf.ln(5)

        # 구분선
        m = config.PDF_MARGIN_MM
        pdf.set_draw_color(160, 140, 110)
        pdf.set_line_width(0.3)
        pdf.line(m + 10, pdf.get_y(), pdf.w - m - 10, pdf.get_y())
        pdf.ln(5)

        pdf.set_text_color(0, 0, 0)

    def _draw_toc(self, pdf, chapters):
        m = config.PDF_MARGIN_MM
        pdf.set_y(m + 3)
        pdf.set_font(self.font_info["font_name"], size=14)
        pdf.cell(0, 10, "목  차", align="C")
        pdf.ln(10)
        pdf.set_draw_color(120, 120, 120)
        pdf.line(m, pdf.get_y(), pdf.w - m, pdf.get_y())
        pdf.ln(8)

        pdf.set_font(self.font_info["font_name"], size=10)
        import re as _re
        row_h = 10
        for idx, chapter in enumerate(chapters, 1):
            title = _re.sub(r"\*+", "", chapter["title"]).strip()
            pdf.cell(8, row_h, f"{idx}.", align="R")
            pdf.cell(0, row_h, f"  {title}", align="L")
            pdf.ln(row_h)

    def _draw_chapter(self, pdf, title, content):
        import re as _re
        m = config.PDF_MARGIN_MM
        pdf.set_y(m + 8)

        # 챕터 제목 (마크다운 제거)
        clean_title = _re.sub(r"\*+", "", title).strip()
        pdf.set_font(self.font_info["font_name"], size=18)
        pdf.set_text_color(20, 20, 20)
        pdf.multi_cell(0, 11, clean_title, align="L")
        pdf.ln(4)

        # 본문 첫 줄이 제목과 같으면 제거
        content_lines = content.strip().split("\n")
        while content_lines:
            first = _re.sub(r"\*+|\s+", "", content_lines[0])
            ttl   = _re.sub(r"\s+", "", clean_title)
            if first == ttl or first.startswith(ttl):
                content_lines.pop(0)
            else:
                break
        content = "\n".join(content_lines).strip()

        # 구분선
        pdf.set_draw_color(80, 80, 80)
        pdf.line(m, pdf.get_y(), m + 35, pdf.get_y())
        pdf.ln(10)

        # 본문 (줄간격 넉넉하게)
        pdf.set_font(self.font_info["font_name"], size=config.PDF_BODY_FONT_SIZE)
        pdf.set_text_color(30, 30, 30)
        effective_width = pdf.w - 2 * m
        line_h = config.PDF_LINE_HEIGHT
        try:
            # FPDF2 - 한국어 음절 단위 줄바꿈 (오른쪽 공백 방지)
            pdf.multi_cell(effective_width, line_h, content, align="L", wrapmode="CHAR")
        except TypeError:
            pdf.multi_cell(effective_width, line_h, content, align="L")


if __name__ == "__main__":
    dummy = {
        "user_name":  "홍길동",
        "persona":    "Senior",
        "age":        70,
        "birth_year": "1955",
        "chapters": [
            {"title": "냇가의 기억", "content": "나는 1955년 봄, 경상남도 어느 작은 마을에서 태어났다..."},
            {"title": "달리기와 꿈",  "content": "학교는 마을에서 걸어서 한 시간 거리에 있었다..."},
        ],
    }
    gen  = PDFGenerator(user_id="test_user")
    path = gen.generate(dummy)
    print(f"테스트 PDF: {path}")
