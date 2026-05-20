from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import csv
import os
from pathlib import Path
import subprocess
import time

import cv2
import numpy as np

from glyph_classify import classify_glyph
from glyph_layout import (
    DEFAULT_CONFIG_PATH as DEFAULT_GLYPH_LAYOUT_CONFIG_PATH,
    apply_adaptive_layout,
    compute_group_statistics,
    get_group_for_char,
    load_glyph_layout_config,
    resolve_layout_rule,
    write_glyph_layout_report,
)


CELLS_DIR = Path("outputs/cells")
OUTPUTS_DIR = Path(os.environ.get("HANDWRITE_OUTPUTS_DIR", "/app/outputs"))
SVG_DIR = OUTPUTS_DIR / "svg"
TMP_DIR = OUTPUTS_DIR / "tmp"
NORMALIZED_DIR = OUTPUTS_DIR / "normalized"
REPORT_PATH = OUTPUTS_DIR / "trace_report.txt"
GLYPH_METRICS_REPORT_PATH = OUTPUTS_DIR / "glyph_metrics_report.csv"
CHARSET_PATH = Path(os.environ.get("HANDWRITE_CHARSET_PATH", "charsets/basiclatin_ksx1001.txt"))

DEFAULT_GLYPH_SIZE = 512
DEFAULT_GLYPH_PADDING = 48
CELL_EXTENSIONS = {".png"}


PUNCTUATION_LAYOUTS = {
    "!": ("punct_exclam", 120, 330, 256, 255),
    '"': ("punct_double_quote", 74, 110, 256, 135),
    "#": ("punct_hash", 192, 270, 256, 265),
    "$": ("punct_dollar", 168, 330, 256, 260),
    "%": ("punct_percent", 200, 280, 256, 265),
    "&": ("punct_ampersand", 200, 280, 256, 265),
    "'": ("punct_quote", 52, 112, 256, 135),
    "(": ("punct_paren_left", 112, 340, 256, 270),
    ")": ("punct_paren_right", 112, 340, 256, 270),
    "*": ("punct_asterisk", 140, 140, 256, 215),
    "+": ("punct_plus", 168, 168, 256, 278),
    ",": ("punct_comma", 58, 112, 256, 382),
    "-": ("punct_hyphen", 168, 44, 256, 278),
    ".": ("punct_dot", 52, 56, 256, 376),
    "/": ("punct_slash", 126, 330, 256, 270),
    ":": ("punct_colon", 94, 255, 256, 280),
    ";": ("punct_semicolon", 94, 278, 256, 300),
    "<": ("punct_less", 170, 245, 256, 270),
    "=": ("punct_equal", 170, 126, 256, 282),
    ">": ("punct_greater", 170, 245, 256, 270),
    "?": ("punct_question", 142, 330, 256, 260),
    "@": ("punct_at", 220, 245, 256, 272),
    "[": ("punct_bracket_left", 105, 345, 256, 270),
    "\\": ("punct_backslash", 126, 330, 256, 270),
    "]": ("punct_bracket_right", 105, 345, 256, 270),
    "^": ("punct_caret", 126, 104, 256, 180),
    "_": ("punct_underscore", 180, 44, 256, 398),
    "`": ("punct_backtick", 62, 104, 256, 140),
    "{": ("punct_brace_left", 112, 345, 256, 270),
    "|": ("punct_bar", 58, 335, 256, 270),
    "}": ("punct_brace_right", 112, 345, 256, 270),
    "~": ("punct_tilde", 176, 88, 256, 260),
}


PUNCTUATION_SIZE_BOOST = 1.12


def boosted_punctuation_layout(layout):
    name, target_width, target_height, target_center_x, target_center_y = layout
    return (
        name,
        int(round(target_width * PUNCTUATION_SIZE_BOOST)),
        int(round(target_height * PUNCTUATION_SIZE_BOOST)),
        target_center_x,
        target_center_y,
    )


