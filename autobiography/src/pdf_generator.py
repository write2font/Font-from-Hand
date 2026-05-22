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
    def __init__(self, user_id: str, font_path: str = None):
        self.user_id       = user_id
        self.has_user_font = bool(font_path)
        font_handler       = FontHandler(user_id, font_path=font_path)
        self.font_info     = font_handler.get_font_info()
        self.output_dir    = os.path.join(config.OUTPUT_DIR, user_id)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, autobiography: dict, cover_image_path: str = None,
                 chapter_images: dict = None) -> str:
        user_name  = autobiography.get("user_name", "저자")
        chapters   = autobiography.get("chapters", [])
        persona    = autobiography.get("persona",  "Adult")
        age        = autobiography.get("age",       0)
        birth_year = autobiography.get("birth_year", str(datetime.now().year - age))
        hometown   = autobiography.get("hometown",  "")
        chapter_images = chapter_images or {}

        pdf = AutobiographyPDF(font_name=self.font_info["font_name"], user_name=user_name)
        self._register_font(pdf)

        # 1. 표지
        pdf.add_page()
        self._draw_cover(pdf, user_name, persona, birth_year, cover_image_path, autobiography)

        # 2. 목차
        pdf.add_page()
        self._draw_toc(pdf, chapters, user_name=user_name, birth_year=birth_year,
                       age=age, hometown=hometown)

        # 3. 챕터 본문
        for i, chapter in enumerate(chapters):
            pdf.add_page()
            self._draw_chapter(pdf, chapter["title"], chapter["content"],
                               chapter_num=i + 1, image_path=chapter_images.get(i))

        output_path = os.path.join(
            self.output_dir,
            f"{self.user_id}_autobiography.pdf",
        )
        pdf.output(output_path)
        print(f"[PDF] 생성 완료: {output_path}")
        return output_path

    def _register_font(self, pdf: FPDF):
        # 사용자가 직접 업로드한 폰트 최우선 적용
        if self.has_user_font:
            font_path = self.font_info.get("font_path", "")
            if font_path and os.path.exists(font_path):
                try:
                    pdf.add_font(self.font_info["font_name"], fname=font_path)
                    pdf.font_name = self.font_info["font_name"]
                    print(f"[PDF] 사용자 업로드 폰트 사용: {self.font_info['font_name']}")
                    return
                except Exception as e:
                    print(f"[PDF] ⚠️  사용자 폰트 실패 ({e})")

        # KoPub Batang 시도
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
        # 기본 폰트 폴백
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
        cover_title = autobiography.get("cover_title") or f"{user_name}의 이야기"
        m = config.PDF_MARGIN_MM

        if image_path and os.path.exists(image_path):
            # AI 이미지를 전체 페이지 배경으로 채우기
            pdf.image(image_path, x=0, y=0, w=pdf.w, h=pdf.h)

            # 하단 반투명 어두운 오버레이 (텍스트 가독성용)
            overlay_h = pdf.h * 0.40
            overlay_y = pdf.h - overlay_h
            try:
                with pdf.local_context(fill_opacity=0.60):
                    pdf.set_fill_color(15, 10, 8)
                    pdf.rect(0, overlay_y, pdf.w, overlay_h, "F")
            except Exception:
                pdf.set_fill_color(15, 10, 8)
                pdf.rect(0, overlay_y, pdf.w, overlay_h, "F")

            # 제목 텍스트 (오버레이 위, 흰색)
            pdf.set_y(overlay_y + 10)
            pdf.set_font(self.font_info["font_name"], size=config.PDF_TITLE_FONT_SIZE + 2)
            pdf.set_text_color(255, 255, 255)
            pdf.multi_cell(0, 10, cover_title, align="C")
            pdf.ln(4)

        else:
            # 이미지 없을 때: 따뜻한 단색 배경
            pdf.set_fill_color(245, 240, 230)
            pdf.rect(0, 0, pdf.w, pdf.h, "F")

            pdf.set_draw_color(180, 160, 130)
            pdf.set_line_width(0.5)
            pdf.line(10, pdf.h * 0.62, pdf.w - 10, pdf.h * 0.62)

            pdf.set_y(pdf.h * 0.45)
            pdf.set_font(self.font_info["font_name"], size=config.PDF_TITLE_FONT_SIZE + 2)
            pdf.set_text_color(40, 30, 20)
            pdf.multi_cell(0, 10, cover_title, align="C")
            pdf.ln(5)

            pdf.set_draw_color(160, 140, 110)
            pdf.set_line_width(0.3)
            pdf.line(m + 10, pdf.get_y(), pdf.w - m - 10, pdf.get_y())
            pdf.ln(5)

        pdf.set_text_color(0, 0, 0)

    def _draw_toc(self, pdf, chapters, user_name="", birth_year="", age=0, hometown=""):
        import re as _re
        m = config.PDF_MARGIN_MM
        pdf.set_y(m + 5)

        pdf.set_font(self.font_info["font_name"], size=12)
        pdf.set_text_color(60, 50, 40)
        pdf.cell(0, 10, "목  차", align="C")
        pdf.ln(8)
        pdf.set_draw_color(160, 140, 110)
        pdf.set_line_width(0.4)
        pdf.line(m, pdf.get_y(), pdf.w - m, pdf.get_y())
        pdf.ln(7)

        pdf.set_font(self.font_info["font_name"], size=9)
        pdf.set_text_color(40, 35, 30)
        row_h = 9
        usable_w = pdf.w - 2 * m
        num_w = 6

        for idx, chapter in enumerate(chapters, 1):
            title = _re.sub(r"\*+", "", chapter["title"]).strip()
            pdf.set_x(m)
            pdf.cell(num_w, row_h, f"{idx}", align="R")
            pdf.set_x(m + num_w + 2)
            pdf.cell(usable_w - num_w - 2, row_h, title, align="L")
            pdf.ln(row_h)
        pdf.set_text_color(0, 0, 0)

    def _draw_chapter(self, pdf, title, content, chapter_num=None, image_path=None):
        import re as _re
        m = config.PDF_MARGIN_MM
        pdf.set_y(m + 10)

        clean_title = _re.sub(r"\*+", "", title).strip()
        pdf.set_font(self.font_info["font_name"], size=config.PDF_TITLE_FONT_SIZE)
        pdf.set_text_color(30, 22, 14)
        pdf.multi_cell(0, 9, clean_title, align="L")
        pdf.ln(8)

        content = content.strip()

        # 챕터 이미지 (있을 때만)
        if image_path and os.path.exists(image_path):
            try:
                import tempfile
                from PIL import Image as PILImage, ExifTags

                pil_img = PILImage.open(image_path)

                # EXIF 회전 자동 보정 (폰 카메라 사진)
                try:
                    exif = pil_img._getexif()
                    if exif:
                        orient_key = next(
                            k for k, v in ExifTags.TAGS.items() if v == "Orientation"
                        )
                        orientation = exif.get(orient_key)
                        rotation_map = {3: 180, 6: 270, 8: 90}
                        if orientation in rotation_map:
                            pil_img = pil_img.rotate(
                                rotation_map[orientation], expand=True
                            )
                except Exception:
                    pass

                orig_w, orig_h = pil_img.size
                max_img_w = pdf.w - 2 * m
                img_h = max_img_w * orig_h / orig_w

                # 페이지 남은 공간보다 크면 축소
                max_h = pdf.h - pdf.get_y() - m - 15
                if img_h > max_h:
                    img_h = max_h
                    max_img_w = img_h * orig_w / orig_h

                # EXIF 보정된 임시 파일로 저장
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    tmp_path = tmp.name
                pil_img.convert("RGB").save(tmp_path, "JPEG", quality=85)

                pdf.image(tmp_path, x=m, y=pdf.get_y(), w=max_img_w, h=img_h)
                pdf.ln(img_h + 8)

                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

            except Exception as e:
                print(f"[PDF] 챕터 이미지 삽입 실패: {e}")

        # 본문 (줄간격 넉넉하게)
        pdf.set_font(self.font_info["font_name"], size=config.PDF_BODY_FONT_SIZE)
        pdf.set_text_color(30, 30, 30)
        effective_width = pdf.w - 2 * m
        line_h = config.PDF_LINE_HEIGHT
        paragraphs = [p.strip() for p in _re.split(r'\n+', content) if p.strip()]
        for i_p, para in enumerate(paragraphs):
            try:
                pdf.multi_cell(effective_width, line_h, para, align="L", wrapmode="CHAR")
            except TypeError:
                pdf.multi_cell(effective_width, line_h, para, align="L")
            if i_p < len(paragraphs) - 1:
                pdf.ln(2)


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
