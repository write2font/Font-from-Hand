import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


OUTPUTS_DIR = Path(os.environ.get("HANDWRITE_OUTPUTS_DIR", "/app/outputs"))
OUTPUT_PATH = OUTPUTS_DIR / "env_check.txt"
MAPPING_OUTPUT_PATH = OUTPUTS_DIR / "mapping_sample.txt"
CHARSET_PATH = Path(os.environ.get("HANDWRITE_CHARSET_PATH", "charsets/basiclatin_ksx1001.txt"))
INPUT_DIR = Path(os.environ.get("HANDWRITE_INPUT_DIR", "samples/input"))
WARPED_DIR = OUTPUTS_DIR / "warped"
CELLS_DIR = OUTPUTS_DIR / "cells"
SVG_DIR = OUTPUTS_DIR / "svg"
GLYPH_LAYOUT_CONFIG_PATH = Path("config/glyph_layout.json")
FONT_INFO_CONFIG_PATH = Path("config/font_info.json")
FONT_INFO_PREVIEW_PATH = OUTPUTS_DIR / "font_info_preview.txt"
PERFORMANCE_REPORT_PATH = OUTPUTS_DIR / "performance_report.txt"

COLS = 11
ROWS = 17
CELLS_PER_PAGE = COLS * ROWS
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
DEFAULT_FAMILY_NAME = "Handwrite2350"
DEFAULT_DESIGNER = ""


def configure_output_encoding():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def list_images(path):
    image_dir = Path(path)
    if not image_dir.exists():
        return []

    return sorted(
        item
        for item in image_dir.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )


def has_cell_images(path):
    cells_dir = Path(path)
    return cells_dir.exists() and any(
        item.is_file() and item.suffix.lower() in {".png", ".jpg", ".jpeg"}
        for item in cells_dir.rglob("*")
    )


def has_warped_png(path):
    warped_dir = Path(path)
    return warped_dir.exists() and any(warped_dir.glob("*.png"))


def parse_args():
    parser = argparse.ArgumentParser(description="handwrite2350 font engine")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--family-name", dest="family_name")
    parser.add_argument("--designer", dest="designer")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--glyph-size", type=int, default=512)
    parser.add_argument("--glyph-padding", type=int, default=48)
    parser.add_argument(
        "--font-quality",
        choices=["fast", "high"],
        default="fast",
        help="FontForge glyph cleanup mode. fast is the default for service speed.",
    )
    parser.add_argument("--save-normalized", action="store_true")
    parser.add_argument("--save-debug-artifacts", action="store_true")
    parser.add_argument("--export-svg-artifacts", action="store_true")
    parser.add_argument("--check-env", action="store_true")
    parser.add_argument("--cell-margin", type=float, default=0.08)
    parser.add_argument("--warp-interpolation", choices=["cubic", "linear"])
    parser.add_argument("--layout-mode", choices=["fixed", "adaptive"], default="fixed")
    parser.add_argument("--glyph-layout-config", default=str(GLYPH_LAYOUT_CONFIG_PATH))
    parser.add_argument("--report-glyph-layout", action="store_true")
    return parser.parse_args()


def resolve_warp_interpolation(args):
    if args.warp_interpolation:
        return args.warp_interpolation
    if args.fast:
        return "linear"
    return "cubic"


def load_font_info_config(path=FONT_INFO_CONFIG_PATH):
    if not Path(path).exists():
        return {}

    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"font info config must be a JSON object: {path}")

    return data


def sanitize_postscript_name(value):
    sanitized = re.sub(r"[^A-Za-z0-9-]", "", value)
    return sanitized or "Handwrite2350-Regular"