def layout_profile(char, group):
    if char in PUNCTUATION_LAYOUTS:
        return boosted_punctuation_layout(PUNCTUATION_LAYOUTS[char])
    if group == "hangul_syllable" or group.startswith("hangul_"):
        return "hangul", 326, 356, 256, 258
    if group in {"latin_upper", "latin_upper_q"}:
        return "latin_upper", 258, 350, 256, 260
    if group == "latin_upper_wide":
        return "latin_upper_wide", 292, 350, 256, 260
    if group == "latin_upper_narrow":
        return "latin_upper_i", 376, 360, 256, 260
    if group == "basic_latin_upper":
        if char in "MW":
            return "latin_upper_wide", 292, 350, 256, 260
        if char == "I":
            return "latin_upper_i", 376, 360, 256, 260
        return "latin_upper", 258, 350, 256, 260
    if group == "digit":
        return "latin_digit", 248, 332, 256, 265
    if group == "digit_one":
        return "latin_digit_one", 215, 344, 256, 265
    if group == "basic_latin_digit":
        if char == "1":
            return "latin_digit_one", 215, 344, 256, 265
        return "latin_digit", 248, 332, 256, 265
    if group == "latin_lower_ascender":
        return "latin_ascender", 234, 348, 256, 270
    if group == "latin_lower_descender":
        return "latin_descender", 238, 348, 256, 315
    if group == "latin_lower_narrow":
        return "latin_narrow", 112, 340, 256, 270
    if group == "latin_lower_t":
        return "latin_narrow", 112, 340, 256, 270
    if group == "latin_lower_j":
        return "latin_descender", 238, 348, 256, 315
    if group == "latin_lower_wide":
        return "latin_lower_wide", 286, 282, 256, 310
    if group in {"basic_latin_lower", "latin_lower_xheight"}:
        if char in "bdfhkl":
            if char in "il":
                return "latin_narrow", 112, 340, 256, 270
            return "latin_ascender", 234, 348, 256, 270
        if char in "gjpqy":
            return "latin_descender", 238, 348, 256, 315
        if char in "it":
            return "latin_narrow", 112, 340, 256, 270
        if char in "mw":
            return "latin_lower_wide", 286, 282, 256, 310
        return "latin_lower", 236, 282, 256, 310
    if group in {"punctuation", "symbol"}:
        return "symbol", 155, 210, 256, 265
    return "default", 230, 300, 256, 270


def parse_args():
    parser = argparse.ArgumentParser(description="Trace handwrite2350 cell PNGs to SVG")
    parser.add_argument("--cells-dir", default=str(CELLS_DIR))
    parser.add_argument("--charset", default=str(CHARSET_PATH))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--glyph-size", type=int, default=DEFAULT_GLYPH_SIZE)
    parser.add_argument("--glyph-padding", type=int, default=DEFAULT_GLYPH_PADDING)
    parser.add_argument("--save-normalized", action="store_true")
    parser.add_argument("--metrics-mode", choices=["full", "none"], default="full")
    parser.add_argument("--layout-mode", choices=["fixed", "adaptive"], default="fixed")
    parser.add_argument("--glyph-layout-config", default=str(DEFAULT_GLYPH_LAYOUT_CONFIG_PATH))
    parser.add_argument("--report-glyph-layout", action="store_true")
    return parser.parse_args()


def default_worker_count():
    cpu_count = os.cpu_count() or 1
    return max(1, cpu_count - 1)


def load_charset(path=CHARSET_PATH):
    return Path(path).read_text(encoding="utf-8").replace("\r", "").replace("\n", "")


def list_cell_images(cells_dir=CELLS_DIR):
    cells_path = Path(cells_dir)
    if not cells_path.exists():
        return []

    image_paths = []
    for page_dir in sorted(path for path in cells_path.iterdir() if path.is_dir()):
        image_paths.extend(
            sorted(
                path
                for path in page_dir.iterdir()
                if path.is_file() and path.suffix.lower() in CELL_EXTENSIONS
            )
        )
    return image_paths


def unicode_svg_path(char, svg_dir=SVG_DIR):
    return Path(svg_dir) / f"uni{ord(char):04X}.svg"


def unicode_normalized_path(char, normalized_dir=NORMALIZED_DIR):
    return Path(normalized_dir) / f"uni{ord(char):04X}.png"


