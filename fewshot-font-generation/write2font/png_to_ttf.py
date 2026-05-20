from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np


FONT_EM = 1000
FONT_ASCENT = 820
FONT_DESCENT = 180
FONT_PADDING = 90
FONT_MIN_WIDTH = 360
FONT_MAX_WIDTH = 980


def safe_family_name(value: str) -> str:
    keep = [ch for ch in value if ch.isalnum() or ch in (" ", "-", "_")]
    return "".join(keep).strip() or "Write2Font"


def glyph_to_pbm(image_path: Path, pbm_path: Path) -> None:
    image = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"failed to read generated image: {image_path}")
    _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    border = np.concatenate(
        [
            binary[0, :],
            binary[-1, :],
            binary[:, 0],
            binary[:, -1],
        ]
    )
    if np.median(border) < 127:
        binary = 255 - binary
    cv2.imwrite(str(pbm_path), binary)


def build_svgs(input_dir: Path, chars: list[str], svg_dir: Path, potrace_cmd: str) -> list[dict]:
    glyphs = []
    svg_dir.mkdir(parents=True, exist_ok=True)
    for char in chars:
        image_path = input_dir / f"{char}.png"
        if not image_path.exists():
            continue
        pbm_path = svg_dir / f"u{ord(char):04x}.pbm"
        svg_path = svg_dir / f"u{ord(char):04x}.svg"
        glyph_to_pbm(image_path, pbm_path)
        subprocess.run(
            [potrace_cmd, str(pbm_path), "-s", "-o", str(svg_path), "--turdsize", "2"],
            check=True,
        )
        glyphs.append({"char": char, "svg_path": str(svg_path)})
        pbm_path.unlink(missing_ok=True)
    return glyphs


def write_fontforge_script(path: Path) -> None:
    path.write_text(
        r'''
import json
import sys
import fontforge

FONT_EM = 1000
FONT_ASCENT = 820
FONT_DESCENT = 180
FONT_PADDING = 90
FONT_MIN_WIDTH = 360
FONT_MAX_WIDTH = 980


def clamp(value, low, high):
    return max(low, min(high, value))


manifest_path, out_ttf = sys.argv[1], sys.argv[2]
manifest = json.load(open(manifest_path, encoding="utf-8"))
family = manifest["family_name"]
glyphs = manifest["glyphs"]

font = fontforge.font()
font.encoding = "UnicodeFull"
font.em = FONT_EM
font.ascent = FONT_ASCENT
font.descent = FONT_DESCENT
font.familyname = family
font.fontname = "".join(ch for ch in family if ch.isalnum()) or "Write2Font"
font.fullname = family
font.version = "1.0"

available_h = FONT_ASCENT - FONT_PADDING
available_w = FONT_EM - FONT_PADDING * 2

for item in glyphs:
    ch = item["char"]
    glyph = font.createChar(ord(ch), ch)
    glyph.importOutlines(item["svg_path"])
    xmin, ymin, xmax, ymax = glyph.boundingBox()
    if xmax > xmin and ymax > ymin:
        outline_w = xmax - xmin
        outline_h = ymax - ymin
        scale = min(available_w / outline_w, available_h / outline_h)
        glyph.transform((scale, 0, 0, scale, 0, 0))
        xmin, ymin, xmax, ymax = glyph.boundingBox()
        glyph.transform((1, 0, 0, 1, -xmin + FONT_PADDING, FONT_DESCENT))
        xmin, ymin, xmax, ymax = glyph.boundingBox()
        width = clamp(int((xmax - xmin) + FONT_PADDING * 2), FONT_MIN_WIDTH, FONT_MAX_WIDTH)
        glyph.width = width
    else:
        glyph.width = FONT_MIN_WIDTH
    glyph.round()

space = font.createChar(0x20, "space")
space.width = FONT_MIN_WIDTH

font.generate(out_ttf)
font.close()
'''.strip(),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a TTF from generated write2font PNG glyphs.")
    parser.add_argument("--input-dir", required=True, help="Directory containing <char>.png files")
    parser.add_argument("--chars", default="write2font/gen_chars.json")
    parser.add_argument("--out-ttf", required=True)
    parser.add_argument("--family-name", default="Write2Font")
    parser.add_argument("--potrace", default="potrace")
    parser.add_argument("--fontforge", default="fontforge")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_ttf = Path(args.out_ttf)
    chars = json.loads(Path(args.chars).read_text(encoding="utf-8"))
    out_ttf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="write2font-ttf-") as tmp:
        tmp_dir = Path(tmp)
        svg_dir = tmp_dir / "svg"
        glyphs = build_svgs(input_dir, chars, svg_dir, args.potrace)
        if not glyphs:
            raise RuntimeError(f"no generated glyph PNGs found in {input_dir}")

        manifest_path = tmp_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps({"family_name": safe_family_name(args.family_name), "glyphs": glyphs}, ensure_ascii=False),
            encoding="utf-8",
        )
        script_path = tmp_dir / "build_font.py"
        write_fontforge_script(script_path)
        subprocess.run([args.fontforge, "-script", str(script_path), str(manifest_path), str(out_ttf)], check=True)


if __name__ == "__main__":
    main()
