import argparse
import csv
import json
import os
import re
import statistics
import time
import xml.etree.ElementTree as ET

import fontforge
import psMat


SPACE_CODEPOINT = 0x0020
SVG_COMMAND_PATTERN = re.compile(r"[AaCcHhLlMmQqSsTtVvZz]")


PUNCTUATION_ADVANCES = {
    "!": 520,
    '"': 280,
    "#": 600,
    "$": 600,
    "%": 600,
    "&": 600,
    "'": 260,
    "(": 440,
    ")": 440,
    "*": 520,
    "+": 560,
    ",": 260,
    "-": 420,
    ".": 260,
    "/": 520,
    ":": 360,
    ";": 360,
    "<": 540,
    "=": 560,
    ">": 540,
    "?": 520,
    "@": 640,
    "[": 440,
    "\\": 520,
    "]": 440,
    "^": 520,
    "_": 420,
    "`": 260,
    "{": 440,
    "|": 360,
    "}": 440,
    "~": 420,
}


PUNCTUATION_GEOMETRY = {
    "!": (170, 620, 420),
    '"': (105, 170, 640),
    "#": (330, 430, 390),
    "$": (270, 540, 390),
    "%": (330, 440, 390),
    "&": (330, 440, 390),
    "'": (90, 170, 640),
    "(": (190, 650, 420),
    ")": (190, 650, 420),
    "*": (250, 270, 500),
    "+": (300, 300, 390),
    ",": (80, 135, 75),
    "-": (230, 60, 310),
    ".": (100, 105, 80),
    "/": (210, 620, 400),
    ":": (140, 470, 315),
    ";": (140, 500, 285),
    "<": (245, 430, 390),
    "=": (300, 210, 360),
    ">": (245, 430, 390),
    "?": (290, 590, 420),
    "@": (385, 420, 390),
    "[": (185, 660, 420),
    "\\": (210, 620, 400),
    "]": (185, 660, 420),
    "^": (245, 215, 570),
    "_": (240, 65, 95),
    "`": (90, 150, 640),
    "{": (190, 650, 420),
    "|": (70, 620, 400),
    "}": (190, 650, 420),
    "~": (235, 120, 355),
}


PUNCTUATION_ADVANCE_FACTOR = 0.92
PUNCTUATION_INK_FACTOR = 1.12
WIDTH_FACTOR = 0.94


def scaled_width(value):
    return int(round(value * WIDTH_FACTOR))


def punctuation_advance(char):
    return int(round(PUNCTUATION_ADVANCES.get(char, 540) * PUNCTUATION_ADVANCE_FACTOR))


