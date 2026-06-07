"""
src/latex_renderer.py
XeLaTeX 기반 자서전 PDF 생성기
- xelatex + kotex 한글 지원
- fontspec으로 사용자 손글씨 TTF 폰트 적용
"""

import os
import re
import sys
import subprocess
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import config
from src.font_handler import FontHandler


def _escape(text: str) -> str:
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('{',  r'\{'),
        ('}',  r'\}'),
        ('$',  r'\$'),
        ('&',  r'\&'),
        ('#',  r'\#'),
        ('^',  r'\^{}'),
        ('_',  r'\_'),
        ('~',  r'\textasciitilde{}'),
        ('%',  r'\%'),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


class LaTeXRenderer:
    def __init__(self, user_id: str, font_path: str = None):
        self.user_id    = user_id
        font_handler    = FontHandler(user_id, font_path=font_path)
        self.font_info  = font_handler.get_font_info()
        self.output_dir = os.path.join(config.OUTPUT_DIR, user_id)
        os.makedirs(self.output_dir, exist_ok=True)

    def generate(self, autobiography: dict, cover_image_path: str = None,
                 chapter_images: dict = None, chapter_captions: dict = None) -> str:
        user_name      = autobiography.get("user_name", "저자")
        chapters       = autobiography.get("chapters", [])
        cover_title    = autobiography.get("cover_title") or f"{user_name}의 이야기"
        chapter_images   = chapter_images or {}
        chapter_captions = chapter_captions or {}

        tex      = self._build_tex(user_name, cover_title, chapters,
                                   cover_image_path, chapter_images, chapter_captions)
        tex_path = os.path.join(self.output_dir, f"{self.user_id}_autobiography.tex")
        pdf_path = os.path.join(self.output_dir, f"{self.user_id}_autobiography.pdf")

        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex)

        self._compile(tex_path)
        print(f"[LaTeX] PDF 생성 완료: {pdf_path}")
        return pdf_path

    def _build_tex(self, user_name, cover_title, chapters,
                   cover_image_path, chapter_images, chapter_captions) -> str:
        import shutil as _shutil
        # 폰트 파일을 output 디렉토리에 안전한 이름으로 복사 (경로에 _등 특수문자 방지)
        raw_font_path = os.path.abspath(self.font_info["font_path"])
        ext = os.path.splitext(raw_font_path)[1] or ".ttf"
        safe_font_name = f"userfont{ext}"
        safe_font_dest = os.path.join(self.output_dir, safe_font_name)
        if os.path.exists(raw_font_path) and raw_font_path != safe_font_dest:
            _shutil.copy2(raw_font_path, safe_font_dest)
        font_dir  = self.output_dir.replace("\\", "/") + "/"
        font_stem = os.path.splitext(safe_font_name)[0]   # "userfont"

        fallback_abs  = os.path.abspath(os.path.join(config.BASE_DIR, config.PDF_KOPUB_FONT))
        fallback_dir  = os.path.dirname(fallback_abs).replace("\\", "/") + "/"
        fallback_stem = os.path.splitext(os.path.basename(fallback_abs))[0]

        lines = []

        # ── 프리앰블 ──────────────────────────────────────────────────────────
        lines += [
            r'\documentclass[a6paper, 10pt, openany]{book}',
            r'\usepackage{fontspec}',
            r'\usepackage{xeCJK}',
            r'\usepackage{graphicx}',
            r'\usepackage{geometry}',
            r'\usepackage{titlesec}',
            r'\usepackage{fancyhdr}',
            r'\usepackage{setspace}',
            r'\usepackage{xcolor}',
            r'\usepackage[hidelinks]{hyperref}',
            r'',
            r'\geometry{a6paper, top=15mm, bottom=15mm, left=14mm, right=14mm}',
            r'\definecolor{covercolor}{RGB}{245,240,230}',
            r'\definecolor{coverrule}{RGB}{160,140,110}',
            r'\xeCJKsetup{CJKspace=true}',
            r'\XeTeXlinebreaklocale "ko"',
            r'\XeTeXlinebreakskip = 0pt plus 1pt',
            r'',
        ]

        # 사용자 손글씨 폰트 — Path/Extension 옵션으로 절대경로 특수문자 우회
        lines += [
            f'\\setmainfont[Path={font_dir},Extension={ext}]{{{font_stem}}}',
            f'\\setCJKmainfont[Path={font_dir},Extension={ext}]{{{font_stem}}}',
            f'\\setCJKfallbackfamilyfont{{\\CJKrmdefault}}[Path={fallback_dir},Extension=.ttf]{{{fallback_stem}}}',
            r'',
        ]

        # 챕터 제목 스타일 (번호 없이)
        lines += [
            r'\titleformat{\chapter}[block]',
            r'  {\normalfont\Large\bfseries\centering}',
            r'  {}{0em}{}',
            r'\titlespacing*{\chapter}{0pt}{0pt}{15pt}',
            r'',
            r'\pagestyle{fancy}',
            r'\fancyhf{}',
            r'\fancyfoot[C]{\small\thepage}',
            r'\renewcommand{\headrulewidth}{0pt}',
            r'',
            r'\setstretch{1.7}',
            r'\setlength{\parindent}{1em}',
            r'\setlength{\parskip}{0.4em}',
            r'',
            r'\begin{document}',
            r'',
        ]

        # ── 표지 ──────────────────────────────────────────────────────────────
        lines.append(r'\begin{titlepage}')
        lines.append(r'\thispagestyle{empty}')
        if cover_image_path and os.path.exists(cover_image_path):
            abs_img = os.path.abspath(cover_image_path).replace("\\", "/")
            lines += [
                r'\vspace*{\fill}',
                r'\begin{center}',
                f'\\includegraphics[width=\\textwidth,height=0.55\\textheight,'
                f'keepaspectratio]{{{abs_img}}}\\\\[2em]',
                f'{{\\Huge\\bfseries {_escape(cover_title)}}}\\\\[1.5em]',
                r'\rule{0.6\textwidth}{0.4pt}\\[1em]',
                f'{{\\Large {_escape(user_name)}}}',
                r'\end{center}',
                r'\vspace*{\fill}',
            ]
        else:
            lines += [
                r'\pagecolor{covercolor}',
                r'\vspace*{0.28\textheight}',
                r'\begin{center}',
                r'{\color{coverrule}\rule{0.72\textwidth}{0.8pt}}\\[2.8em]',
                f'{{\\Huge\\bfseries {_escape(cover_title)}}}\\\\[2em]',
                r'{\color{coverrule}\rule{0.5\textwidth}{0.4pt}}\\[1.8em]',
                f'{{\\large {_escape(user_name)}}}',
                r'\end{center}',
                r'\vfill',
                r'\begin{center}',
                r'{\color{coverrule}\rule{0.72\textwidth}{0.8pt}}',
                r'\end{center}',
            ]
        lines += [
            r'\end{titlepage}',
            r'\pagecolor{white}',
            r'',
        ]

        # ── 목차 ──────────────────────────────────────────────────────────────
        lines += [
            r'\tableofcontents',
            r'\newpage',
            r'',
        ]

        # ── 챕터 본문 ─────────────────────────────────────────────────────────
        for i, chapter in enumerate(chapters):
            title   = re.sub(r'\*+', '', chapter.get('title', '')).strip()
            content = chapter.get('content', '').strip()
            img_path = chapter_images.get(i)

            # 챕터 제목 (번호 없이, TOC에는 포함)
            lines.append(f'\\chapter{{{_escape(title)}}}')
            lines.append(r'')

            # 챕터 이미지 — float 없이 인라인 배치 (본문 밀림 방지)
            if img_path and os.path.exists(img_path):
                abs_img = os.path.abspath(img_path).replace("\\", "/")
                caption = chapter_captions.get(i, "")
                lines += [r'\begin{center}']
                lines.append(f'\\includegraphics[width=0.82\\textwidth]{{{abs_img}}}')
                if caption:
                    lines.append(f'\\\\[0.3em]{{\\small\\textit{{{_escape(caption)}}}}}')
                lines += [r'\end{center}', r'\vspace{0.5em}', r'']

            # 본문 단락
            paragraphs = [p.strip() for p in re.split(r'\n+', content) if p.strip()]
            for para in paragraphs:
                lines.append(_escape(para))
                lines.append(r'')

        lines.append(r'\end{document}')
        return '\n'.join(lines)

    def _compile(self, tex_path: str):
        work_dir = os.path.dirname(tex_path)
        cmd = ['xelatex', '-interaction=nonstopmode', os.path.basename(tex_path)]
        for run in range(2):  # 목차 반영을 위해 2회 컴파일
            result = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)
            if result.returncode != 0:
                log = (result.stdout + result.stderr).splitlines()
                for line in log[-40:]:
                    print(f'[LaTeX] {line}')
                raise RuntimeError(f'xelatex 컴파일 실패 (run {run+1}): {tex_path}')
        print('[LaTeX] 컴파일 완료 (2회)')