def build_font_info(family_name=DEFAULT_FAMILY_NAME, designer=DEFAULT_DESIGNER):
    family_name = (family_name or DEFAULT_FAMILY_NAME).strip() or DEFAULT_FAMILY_NAME
    designer = (designer or DEFAULT_DESIGNER).strip()
    style_name = "Regular"

    return {
        "family_name": family_name,
        "designer": designer,
        "style_name": style_name,
        "full_name": f"{family_name} {style_name}",
        "postscript_name": sanitize_postscript_name(f"{family_name}-{style_name}"),
        "version": "Version 1.000",
        "manufacturer": "handwrite2350",
        "description": (
            "Handwritten font based on 94 Basic Latin and 2,350 KS X 1001 "
            "Hangul glyphs."
        ),
        "copyright": (
            f"Copyright \u00A9 {designer}. All rights reserved." if designer else ""
        ),
        "license": "",
    }


def prompt_font_info(default_family_name, default_designer):
    family_prompt = f"Font family name [{default_family_name}]: "
    designer_prompt = "Designer name [optional]: "

    family_name = input(family_prompt).strip() or default_family_name
    designer = input(designer_prompt).strip() or default_designer
    return family_name, designer


def resolve_font_info(args):
    family_name = DEFAULT_FAMILY_NAME
    designer = DEFAULT_DESIGNER

    if args.family_name is not None or args.designer is not None:
        family_name = args.family_name if args.family_name is not None else family_name
        designer = args.designer if args.designer is not None else designer
    elif not args.interactive:
        config = load_font_info_config(FONT_INFO_CONFIG_PATH)
        family_name = config.get("family_name", family_name)
        designer = config.get("designer", designer)

    if args.interactive:
        family_name, designer = prompt_font_info(family_name, designer)

    return build_font_info(family_name, designer)


def format_font_info(font_info):
    lines = ["handwrite2350 font info preview", "=" * 40]
    for key, value in font_info.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines) + "\n"


def run_font_info_preview(args):
    font_info = resolve_font_info(args)
    output_text = format_font_info(font_info)
    FONT_INFO_PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    FONT_INFO_PREVIEW_PATH.write_text(output_text, encoding="utf-8")
    print(output_text, end="")
    return font_info


def check_import(module_name, display_name):
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "version unknown")
        return True, f"[OK] {display_name} import: {version}"
    except Exception as exc:
        return False, f"[FAIL] {display_name} import: {type(exc).__name__}: {exc}"


def check_command(command, display_name):
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        output = (result.stdout or result.stderr).strip()
        first_line = output.splitlines()[0] if output else "no version output"
        return True, f"[OK] {display_name}: {first_line}"
    except FileNotFoundError as exc:
        return False, f"[FAIL] {display_name}: command not found: {exc}"
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        return False, f"[FAIL] {display_name}: {details}"
    except Exception as exc:
        return False, f"[FAIL] {display_name}: {type(exc).__name__}: {exc}"


def load_charset(path):
    try:
        return Path(path).read_text(encoding="utf-8").replace("\r", "").replace("\n", "")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"charset file not found: {path}") from exc


def index_to_position(index):
    page = index // CELLS_PER_PAGE
    row = (index % CELLS_PER_PAGE) // COLS
    col = (index % CELLS_PER_PAGE) % COLS
    return page, row, col


def index_to_glyph_info(chars, index):
    try:
        char = chars[index]
    except IndexError as exc:
        raise IndexError(
            f"index out of range: {index} (charset length: {len(chars)})"
        ) from exc

    unicode_dec = ord(char)
    unicode_hex = f"U+{unicode_dec:04X}"
    page, row, col = index_to_position(index)

    return {
        "index": index,
        "char": char,
        "unicode_dec": unicode_dec,
        "unicode_hex": unicode_hex,
        "page": page,
        "row": row,
        "col": col,
    }