def list_svg_files(svg_dir=SVG_DIR):
    path = Path(svg_dir)
    if not path.exists():
        return []
    return sorted(path.rglob("*.svg"))


def decode_cell_image(task):
    if "gray_bytes" in task:
        height, width = task["gray_shape"]
        image = np.frombuffer(task["gray_bytes"], dtype=np.uint8).reshape(
            int(height),
            int(width),
        )
        source = f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"
    elif "binary_bytes" in task:
        height, width = task["binary_shape"]
        image = np.frombuffer(task["binary_bytes"], dtype=np.uint8).reshape(
            int(height),
            int(width),
        )
        source = f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"
    elif "binary_png" in task:
        data = np.frombuffer(task["binary_png"], dtype=np.uint8)
        image = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE)
        source = f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"
    else:
        cell_path = Path(task["cell_path"])
        image = cv2.imread(str(cell_path), cv2.IMREAD_GRAYSCALE)
        source = str(cell_path)

    if image is None:
        raise ValueError(f"failed to read cell image: {source}")
    return image, source


def threshold_for_bbox(gray):
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    black_pixels = np.count_nonzero(binary == 0)
    white_pixels = np.count_nonzero(binary == 255)
    if black_pixels > white_pixels:
        gray = cv2.bitwise_not(gray)
        binary = cv2.bitwise_not(binary)
    return gray, binary


def threshold_final(gray):
    if min(gray.shape[:2]) >= 3:
        gray = cv2.GaussianBlur(gray, (3, 3), 0.35)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    black_pixels = np.count_nonzero(binary == 0)
    white_pixels = np.count_nonzero(binary == 255)
    if black_pixels > white_pixels:
        binary = cv2.bitwise_not(binary)
    return binary


def measure_glyph_bitmap(image, char, source):
    gray, binary_for_bbox = threshold_for_bbox(image)

    ys, xs = np.where(binary_for_bbox == 0)
    if len(xs) == 0 or len(ys) == 0:
        raise ValueError(f"empty glyph bitmap after threshold: {source}")

    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    bbox_width = x1 - x0
    bbox_height = y1 - y0
    center_x = x0 + bbox_width / 2.0
    center_y = y0 + bbox_height / 2.0
    group = classify_glyph(char)

    return {
        "group": group,
        "bbox_x0": x0,
        "bbox_y0": y0,
        "bbox_x1": x1,
        "bbox_y1": y1,
        "bbox_width": bbox_width,
        "bbox_height": bbox_height,
        "bbox_max": max(bbox_width, bbox_height),
        "center_x": center_x,
        "center_y": center_y,
        "source_width": int(gray.shape[1]),
        "source_height": int(gray.shape[0]),
    }


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def glyph_crop_with_padding(gray, metrics):
    x0 = metrics["bbox_x0"]
    x1 = metrics["bbox_x1"]
    y0 = metrics["bbox_y0"]
    y1 = metrics["bbox_y1"]
    pad = max(3, int(round(max(metrics["bbox_width"], metrics["bbox_height"]) * 0.06)))
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(gray.shape[1], x1 + pad)
    y1 = min(gray.shape[0], y1 + pad)
    return gray[y0:y1, x0:x1], x0, y0


def calculate_layout_scale(
    metrics,
    target_width,
    target_height,
    target_size,
    glyph_size,
    crop_width,
    crop_height,
):
    width = max(1, metrics["bbox_width"])
    height = max(1, metrics["bbox_height"])
    scale = min(target_width / width, target_height / height)
    return min(
        scale,
        target_size / width,
        target_size / height,
        glyph_size / crop_width,
        glyph_size / crop_height,
    )