def punctuation_geometry(char):
    target_width, target_height, target_center_y = PUNCTUATION_GEOMETRY[char]
    return (
        target_width * PUNCTUATION_INK_FACTOR,
        target_height * PUNCTUATION_INK_FACTOR,
        target_center_y,
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Build handwrite2350 TTF with FontForge")
    parser.add_argument("--charset", required=True)
    parser.add_argument("--svg-dir", required=True)
    parser.add_argument("--fonts-dir", required=True)
    parser.add_argument("--font-info", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--quality", choices=["fast", "high"], default="fast")
    parser.add_argument("--profile-import", action="store_true")
    parser.add_argument("--metrics-csv")
    parser.add_argument("--metrics-json")
    return parser.parse_args()


def load_charset(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read().replace("\r", "").replace("\n", "")


def load_font_info(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def glyph_width(codepoint):
    if codepoint == SPACE_CODEPOINT:
        return 450
    if 0x0021 <= codepoint <= 0x007E:
        char = chr(codepoint)
        if not char.isalnum():
            return punctuation_advance(char)
        if char == "I":
            return 480
        if char in "il":
            return 330
        if char == "1":
            return 560
        if char in "mwMW":
            return scaled_width(760)
        return scaled_width(660)
    return 940


def target_geometry(codepoint):
    advance = glyph_width(codepoint)
    char = chr(codepoint)

    if 0xAC00 <= codepoint <= 0xD7A3:
        return advance * 0.70, 760, 440
    if "A" <= char <= "Z":
        if char in "MW":
            return advance * 0.76, 700, 455
        if char == "I":
            return advance * 0.76, 700, 455
        return advance * 0.70, 700, 455
    if "0" <= char <= "9":
        if char == "1":
            return advance * 0.74, 670, 440
        return advance * 0.64, 660, 440
    if "a" <= char <= "z":
        if char in "il":
            return advance * 0.42, 650, 430
        if char in "mw":
            return advance * 0.74, 540, 360
        if char in "bdfhklt":
            return advance * 0.62, 680, 430
        if char in "gjpqy":
            return advance * 0.62, 680, 320
        return advance * 0.62, 540, 350
    if char in PUNCTUATION_GEOMETRY:
        return punctuation_geometry(char)
    if 0x0021 <= codepoint <= 0x007E:
        return advance * 0.50, 430, 370
    return advance * 0.70, 650, 430


def svg_path_for_codepoint(svg_dir, codepoint):
    return os.path.join(svg_dir, "uni%04X.svg" % codepoint)


def default_metrics_csv_path(report_path):
    return os.path.join(os.path.dirname(report_path), "font_import_metrics.csv")


def default_metrics_json_path(report_path):
    return os.path.join(os.path.dirname(report_path), "font_import_metrics_summary.json")


def timed_call(callback):
    start = time.perf_counter()
    value = callback()
    return value, time.perf_counter() - start


def analyze_svg(svg_path):
    result = {
        "svg_file_size_bytes": os.path.getsize(svg_path),
        "svg_path_element_count": 0,
        "svg_path_command_count": 0,
        "svg_d_attribute_length": 0,
    }

    try:
        root = ET.parse(svg_path).getroot()
    except Exception:
        return result

    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "path":
            continue
        result["svg_path_element_count"] += 1
        d_attribute = element.attrib.get("d", "")
        result["svg_d_attribute_length"] += len(d_attribute)
        result["svg_path_command_count"] += len(SVG_COMMAND_PATTERN.findall(d_attribute))

    return result


def append_sfnt_name(font, name_id, value):
    if not value:
        return
    try:
        font.appendSFNTName("English (US)", name_id, value)
    except Exception:
        pass


def apply_font_metadata(font, font_info):
    family_name = font_info.get("family_name", "Handwrite2350")
    style_name = font_info.get("style_name", "Regular")
    full_name = font_info.get("full_name", family_name + " " + style_name)
    postscript_name = font_info.get("postscript_name", "Handwrite2350-Regular")
    version = font_info.get("version", "Version 1.000")

    font.encoding = "UnicodeFull"
    font.em = 1000
    font.ascent = 880
    font.descent = 120
    font.familyname = family_name
    font.fullname = full_name
    font.fontname = postscript_name
    font.version = version
    font.copyright = font_info.get("copyright", "")

    append_sfnt_name(font, "Family", family_name)
    append_sfnt_name(font, "SubFamily", style_name)
    append_sfnt_name(font, "Fullname", full_name)
    append_sfnt_name(font, "PostScriptName", postscript_name)
    append_sfnt_name(font, "Version", version)
    append_sfnt_name(font, "Manufacturer", font_info.get("manufacturer", ""))
    append_sfnt_name(font, "Designer", font_info.get("designer", ""))
    append_sfnt_name(font, "Descriptor", font_info.get("description", ""))
    append_sfnt_name(font, "Copyright", font_info.get("copyright", ""))
    append_sfnt_name(font, "License", font_info.get("license", ""))


def create_space_glyph(font):
    glyph = font.createChar(SPACE_CODEPOINT)
    glyph.width = glyph_width(SPACE_CODEPOINT)
    return glyph


def import_glyph(font, codepoint, svg_path, quality):
    width = glyph_width(codepoint)
    geometry = target_geometry(codepoint)

    def create_glyph():
        glyph = font.createChar(codepoint)
        glyph.width = width
        return glyph

    glyph, create_time = timed_call(create_glyph)

    _, import_time = timed_call(lambda: glyph.importOutlines(svg_path))

    transform_time = 0.0
    cleanup_time = 0.0

    if quality == "high":
        _, correct_time = timed_call(glyph.correctDirection)
        _, overlap_time = timed_call(glyph.removeOverlap)
        cleanup_time += correct_time + overlap_time

    _, transform_time = timed_call(
        lambda: fit_glyph_to_font_box(glyph, codepoint, width, geometry)
    )

    _, set_width_time = timed_call(lambda: setattr(glyph, "width", width))
    transform_time += set_width_time

    return glyph, create_time, import_time, transform_time, cleanup_time


def fit_glyph_to_font_box(glyph, codepoint, advance_width=None, geometry=None):
    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return

    glyph_box_width = xmax - xmin
    glyph_box_height = ymax - ymin
    if glyph_box_width <= 0 or glyph_box_height <= 0:
        return

    advance_width = advance_width if advance_width is not None else glyph_width(codepoint)
    target_width, target_height, target_center_y = (
        geometry if geometry is not None else target_geometry(codepoint)
    )
    scale = min(target_width / glyph_box_width, target_height / glyph_box_height)
    if scale <= 0:
        return

    glyph.transform(psMat.translate(-xmin, -ymin))
    glyph.transform(psMat.scale(scale))

    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return

    glyph_center_x = (xmin + xmax) / 2.0
    glyph_center_y = (ymin + ymax) / 2.0
    x_offset = advance_width / 2.0 - glyph_center_x
    y_offset = target_center_y - glyph_center_y
    glyph.transform(psMat.translate(x_offset, y_offset))
    if codepoint == ord("I"):
        stretch_upper_i(glyph, target_center_y)


def stretch_upper_i(glyph, target_center_y):
    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return

    glyph_box_height = ymax - ymin
    if glyph_box_height <= 0 or glyph_box_height >= 600:
        return

    center_y = (ymin + ymax) / 2.0
    y_scale = min(600 / glyph_box_height, 1.85)
    glyph.transform(psMat.translate(0, -center_y))
    glyph.transform(psMat.scale(1.0, y_scale))
    glyph.transform(psMat.translate(0, center_y))

    try:
        xmin, ymin, xmax, ymax = glyph.boundingBox()
    except Exception:
        return

    glyph_center_y = (ymin + ymax) / 2.0
    glyph.transform(psMat.translate(0, target_center_y - glyph_center_y))


def fit_glyph_fast(glyph, codepoint):
    fit_glyph_to_font_box(glyph, codepoint)


def normalize_glyph_geometry(glyph, codepoint):
    fit_glyph_to_font_box(glyph, codepoint)


def write_report(path, lines):
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines) + "\n")


def percentile(values, percent):
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * percent / 100.0))
    return sorted_values[index]