def run_env_check():
    check_tasks = [
        lambda: (True, f"[OK] Python: {platform.python_version()} ({sys.executable})"),
        lambda: check_import("cv2", "OpenCV (cv2)"),
        lambda: check_import("numpy", "NumPy"),
        lambda: check_import("PIL", "Pillow (PIL)"),
        lambda: check_command(["fontforge", "--version"], "FontForge"),
        lambda: check_command(["potrace", "--version"], "Potrace"),
    ]
    with ThreadPoolExecutor(max_workers=len(check_tasks)) as executor:
        checks = list(executor.map(lambda task: task(), check_tasks))

    lines = [
        "handwrite2350 Docker environment check",
        "=" * 40,
        *[message for _, message in checks],
    ]

    failed = [message for ok, message in checks if not ok]
    lines.extend(
        [
            "",
            f"Result: {'FAIL' if failed else 'PASS'}",
            f"Failed checks: {len(failed)}",
        ]
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_text = "\n".join(lines) + "\n"
    OUTPUT_PATH.write_text(output_text, encoding="utf-8")
    print(output_text, end="")

    return not failed


def format_glyph_info(info):
    return (
        f"index={info['index']} "
        f"char={info['char']} "
        f"unicode_dec={info['unicode_dec']} "
        f"unicode_hex={info['unicode_hex']} "
        f"page={info['page']} "
        f"row={info['row']} "
        f"col={info['col']}"
    )


def run_mapping_sample():
    chars = load_charset(CHARSET_PATH)
    sample_indexes = [0, 93, 94, 187, len(chars) - 1]

    lines = [
        "handwrite2350 charset mapping sample",
        "=" * 40,
        f"Charset path: {CHARSET_PATH}",
        f"Total characters: {len(chars)}",
        "",
    ]

    for index in sample_indexes:
        info = index_to_glyph_info(chars, index)
        lines.append(format_glyph_info(info))

    MAPPING_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_text = "\n".join(lines) + "\n"
    MAPPING_OUTPUT_PATH.write_text(output_text, encoding="utf-8")
    print(output_text, end="")


def timed_step(performance, name, callback):
    start = time.perf_counter()
    result = callback()
    performance[name] = time.perf_counter() - start
    return result


def add_detail_time(performance, name, elapsed):
    details = performance.setdefault("detail times", {})
    details[name] = details.get(name, 0.0) + elapsed


def timed_detail(performance, name, callback):
    start = time.perf_counter()
    result = callback()
    add_detail_time(performance, name, time.perf_counter() - start)
    return result


def write_performance_report(performance, detailed=True):
    total = performance.get("total time", 0.0)
    lines = ["handwrite2350 performance report", "=" * 40]
    lines.extend(
        [
            f"fast mode: {performance.get('fast mode', False)}",
            f"save warped PNG: {performance.get('save warped PNG', True)}",
            f"warp interpolation: {performance.get('warp interpolation', 'cubic')}",
            f"trace metrics: {performance.get('trace metrics', 'full')}",
            f"layout mode: {performance.get('layout mode', 'fixed')}",
            f"glyph layout report: {performance.get('glyph layout report', False)}",
        ]
    )
    if performance.get("fast mode", False):
        lines.extend(
            [
                "fast mode skipped work:",
                "- warped PNG file writes",
                "- font info preview file/stdout",
                "- charset mapping sample file/stdout",
                "- detailed glyph metrics CSV",
                "- detailed performance breakdown",
            ]
        )
    for name in [
        "preprocessing time",
        "cell split time",
        "trace time",
        "font build time",
        "total time",
    ]:
        lines.append(f"{name}: {performance.get(name, 0.0):.2f}s")

    lines.extend(
        [
            f"cell PNG saving: {performance.get('cell PNG saving', False)}",
            f"direct trace mode: {performance.get('direct trace mode', False)}",
            f"page binary mode: {performance.get('page binary mode', False)}",
            f"in-memory warped input: {performance.get('in-memory warped input', False)}",
            f"font quality: {performance.get('font quality', 'fast')}",
            f"debug artifacts saved: {performance.get('debug artifacts saved', False)}",
            f"env check run: {performance.get('env check run', False)}",
            f"SVG artifact export: {performance.get('SVG artifact export', False)}",
        ]
    )

    if detailed and total > 0:
        stage_measured = sum(
            performance.get(name, 0.0)
            for name in [
                "preprocessing time",
                "cell split time",
                "trace time",
                "font build time",
            ]
        )
        other_time = max(0.0, total - stage_measured)
        lines.append(f"other time: {other_time:.2f}s")

        detail_times = performance.get("detail times", {})
        if detail_times:
            lines.extend(["", "other time breakdown:"])
            for name, elapsed in sorted(
                detail_times.items(),
                key=lambda item: item[1],
                reverse=True,
            ):
                lines.append(f"{name}: {elapsed:.4f}s")
            detail_total = sum(detail_times.values())
            lines.append(f"other detail total: {detail_total:.4f}s")
            lines.append(f"other unaccounted: {max(0.0, other_time - detail_total):.4f}s")

    PERFORMANCE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output_text = "\n".join(lines) + "\n"
    start = time.perf_counter()
    PERFORMANCE_REPORT_PATH.write_text(output_text, encoding="utf-8")
    add_detail_time(performance, "performance report write time", time.perf_counter() - start)
    start = time.perf_counter()
    print(output_text, end="")
    add_detail_time(performance, "performance report stdout time", time.perf_counter() - start)


def export_svg_artifacts(source_dir, output_dir=SVG_DIR):
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for old_svg in output_dir.glob("*.svg"):
        old_svg.unlink()

    copied_count = 0
    for svg_path in source_dir.glob("*.svg"):
        shutil.copyfile(svg_path, output_dir / svg_path.name)
        copied_count += 1
    return copied_count


def main():
    total_start = time.perf_counter()
    performance = {}
    timed_detail(performance, "stdout encoding setup time", configure_output_encoding)
    args = timed_detail(performance, "argument parse time", parse_args)
    save_warped = not args.fast
    warp_interpolation = resolve_warp_interpolation(args)
    trace_metrics_mode = "none" if args.fast else "full"
    performance["fast mode"] = args.fast
    performance["save warped PNG"] = save_warped
    performance["warp interpolation"] = warp_interpolation
    performance["trace metrics"] = trace_metrics_mode
    performance["layout mode"] = args.layout_mode
    performance["glyph layout report"] = args.report_glyph_layout
    performance["env check run"] = args.check_env
    if args.check_env:
        env_ok = timed_detail(performance, "environment check/write/stdout time", run_env_check)
    else:
        env_ok = True

    try:
        if args.fast:
            font_info = timed_detail(
                performance,
                "font info resolve time",
                lambda: resolve_font_info(args),
            )
        else:
            font_info = timed_detail(
                performance,
                "font info resolve/write/stdout time",
                lambda: run_font_info_preview(args),
            )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[ERROR] failed to load font info: {exc}")
        sys.exit(1)

    try:
        if args.fast:
            timed_detail(
                performance,
                "charset validation time",
                lambda: load_charset(CHARSET_PATH),
            )
        else:
            timed_detail(
                performance,
                "mapping sample load/write/stdout time",
                run_mapping_sample,
            )
    except (FileNotFoundError, IndexError) as exc:
        message = f"[ERROR] {exc}"
        MAPPING_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        MAPPING_OUTPUT_PATH.write_text(message + "\n", encoding="utf-8")
        print(message)
        sys.exit(1)

    input_images = timed_detail(
        performance,
        "input image count/list time",
        lambda: list_images(INPUT_DIR),
    )
    if input_images:
        run_preprocess = timed_detail(
            performance,
            "page_preprocess import time",
            lambda: __import__("page_preprocess").run_preprocess,
        )

        preprocess_ok, warped_records = timed_step(
            performance,
            "preprocessing time",
            lambda: run_preprocess(
                INPUT_DIR,
                save_debug=args.save_debug_artifacts,
                workers=args.workers,
                save_warped=save_warped,
                interpolation=warp_interpolation,
            ),
        )
        if not preprocess_ok:
            sys.exit(1)
    else:
        print("No input images found in samples/input. Skipped preprocessing.\n")
        performance["preprocessing time"] = 0.0
        warped_records = []

    cell_records = []
    performance["cell PNG saving"] = args.save_debug_artifacts
    performance["debug artifacts saved"] = args.save_debug_artifacts
    performance["page binary mode"] = False
    performance["font quality"] = args.font_quality
    performance["in-memory warped input"] = bool(warped_records)

    warped_png_exists = False
    if not warped_records:
        warped_png_exists = timed_detail(
            performance,
            "warped PNG existence check time",
            lambda: has_warped_png(WARPED_DIR),
        )

    if warped_records or warped_png_exists:
        run_cell_split = timed_detail(
            performance,
            "cell_split import time",
            lambda: __import__("cell_split").run_cell_split,
        )

        cell_split_ok, cell_records = timed_step(
            performance,
            "cell split time",
            lambda: run_cell_split(
                WARPED_DIR,
                CHARSET_PATH,
                margin_ratio=args.cell_margin,
                save_cells=args.save_debug_artifacts,
                save_contact_sheets=args.save_debug_artifacts,
                warped_records=warped_records if warped_records else None,
            ),
        )
        if not cell_split_ok:
            sys.exit(1)
        warped_records = []
    else:
        print("No warped images found in outputs/warped. Skipped cell split.\n")
        performance["cell split time"] = 0.0

    performance["direct trace mode"] = bool(cell_records)

    cell_images_exist = False
    if not cell_records:
        cell_images_exist = timed_detail(
            performance,
            "cell image existence check time",
            lambda: has_cell_images(CELLS_DIR),
        )

    work_temp = tempfile.TemporaryDirectory(prefix="handwrite2350-work-")
    work_dir = Path(work_temp.name)
    local_svg_dir = work_dir / "svg"
    performance["local SVG work dir"] = str(local_svg_dir)
    performance["SVG artifact export"] = args.export_svg_artifacts

    if cell_records or cell_images_exist:
        run_trace = timed_detail(
            performance,
            "trace_glyphs import time",
            lambda: __import__("trace_glyphs").run_trace,
        )

        trace_ok = timed_step(
            performance,
            "trace time",
            lambda: run_trace(
                CELLS_DIR,
                CHARSET_PATH,
                cell_records=cell_records if cell_records else None,
                workers=args.workers,
                glyph_size=args.glyph_size,
                glyph_padding=args.glyph_padding,
                save_normalized=args.save_normalized,
                svg_dir=local_svg_dir,
                metrics_mode=trace_metrics_mode,
                layout_mode=args.layout_mode,
                glyph_layout_config_path=args.glyph_layout_config,
                report_glyph_layout=args.report_glyph_layout,
            ),
        )
        if not trace_ok:
            sys.exit(1)
        cell_records = []
    else:
        print("No cell images found in outputs/cells. Skipped SVG tracing.\n")
        performance["trace time"] = 0.0

    build_font_module = timed_detail(
        performance,
        "build_font import time",
        lambda: __import__("build_font"),
    )
    count_svg_files = build_font_module.count_svg_files
    run_font_build = build_font_module.run_font_build

    svg_count = timed_detail(
        performance,
        "main SVG files found count time",
        lambda: count_svg_files(local_svg_dir),
    )
    timed_detail(
        performance,
        "main SVG files found stdout time",
        lambda: print(f"SVG files found in {local_svg_dir}: {svg_count}\n", end=""),
    )

    if args.export_svg_artifacts and svg_count > 0:
        exported_count = timed_detail(
            performance,
            "SVG artifact export time",
            lambda: export_svg_artifacts(local_svg_dir, SVG_DIR),
        )
        performance["SVG artifacts exported count"] = exported_count

    if svg_count > 0:
        font_build_ok = timed_step(
            performance,
            "font build time",
            lambda: run_font_build(
                font_info,
                CHARSET_PATH,
                local_svg_dir,
                font_quality=args.font_quality,
            ),
        )
        if not font_build_ok:
            sys.exit(1)
    else:
        print(f"No SVG files found in {SVG_DIR}. Skipped TTF generation.\n")
        performance["font build time"] = 0.0

    performance["total time"] = time.perf_counter() - total_start
    write_performance_report(performance, detailed=not args.fast)
    timed_detail(performance, "local work dir cleanup time", work_temp.cleanup)

    if not env_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
