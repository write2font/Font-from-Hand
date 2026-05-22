from __future__ import annotations

import hashlib
import re
from pathlib import Path

from fontTools.ttLib import TTFont


def safe_family_name(value: str) -> str:
    keep = [ch for ch in value if ch.isalnum() or ch in (" ", "-", "_")]
    return "".join(keep).strip() or "Write2Font"


def ascii_name(value: str, fallback_prefix: str = "Write2Font") -> str:
    keep = re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-")
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    if keep and any(ord(ch) > 127 for ch in value):
        return f"{keep[:39]}-{digest}"
    if keep:
        return keep[:48]
    return f"{fallback_prefix}-{digest}"


def split_family_and_style(family_name: str) -> tuple[str, str, int]:
    normalized = family_name.lower().strip()
    for suffix in ("-bold", "_bold", " bold", "bold"):
        if normalized.endswith(suffix):
            return family_name[: -len(suffix)].strip(" -_") or family_name, "Bold", 700
    for suffix in ("-regular", "_regular", " regular", "regular"):
        if normalized.endswith(suffix):
            return family_name[: -len(suffix)].strip(" -_") or family_name, "Regular", 400
    return family_name, "Regular", 400


def repair_ttf_metadata(ttf_path: Path, family_name: str) -> None:
    family_name = safe_family_name(family_name)
    family_name, style_name, weight = split_family_and_style(family_name)
    full_name = family_name if style_name == "Regular" else f"{family_name} {style_name}"
    ascii_family = ascii_name(family_name)
    ascii_full = ascii_family if style_name == "Regular" else f"{ascii_family}-{style_name}"
    postscript_name = f"{ascii_family}-{style_name}"
    version = "Version 1.000"
    unique_id = f"{version};{postscript_name}"

    font = TTFont(ttf_path)
    name_table = font["name"]
    replace_ids = {1, 2, 3, 4, 5, 6, 16, 17}
    name_table.names = [record for record in name_table.names if record.nameID not in replace_ids]

    for lang_id in (0x0409, 0x0412):
        name_table.setName(family_name, 1, 3, 1, lang_id)
        name_table.setName(style_name, 2, 3, 1, lang_id)
        name_table.setName(unique_id, 3, 3, 1, lang_id)
        name_table.setName(full_name, 4, 3, 1, lang_id)
        name_table.setName(version, 5, 3, 1, lang_id)
        name_table.setName(postscript_name, 6, 3, 1, lang_id)
        name_table.setName(family_name, 16, 3, 1, lang_id)
        name_table.setName(style_name, 17, 3, 1, lang_id)

    # Macintosh platform names are MacRoman, so keep them ASCII-only.
    for name_id, value in (
        (1, ascii_family),
        (2, style_name),
        (3, unique_id),
        (4, ascii_full),
        (5, version),
        (6, postscript_name),
        (16, ascii_family),
        (17, style_name),
    ):
        name_table.setName(value, name_id, 1, 0, 0)

    os2 = font.get("OS/2")
    if os2 is not None:
        os2.usWeightClass = weight
        os2.usWidthClass = 5
        os2.fsSelection &= ~((1 << 5) | (1 << 6))
        os2.fsSelection |= 1 << 7  # Use typo metrics
        os2.fsSelection |= 1 << 5 if style_name == "Bold" else 1 << 6
        if hasattr(os2, "ulCodePageRange1"):
            os2.ulCodePageRange1 |= (1 << 19) | (1 << 21)  # Korean Wansung/Johab
        os2.ulUnicodeRange2 |= 1 << (56 - 32)  # Hangul Syllables
        os2.sTypoAscender = 820
        os2.sTypoDescender = -180
        os2.sTypoLineGap = 90
        os2.usWinAscent = max(getattr(os2, "usWinAscent", 0), 958)
        os2.usWinDescent = max(getattr(os2, "usWinDescent", 0), 180)

    head = font.get("head")
    if head is not None:
        head.macStyle &= ~1
        if style_name == "Bold":
            head.macStyle |= 1

    hhea = font.get("hhea")
    if hhea is not None:
        hhea.ascent = 820
        hhea.descent = -180
        hhea.lineGap = 90

    font.save(ttf_path)