def normalize_cell_bitmap(image, char, glyph_size, glyph_padding, source, metrics=None):
    gray, _ = threshold_for_bbox(image)
    metrics = metrics or measure_glyph_bitmap(gray, char, source)

    target_size = glyph_size - glyph_padding * 2
    if target_size <= 0:
        raise ValueError(
            f"glyph padding is too large for glyph size: size={glyph_size}, padding={glyph_padding}"
        )

    if all(
        key in metrics
        for key in [
            "layout",
            "target_width",
            "target_height",
            "target_center_x",
            "target_center_y",
        ]
    ):
        layout = metrics["layout"]
        target_width = metrics["target_width"]
        target_height = metrics["target_height"]
        target_center_x = metrics["target_center_x"]
        target_center_y = metrics["target_center_y"]
    else:
        layout, target_width, target_height, target_center_x, target_center_y = layout_profile(
            char,
            metrics["group"],
        )
    crop, crop_x0, crop_y0 = glyph_crop_with_padding(gray, metrics)
    crop_height, crop_width = crop.shape
    scale = calculate_layout_scale(
        metrics,
        target_width,
        target_height,
        target_size,
        glyph_size,
        crop_width,
        crop_height,
    )
    bbox_center_in_crop_x = metrics["center_x"] - crop_x0
    bbox_center_in_crop_y = metrics["center_y"] - crop_y0

    metrics["scale"] = float(scale)
    metrics["scale_adjustment"] = float(scale)
    metrics["target_width"] = target_width
    metrics["target_height"] = target_height
    metrics["target_center_x"] = target_center_x
    metrics["target_center_y"] = target_center_y
    metrics["layout"] = layout

    new_width = max(1, int(round(crop_width * scale)))
    new_height = max(1, int(round(crop_height * scale)))

    interpolation = cv2.INTER_LANCZOS4 if scale >= 1.0 else cv2.INTER_AREA
    resized = cv2.resize(crop, (new_width, new_height), interpolation=interpolation)
    resized = threshold_final(resized)

    canvas = np.full((glyph_size, glyph_size), 255, dtype=np.uint8)
    x_offset = int(round(target_center_x - bbox_center_in_crop_x * scale))
    y_offset = int(round(target_center_y - bbox_center_in_crop_y * scale))
    x_offset = int(clamp(x_offset, 0, glyph_size - new_width))
    y_offset = int(clamp(y_offset, 0, glyph_size - new_height))
    actual_center_x = x_offset + bbox_center_in_crop_x * scale
    actual_center_y = y_offset + bbox_center_in_crop_y * scale
    dx = int(round(actual_center_x - metrics["center_x"]))
    dy = int(round(actual_center_y - metrics["center_y"]))
    metrics["dx"] = dx
    metrics["dy"] = dy
    metrics["correction_applied"] = True
    metrics["scale_adjusted"] = True
    metrics["position_adjusted"] = (
        abs(actual_center_x - metrics["center_x"]) > 1
        or abs(actual_center_y - metrics["center_y"]) > 1
    )
    canvas[y_offset : y_offset + new_height, x_offset : x_offset + new_width] = resized

    return canvas


def make_pbm_bytes(binary_image):
    black_mask = binary_image == 0
    height, width = black_mask.shape
    header = f"P4\n{width} {height}\n".encode("ascii")
    packed = np.packbits(black_mask.astype(np.uint8), axis=1, bitorder="big")
    return header + packed.tobytes()


def trace_glyph_task(task):
    index = task["index"]
    char = task["char"]
    codepoint = ord(char)
    svg_path = Path(task["svg_dir"]) / f"uni{codepoint:04X}.svg"

    try:
        image, source = decode_cell_image(task)
        normalized = normalize_cell_bitmap(
            image,
            char,
            task["glyph_size"],
            task["glyph_padding"],
            source,
            task.get("metrics"),
        )
        if task["save_normalized"]:
            normalized_path = Path(task["normalized_dir"]) / f"uni{codepoint:04X}.png"
            if not cv2.imwrite(str(normalized_path), normalized):
                raise ValueError(f"failed to write normalized glyph: {normalized_path}")

        result = subprocess.run(
            ["potrace", "-", "-s", "-o", "-"],
            input=make_pbm_bytes(normalized),
            check=True,
            capture_output=True,
            text=False,
        )
        svg_path.write_bytes(result.stdout)
        metrics = task.get("metrics", {})
        return {
            "ok": True,
            "index": index,
            "svg_path": str(svg_path),
            "scale": metrics.get("scale", ""),
            "scale_adjustment": metrics.get("scale_adjustment", ""),
            "dx": metrics.get("dx", ""),
            "dy": metrics.get("dy", ""),
            "target_width": metrics.get("target_width", ""),
            "target_height": metrics.get("target_height", ""),
            "target_center_x": metrics.get("target_center_x", ""),
            "target_center_y": metrics.get("target_center_y", ""),
            "layout": metrics.get("layout", ""),
            "correction_applied": metrics.get("correction_applied", ""),
            "scale_adjusted": metrics.get("scale_adjusted", ""),
            "position_adjusted": metrics.get("position_adjusted", ""),
        }
    except Exception as exc:
        return {
            "ok": False,
            "index": index,
            "file": task.get("cell_path", f"{task.get('page', 'memory')} r{task.get('row', -1):02d}_c{task.get('col', -1):02d}"),
            "char": char,
            "unicode": f"U+{codepoint:04X}",
            "error": f"{type(exc).__name__}: {exc}",
        }


