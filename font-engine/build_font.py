#!/usr/bin/env fontforge
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fontforge

from config import (
    FONT_ASCENT,
    FONT_BOTTOM_PADDING,
    FONT_DESCENT,
    FONT_EM,
    FONT_INNER_MAX_WIDTH,
    FONT_LSB,
    FONT_MAX_ADVANCE_WIDTH,
    FONT_MIN_ADVANCE_WIDTH,
    FONT_RSB,
    FONT_TOP_PADDING,
)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def build_font(manifest_path: str, out_ttf: str) -> None:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    family = manifest["family_name"]
    glyphs = manifest["glyphs"]

    font = fontforge.font()
    font.encoding = "UnicodeFull"
    font.em = FONT_EM
    font.ascent = FONT_ASCENT
    font.descent = FONT_DESCENT
    font.familyname = family
    font.fontname = family.replace(" ", "")
    font.fullname = family
    font.version = "1.4"

    available_h = max(1, FONT_ASCENT - FONT_TOP_PADDING - FONT_BOTTOM_PADDING)
    available_w = max(1, FONT_INNER_MAX_WIDTH)

    total = len(glyphs)
    print(f"[fontforge] start build: {total} glyphs", flush=True)

    for idx, item in enumerate(glyphs, start=1):
        if idx == 1 or idx % 50 == 0 or idx == total:
            print(f"[fontforge] {idx}/{total}", flush=True)

        ch = item["char"]
        svg_path = item["svg_path"]
        glyph = font.createChar(ord(ch), ch)
        glyph.importOutlines(svg_path)

        xmin, ymin, xmax, ymax = glyph.boundingBox()
        if xmax > xmin and ymax > ymin:
            outline_w = float(xmax - xmin)
            outline_h = float(ymax - ymin)

            scale_x = available_w / outline_w
            scale_y = available_h / outline_h
            scale = min(scale_x, scale_y)
            glyph.transform((scale, 0, 0, scale, 0, 0))

            xmin, ymin, xmax, ymax = glyph.boundingBox()
            ty = FONT_BOTTOM_PADDING - ymin
            glyph.transform((1, 0, 0, 1, 0, ty))

            xmin, ymin, xmax, ymax = glyph.boundingBox()
            real_w = xmax - xmin
            needed_width = int(round(real_w + FONT_LSB + FONT_RSB))
            advance_width = _clamp(
                needed_width,
                FONT_MIN_ADVANCE_WIDTH,
                FONT_MAX_ADVANCE_WIDTH,
            )

            target_left = (advance_width - real_w) / 2.0
            tx = target_left - xmin
            glyph.transform((1, 0, 0, 1, tx, 0))
            glyph.width = advance_width
        else:
            glyph.width = FONT_MIN_ADVANCE_WIDTH

        glyph.round()

    space = font.createChar(0x20, "space")
    if space.width <= 0:
        space.width = FONT_MIN_ADVANCE_WIDTH // 2

    print("[fontforge] generating ttf...", flush=True)
    font.generate(out_ttf)
    font.close()
    print(f"[fontforge] done: {out_ttf}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: fontforge -script build_font.py <manifest.json> <out.ttf>", file=sys.stderr)
        sys.exit(1)

    build_font(sys.argv[1], sys.argv[2])