def summarize_times(rows, key):
    values = [row[key] for row in rows if row.get("ok")]
    return {
        "total": sum(values),
        "average": statistics.mean(values) if values else 0.0,
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "max": max(values) if values else 0.0,
    }


def pearson_correlation(rows, x_key, y_key):
    pairs = [(row[x_key], row[y_key]) for row in rows if row.get("ok")]
    if len(pairs) < 2:
        return 0.0

    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    mean_x = statistics.mean(xs)
    mean_y = statistics.mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator_x = sum((x - mean_x) ** 2 for x in xs)
    denominator_y = sum((y - mean_y) ** 2 for y in ys)
    denominator = (denominator_x * denominator_y) ** 0.5
    return numerator / denominator if denominator else 0.0


def write_metrics_csv(path, rows):
    fieldnames = [
        "index",
        "unicode",
        "character",
        "svg_filepath",
        "svg_file_size_bytes",
        "svg_path_element_count",
        "svg_path_command_count",
        "svg_d_attribute_length",
        "glyph_create_time",
        "svg_import_outlines_time",
        "transform_time",
        "cleanup_time",
        "glyph_total_time",
        "ok",
        "error",
    ]
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)


def write_metrics_json(path, rows, timings, total_time):
    top_slowest = sorted(
        (row for row in rows if row.get("ok")),
        key=lambda row: row["glyph_total_time"],
        reverse=True,
    )[:20]
    summary = {
        "glyph_count": len(rows),
        "ok_glyph_count": sum(1 for row in rows if row.get("ok")),
        "failed_glyph_count": sum(1 for row in rows if not row.get("ok")),
        "font_object_create_time": timings["create font time"],
        "metadata_time": timings["metadata time"],
        "svg_analysis_time": timings["SVG analysis time"],
        "svg_import_total_time": timings["import SVG total time"],
        "transform_total_time": timings["transform time"],
        "cleanup_total_time": timings["glyph cleanup time"],
        "font_generate_time": timings["generate TTF time"],
        "font_build_total_time": total_time,
        "stats": {
            "glyph_create_time": summarize_times(rows, "glyph_create_time"),
            "svg_import_outlines_time": summarize_times(rows, "svg_import_outlines_time"),
            "transform_time": summarize_times(rows, "transform_time"),
            "cleanup_time": summarize_times(rows, "cleanup_time"),
            "glyph_total_time": summarize_times(rows, "glyph_total_time"),
        },
        "correlation": {
            "svg_file_size_vs_import_time": pearson_correlation(
                rows,
                "svg_file_size_bytes",
                "svg_import_outlines_time",
            ),
            "svg_path_command_count_vs_import_time": pearson_correlation(
                rows,
                "svg_path_command_count",
                "svg_import_outlines_time",
            ),
            "svg_d_attribute_length_vs_import_time": pearson_correlation(
                rows,
                "svg_d_attribute_length",
                "svg_import_outlines_time",
            ),
        },
        "top_20_slowest_glyphs": top_slowest,
    }
    with open(path, "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
    return summary


def main():
    args = parse_args()
    total_start = time.perf_counter()
    metrics_csv = args.metrics_csv or default_metrics_csv_path(args.report)
    metrics_json = args.metrics_json or default_metrics_json_path(args.report)
    timings = {
        "create font time": 0.0,
        "metadata time": 0.0,
        "SVG analysis time": 0.0,
        "import SVG total time": 0.0,
        "transform time": 0.0,
        "glyph cleanup time": 0.0,
        "generate TTF time": 0.0,
    }

    chars = load_charset(args.charset)
    font_info = load_font_info(args.font_info)
    os.makedirs(args.fonts_dir, exist_ok=True)

    start = time.time()
    font = fontforge.font()
    timings["create font time"] += time.time() - start

    start = time.time()
    apply_font_metadata(font, font_info)
    timings["metadata time"] += time.time() - start

    create_space_glyph(font)

    imported_count = 0
    missing = []
    failed = []
    metric_rows = [] if args.profile_import else None

    for index, char in enumerate(chars):
        codepoint = ord(char)
        svg_path = svg_path_for_codepoint(args.svg_dir, codepoint)
        row = None
        if args.profile_import:
            row = {
                "index": index,
                "unicode": "U+%04X" % codepoint,
                "character": char,
                "svg_filepath": svg_path,
                "glyph_create_time": 0.0,
                "svg_import_outlines_time": 0.0,
                "transform_time": 0.0,
                "cleanup_time": 0.0,
                "glyph_total_time": 0.0,
                "ok": False,
                "error": "",
            }

        if not os.path.exists(svg_path):
            missing.append("index=%d unicode=U+%04X file=%s" % (index, codepoint, svg_path))
            glyph = font.createChar(codepoint)
            glyph.width = glyph_width(codepoint)
            if args.profile_import:
                row.update(
                    {
                        "svg_file_size_bytes": 0,
                        "svg_path_element_count": 0,
                        "svg_path_command_count": 0,
                        "svg_d_attribute_length": 0,
                        "error": "missing SVG",
                    }
                )
                metric_rows.append(row)
            continue

        try:
            if args.profile_import:
                svg_metrics, svg_analysis_time = timed_call(lambda: analyze_svg(svg_path))
                row.update(svg_metrics)
                timings["SVG analysis time"] += svg_analysis_time
            glyph_start = time.perf_counter()
            _, create_time, import_time, transform_time, cleanup_time = import_glyph(
                font,
                codepoint,
                svg_path,
                args.quality,
            )
            glyph_total_time = time.perf_counter() - glyph_start
            if args.profile_import:
                row.update(
                    {
                        "glyph_create_time": create_time,
                        "svg_import_outlines_time": import_time,
                        "transform_time": transform_time,
                        "cleanup_time": cleanup_time,
                        "glyph_total_time": glyph_total_time,
                        "ok": True,
                    }
                )
            timings["import SVG total time"] += import_time
            timings["transform time"] += transform_time
            timings["glyph cleanup time"] += cleanup_time
            imported_count += 1
        except Exception as exc:
            if args.profile_import:
                row["error"] = f"{type(exc).__name__}: {exc}"
            failed.append(
                "index=%d unicode=U+%04X file=%s error=%s: %s"
                % (index, codepoint, svg_path, type(exc).__name__, exc)
            )
            glyph = font.createChar(codepoint)
            glyph.width = glyph_width(codepoint)
        if args.profile_import:
            metric_rows.append(row)

    output_path = os.path.join(
        args.fonts_dir,
        "%s.ttf" % font_info.get("postscript_name", "Handwrite2350-Regular"),
    )
    start = time.time()
    font.generate(output_path)
    timings["generate TTF time"] += time.time() - start
    font.close()
    total_time = time.perf_counter() - total_start
    metrics_summary = None
    if args.profile_import:
        write_metrics_csv(metrics_csv, metric_rows)
        metrics_summary = write_metrics_json(metrics_json, metric_rows, timings, total_time)

    problem_list = missing + failed
    lines = [
        "handwrite2350 font build report",
        "========================================",
        "total charset count: %d" % len(chars),
        "imported SVG count: %d" % imported_count,
        "missing SVG count: %d" % len(missing),
        "generated font path: %s" % output_path,
        "font quality: %s" % args.quality,
        "create font time: %.2fs" % timings["create font time"],
        "SVG analysis time: %.2fs" % timings["SVG analysis time"],
        "import SVG total time: %.2fs" % timings["import SVG total time"],
        "transform time: %.2fs" % timings["transform time"],
        "glyph cleanup time: %.2fs" % timings["glyph cleanup time"],
        "metadata time: %.2fs" % timings["metadata time"],
        "generate TTF time: %.2fs" % timings["generate TTF time"],
        "font build total time: %.2fs" % total_time,
        "failed glyph count: %d" % len(problem_list),
        "",
        "failed glyph list:",
    ]
    if metrics_summary is not None:
        failed_count_line = "failed glyph count: %d" % len(problem_list)
        insert_at = lines.index(failed_count_line)
        lines[insert_at:insert_at] = [
            "glyph metrics CSV: %s" % metrics_csv,
            "glyph metrics summary JSON: %s" % metrics_json,
            "glyph import p50: %.6fs" % metrics_summary["stats"]["svg_import_outlines_time"]["p50"],
            "glyph import p95: %.6fs" % metrics_summary["stats"]["svg_import_outlines_time"]["p95"],
            "glyph import max: %.6fs" % metrics_summary["stats"]["svg_import_outlines_time"]["max"],
            "SVG size/import correlation: %.4f" % metrics_summary["correlation"]["svg_file_size_vs_import_time"],
            "path command/import correlation: %.4f" % metrics_summary["correlation"]["svg_path_command_count_vs_import_time"],
        ]
    lines.extend(problem_list if problem_list else ["None"])
    write_report(args.report, lines)


if __name__ == "__main__":
    main()