def cleanup_empty_tmp_dir():
    if TMP_DIR.exists() and not any(TMP_DIR.iterdir()):
        TMP_DIR.rmdir()


def clear_output_dirs(save_normalized, svg_dir=SVG_DIR):
    svg_dir = Path(svg_dir)
    svg_dir.mkdir(parents=True, exist_ok=True)
    for old_svg in list_svg_files(svg_dir):
        old_svg.unlink()
    if TMP_DIR.exists():
        for old_pbm in TMP_DIR.glob("*.pbm"):
            old_pbm.unlink()

    if save_normalized:
        NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
        for old_png in NORMALIZED_DIR.rglob("*.png"):
            old_png.unlink()


def median(values):
    sorted_values = sorted(values)
    count = len(sorted_values)
    if count == 0:
        return 0.0
    middle = count // 2
    if count % 2:
        return float(sorted_values[middle])
    return (sorted_values[middle - 1] + sorted_values[middle]) / 2.0


def calculate_group_medians(metrics_rows):
    grouped = {}
    for row in metrics_rows:
        if not row.get("ok"):
            continue
        grouped.setdefault(row["group"], []).append(row)

    return {
        group: {
            "bbox_width": median([row["bbox_width"] for row in rows]),
            "bbox_height": median([row["bbox_height"] for row in rows]),
            "bbox_max": median([row["bbox_max"] for row in rows]),
            "center_x": median([row["center_x"] for row in rows]),
            "center_y": median([row["center_y"] for row in rows]),
        }
        for group, rows in grouped.items()
    }


def measure_trace_metrics(tasks, layout_config=None):
    metrics_rows = []
    metrics_by_index = {}

    for task in tasks:
        index = task["index"]
        char = task["char"]
        row = {
            "index": index,
            "char": char,
            "unicode": f"U+{ord(char):04X}",
            "group": get_group_for_char(char, layout_config) if layout_config else classify_glyph(char),
            "page": task.get("page", ""),
            "row": task.get("row", ""),
            "col": task.get("col", ""),
            "ok": False,
            "error": "",
        }
        try:
            image, source = decode_cell_image(task)
            row.update(measure_glyph_bitmap(image, char, source))
            row["ok"] = True
            metrics_by_index[index] = {
                key: row[key]
                for key in [
                    "group",
                    "bbox_x0",
                    "bbox_y0",
                    "bbox_x1",
                    "bbox_y1",
                    "bbox_width",
                    "bbox_height",
                    "bbox_max",
                    "center_x",
                    "center_y",
                    "source_width",
                    "source_height",
                ]
            }
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        metrics_rows.append(row)

    group_medians = calculate_group_medians(metrics_rows)

    for row in metrics_rows:
        medians = group_medians.get(row["group"], {})
        row["group_median_bbox_width"] = medians.get("bbox_width", "")
        row["group_median_bbox_height"] = medians.get("bbox_height", "")
        row["group_median_bbox_max"] = medians.get("bbox_max", "")
        row["group_median_center_x"] = medians.get("center_x", "")
        row["group_median_center_y"] = medians.get("center_y", "")
        row["scale"] = ""
        row["scale_adjustment"] = ""
        row["dx"] = ""
        row["dy"] = ""
        row["target_width"] = ""
        row["target_height"] = ""
        row["target_center_x"] = ""
        row["target_center_y"] = ""
        row["layout"] = ""
        row["correction_applied"] = ""
        row["scale_adjusted"] = ""
        row["position_adjusted"] = ""

    for metrics in metrics_by_index.values():
        medians = group_medians.get(metrics["group"], {})
        metrics["group_median_bbox_width"] = medians.get("bbox_width", metrics["bbox_width"])
        metrics["group_median_bbox_height"] = medians.get("bbox_height", metrics["bbox_height"])
        metrics["group_median_bbox_max"] = medians.get("bbox_max", metrics["bbox_max"])
        metrics["group_median_center_x"] = medians.get("center_x", metrics["center_x"])
        metrics["group_median_center_y"] = medians.get("center_y", metrics["center_y"])

    return metrics_rows, metrics_by_index


def measure_required_bbox_metrics(tasks, layout_config=None):
    metrics_rows = []
    metrics_by_index = {}

    for task in tasks:
        index = task["index"]
        char = task["char"]
        row = {
            "index": index,
            "char": char,
            "unicode": f"U+{ord(char):04X}",
            "group": get_group_for_char(char, layout_config) if layout_config else classify_glyph(char),
            "page": task.get("page", ""),
            "row": task.get("row", ""),
            "col": task.get("col", ""),
            "ok": False,
            "error": "",
        }
        try:
            image, source = decode_cell_image(task)
            row.update(measure_glyph_bitmap(
                image,
                char,
                source,
            ))
            row["group"] = get_group_for_char(char, layout_config) if layout_config else row["group"]
            row["ok"] = True
            metrics_by_index[index] = {
                key: row[key]
                for key in [
                    "group",
                    "bbox_x0",
                    "bbox_y0",
                    "bbox_x1",
                    "bbox_y1",
                    "bbox_width",
                    "bbox_height",
                    "bbox_max",
                    "center_x",
                    "center_y",
                    "source_width",
                    "source_height",
                ]
            }
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        metrics_rows.append(row)

    return metrics_rows, metrics_by_index


def attach_adaptive_layouts(metrics_rows, metrics_by_index, layout_config):
    group_stats = compute_group_statistics(metrics_rows)
    rows_by_index = {row["index"]: row for row in metrics_rows}

    for index, metrics in metrics_by_index.items():
        char = rows_by_index.get(index, {}).get("char")
        if not char:
            continue
        group = get_group_for_char(char, layout_config)
        metrics["group"] = group
        rule = resolve_layout_rule(char, group, layout_config)
        adaptive = apply_adaptive_layout(metrics, group_stats, rule)
        metrics.update(adaptive)

        row = rows_by_index.get(index)
        if row is not None:
            row["group"] = group
            row.update(adaptive)

    return group_stats


def update_metrics_report_rows(metrics_rows, task_results):
    by_index = {row["index"]: row for row in metrics_rows}
    for result in task_results:
        row = by_index.get(result["index"])
        if row is None:
            continue
        if result.get("ok"):
            row["scale"] = result.get("scale", "")
            row["scale_adjustment"] = result.get("scale_adjustment", "")
            row["dx"] = result.get("dx", "")
            row["dy"] = result.get("dy", "")
            row["target_width"] = result.get("target_width", "")
            row["target_height"] = result.get("target_height", "")
            row["target_center_x"] = result.get("target_center_x", "")
            row["target_center_y"] = result.get("target_center_y", "")
            row["layout"] = result.get("layout", "")
            row["correction_applied"] = result.get("correction_applied", "")
            row["scale_adjusted"] = result.get("scale_adjusted", "")
            row["position_adjusted"] = result.get("position_adjusted", "")


def write_glyph_metrics_report(rows, path=GLYPH_METRICS_REPORT_PATH):
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "index",
        "char",
        "unicode",
        "group",
        "ok",
        "bbox_x0",
        "bbox_y0",
        "bbox_x1",
        "bbox_y1",
        "bbox_width",
        "bbox_height",
        "bbox_max",
        "center_x",
        "center_y",
        "source_width",
        "source_height",
        "group_median_bbox_width",
        "group_median_bbox_height",
        "group_median_bbox_max",
        "group_median_center_x",
        "group_median_center_y",
        "correction_applied",
        "scale_adjusted",
        "position_adjusted",
        "scale",
        "scale_adjustment",
        "dx",
        "dy",
        "target_width",
        "target_height",
        "target_center_x",
        "target_center_y",
        "layout",
        "error",
    ]
    with report_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fieldnames} for row in rows)


def run_trace(
    cells_dir=CELLS_DIR,
    charset_path=CHARSET_PATH,
    cell_records=None,
    workers=None,
    glyph_size=DEFAULT_GLYPH_SIZE,
    glyph_padding=DEFAULT_GLYPH_PADDING,
    save_normalized=False,
    svg_dir=SVG_DIR,
    metrics_mode="full",
    layout_mode="fixed",
    glyph_layout_config_path=DEFAULT_GLYPH_LAYOUT_CONFIG_PATH,
    report_glyph_layout=False,
):
    start = time.perf_counter()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if metrics_mode not in {"full", "none"}:
        raise ValueError(f"unsupported metrics_mode: {metrics_mode}")
    if layout_mode not in {"fixed", "adaptive"}:
        raise ValueError(f"unsupported layout_mode: {layout_mode}")
    if metrics_mode == "none" and GLYPH_METRICS_REPORT_PATH.exists():
        GLYPH_METRICS_REPORT_PATH.unlink()
    layout_config = (
        load_glyph_layout_config(glyph_layout_config_path)
        if layout_mode == "adaptive"
        else None
    )

    chars = load_charset(charset_path)
    direct_trace_mode = cell_records is not None
    cell_paths = [] if direct_trace_mode else list_cell_images(cells_dir)
    records = sorted(cell_records or [], key=lambda item: item["index"])
    input_mode = (
        "grayscale crop, resize, final threshold"
        if direct_trace_mode and records and "gray_bytes" in records[0]
        else "binary crop"
        if direct_trace_mode
        else "cell image file"
    )
    worker_count = max(1, int(workers)) if workers else default_worker_count()
    input_count = len(records) if direct_trace_mode else len(cell_paths)
    target_count = min(len(chars), input_count)
    failures = []
    success_count = 0

    if glyph_size <= 0:
        raise ValueError(f"glyph_size must be positive: {glyph_size}")
    if glyph_padding < 0 or glyph_padding * 2 >= glyph_size:
        raise ValueError(
            f"glyph_padding must fit inside glyph_size: size={glyph_size}, padding={glyph_padding}"
        )

    if input_count == 0:
        report = "No cell input found. Skipped SVG tracing.\n"
        REPORT_PATH.write_text(report, encoding="utf-8")
        if metrics_mode == "full":
            write_glyph_metrics_report([])
        print(report, end="")
        return True

    svg_dir = Path(svg_dir)
    clear_output_dirs(save_normalized, svg_dir)

    tasks = []
    for order_index in range(target_count):
        glyph_index = records[order_index]["index"] if direct_trace_mode else order_index
        task = {
            "index": glyph_index,
            "char": chars[glyph_index],
            "svg_dir": str(svg_dir),
            "normalized_dir": str(NORMALIZED_DIR),
            "glyph_size": glyph_size,
            "glyph_padding": glyph_padding,
            "save_normalized": save_normalized,
        }
        if direct_trace_mode:
            record = records[order_index]
            task.update(
                {
                    "page": record["page"],
                    "row": record["row"],
                    "col": record["col"],
                }
            )
            if "gray_bytes" in record:
                task.update(
                    {
                        "gray_bytes": record["gray_bytes"],
                        "gray_shape": record["gray_shape"],
                    }
                )
            else:
                task.update(
                    {
                        "binary_bytes": record["binary_bytes"],
                        "binary_shape": record["binary_shape"],
                    }
                )
        else:
            task["cell_path"] = str(cell_paths[order_index])
        tasks.append(task)

    metrics_rows = []
    group_stats = {}
    if metrics_mode == "full":
        metrics_rows, metrics_by_index = measure_trace_metrics(tasks, layout_config)
    else:
        metrics_rows, metrics_by_index = measure_required_bbox_metrics(tasks, layout_config)
    if layout_mode == "adaptive":
        group_stats = attach_adaptive_layouts(metrics_rows, metrics_by_index, layout_config)
    for task in tasks:
        metrics = metrics_by_index.get(task["index"])
        if metrics is not None:
            task["metrics"] = metrics

    task_results = []
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(trace_glyph_task, task) for task in tasks]
        for future in as_completed(futures):
            result = future.result()
            task_results.append(result)
            if result["ok"]:
                success_count += 1
            else:
                failures.append(
                    "index={index} file={file} char={char} unicode={unicode} error={error}".format(
                        **result
                    )
                )

    if input_count < len(chars):
        for index in range(input_count, len(chars)):
            char = chars[index]
            if metrics_mode == "full":
                metrics_rows.append(
                    {
                        "index": index,
                        "char": char,
                        "unicode": f"U+{ord(char):04X}",
                        "group": classify_glyph(char),
                        "ok": False,
                        "error": "missing cell input",
                    }
                )
            failures.append(
                f"index={index} file=<missing> char={char} "
                f"unicode=U+{ord(char):04X} error=missing cell input"
            )

    if input_count > len(chars):
        failures.append(f"extra cell inputs ignored: {input_count - len(chars)}")

    if metrics_mode == "full":
        update_metrics_report_rows(metrics_rows, task_results)
        write_glyph_metrics_report(metrics_rows)

    layout_report_result = None
    if report_glyph_layout:
        layout_report_result = write_glyph_layout_report(metrics_rows, group_stats)
    adjusted_count = sum(
        1 for result in task_results if result.get("ok") and result.get("correction_applied")
    )
    scale_adjusted_count = sum(
        1 for result in task_results if result.get("ok") and result.get("scale_adjusted")
    )
    position_adjusted_count = sum(
        1 for result in task_results if result.get("ok") and result.get("position_adjusted")
    )

    cleanup_empty_tmp_dir()
    elapsed = time.perf_counter() - start
    normalized_count = (
        len(list(NORMALIZED_DIR.rglob("*.png")))
        if save_normalized and NORMALIZED_DIR.exists()
        else 0
    )

    lines = [
        "handwrite2350 SVG trace report",
        "=" * 40,
        f"total glyph count: {len(chars)}",
        f"cell inputs found: {input_count}",
        f"direct trace mode: {direct_trace_mode}",
        f"input mode: {input_mode}",
        f"success count: {success_count}",
        f"failed count: {len(failures)}",
        f"adjusted glyph count: {adjusted_count}",
        f"scale adjusted count: {scale_adjusted_count}",
        f"position adjusted count: {position_adjusted_count}",
        f"worker count: {worker_count}",
        f"glyph size: {glyph_size}",
        f"glyph padding: {glyph_padding}",
        f"save_normalized: {save_normalized}",
        f"trace metrics: {metrics_mode}",
        f"layout mode: {layout_mode}",
        f"glyph layout config: {glyph_layout_config_path if layout_mode == 'adaptive' else 'not used'}",
        f"normalized PNG count: {normalized_count}",
        f"SVG files in {svg_dir}: {len(list_svg_files(svg_dir))}",
        f"elapsed time: {elapsed:.2f}s",
    ]
    if layout_report_result:
        lines.extend(
            [
                f"glyph layout report: {layout_report_result['report_path']}",
                f"glyph layout summary: {layout_report_result['summary_path']}",
                f"layout outlier glyph count: {layout_report_result['outlier_count']}",
                f"layout correction applied count: {layout_report_result['correction_count']}",
            ]
        )
    lines.extend(
        [
            "",
            "failed glyph list:",
        ]
    )
    lines.extend(sorted(failures) if failures else ["None"])

    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")
    return success_count == len(chars) and not failures


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(
        0
        if run_trace(
            args.cells_dir,
            args.charset,
            workers=args.workers,
            glyph_size=args.glyph_size,
            glyph_padding=args.glyph_padding,
            save_normalized=args.save_normalized,
            svg_dir=SVG_DIR,
            metrics_mode=args.metrics_mode,
            layout_mode=args.layout_mode,
            glyph_layout_config_path=args.glyph_layout_config,
            report_glyph_layout=args.report_glyph_layout,
        )
        else 1
    )
