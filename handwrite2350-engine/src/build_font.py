import csv
import json
import os
import shlex
import subprocess
import tempfile
import time
from pathlib import Path


OUTPUTS_DIR = Path(os.environ.get("HANDWRITE_OUTPUTS_DIR", "/app/outputs"))
CHARSET_PATH = Path(os.environ.get("HANDWRITE_CHARSET_PATH", "charsets/basiclatin_ksx1001.txt"))
SVG_DIR = OUTPUTS_DIR / "svg"
FONTS_DIR = OUTPUTS_DIR / "fonts"
REPORT_PATH = OUTPUTS_DIR / "font_build_report.txt"
FONT_INFO_BUILD_PATH = OUTPUTS_DIR / "font_info_build.json"
FONTFORGE_SCRIPT_PATH = Path("src/fontforge_build.py")
STAGING_METRICS_CSV_PATH = OUTPUTS_DIR / "svg_staging_metrics.csv"
STAGING_METRICS_SUMMARY_PATH = OUTPUTS_DIR / "svg_staging_metrics_summary.json"


def list_svg_files(svg_dir=SVG_DIR):
    path = Path(svg_dir)
    if not path.exists():
        return []

    return sorted(path.rglob("*.svg"))


def count_svg_files(svg_dir=SVG_DIR):
    return len(list_svg_files(svg_dir))


def has_svg_files(svg_dir=SVG_DIR):
    return count_svg_files(svg_dir) > 0


def percentile(values, percent):
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(round((len(sorted_values) - 1) * percent / 100.0))
    return sorted_values[index]


def summarize_values(values):
    return {
        "total": sum(values),
        "average": sum(values) / len(values) if values else 0.0,
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "max": max(values) if values else 0.0,
    }


def pearson_correlation(pairs):
    if len(pairs) < 2:
        return 0.0
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    denominator_x = sum((x - mean_x) ** 2 for x in xs)
    denominator_y = sum((y - mean_y) ** 2 for y in ys)
    denominator = (denominator_x * denominator_y) ** 0.5
    return numerator / denominator if denominator else 0.0


def write_staging_metrics(file_rows, stage_info):
    STAGING_METRICS_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "index",
        "source_path",
        "staged_path",
        "svg_file_size_bytes",
        "temp_file_created",
        "filename_changed",
        "content_modified",
        "xml_parse",
        "path_rewrite",
        "viewbox_modified",
        "transform_inserted",
        "read_time",
        "write_time",
        "file_total_time",
    ]
    with STAGING_METRICS_CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fieldnames} for row in file_rows)

    staging_times = [row["file_total_time"] for row in file_rows]
    read_times = [row["read_time"] for row in file_rows]
    write_times = [row["write_time"] for row in file_rows]
    size_pairs = [(row["svg_file_size_bytes"], row["file_total_time"]) for row in file_rows]
    top_slowest = sorted(file_rows, key=lambda row: row["file_total_time"], reverse=True)[:20]
    summary = {
        **stage_info,
        "metrics_csv": str(STAGING_METRICS_CSV_PATH),
        "staging_time_stats": summarize_values(staging_times),
        "read_time_stats": summarize_values(read_times),
        "write_time_stats": summarize_values(write_times),
        "svg_size_staging_time_correlation": pearson_correlation(size_pairs),
        "top_20_slowest_svg_staging": top_slowest,
        "content_modified": False,
        "xml_parse": False,
        "path_rewrite": False,
        "viewbox_modified": False,
        "transform_inserted": False,
        "filename_changed": False,
    }
    STAGING_METRICS_SUMMARY_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def cleanup_staged_temp(staged_temp):
    start = time.perf_counter()
    staged_temp.cleanup()
    return time.perf_counter() - start


def update_staging_summary_cleanup(stage_info):
    summary_path = stage_info.get("metrics_summary_json")
    if not summary_path:
        return
    path = Path(summary_path)
    if not path.exists():
        return
    summary = json.loads(path.read_text(encoding="utf-8"))
    summary["cleanup_time"] = stage_info["cleanup_time"]
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def stage_svg_files_profiled(source_dir, staged_dir, svg_paths):
    rows = []
    start = time.perf_counter()
    for index, svg_path in enumerate(svg_paths):
        target_path = staged_dir / svg_path.name
        file_start = time.perf_counter()

        read_start = time.perf_counter()
        data = svg_path.read_bytes()
        read_time = time.perf_counter() - read_start

        write_start = time.perf_counter()
        target_path.write_bytes(data)
        write_time = time.perf_counter() - write_start

        rows.append(
            {
                "index": index,
                "source_path": str(svg_path),
                "staged_path": str(target_path),
                "svg_file_size_bytes": len(data),
                "temp_file_created": True,
                "filename_changed": svg_path.name != target_path.name,
                "content_modified": False,
                "xml_parse": False,
                "path_rewrite": False,
                "viewbox_modified": False,
                "transform_inserted": False,
                "read_time": read_time,
                "write_time": write_time,
                "file_total_time": time.perf_counter() - file_start,
            }
        )
    return time.perf_counter() - start, rows


def stage_svg_files_tar(source_dir, staged_dir, svg_paths):
    start = time.perf_counter()
    if svg_paths:
        copy_command = (
            f"tar -cf - -C {shlex.quote(str(source_dir))} . "
            f"| tar -xf - -C {shlex.quote(str(staged_dir))}"
        )
        subprocess.run(["sh", "-c", copy_command], check=True)
    return time.perf_counter() - start


def stage_svg_files(svg_dir):
    source_dir = Path(svg_dir)
    profile_staging = os.environ.get("HANDWRITE_PROFILE_STAGING") == "1"

    create_start = time.perf_counter()
    staged_temp = tempfile.TemporaryDirectory(prefix="handwrite2350-svg-")
    staged_dir = Path(staged_temp.name)
    temp_dir_create_time = time.perf_counter() - create_start

    list_start = time.perf_counter()
    svg_paths = sorted(source_dir.glob("*.svg"))
    source_list_time = time.perf_counter() - list_start

    if profile_staging:
        copy_time, file_rows = stage_svg_files_profiled(source_dir, staged_dir, svg_paths)
    else:
        copy_time = stage_svg_files_tar(source_dir, staged_dir, svg_paths)
        file_rows = []

    stage_info = {
        "staging_mode": "profiled-read-write" if profile_staging else "tar-stream",
        "staged_svg_count": len(svg_paths),
        "staged_svg_dir": str(staged_dir),
        "temp_dir_create_time": temp_dir_create_time,
        "source_list_time": source_list_time,
        "copy_time": copy_time,
        "staging_total_time": temp_dir_create_time + source_list_time + copy_time,
        "cleanup_time": 0.0,
        "content_modified": False,
        "modification_operations": {
            "xml_parse": False,
            "path_rewrite": False,
            "viewbox_modified": False,
            "transform_inserted": False,
            "filename_changed": False,
            "temporary_file_created": True,
        },
        "metrics_csv": str(STAGING_METRICS_CSV_PATH) if profile_staging else "",
        "metrics_summary_json": str(STAGING_METRICS_SUMMARY_PATH) if profile_staging else "",
    }
    if profile_staging:
        write_staging_metrics(file_rows, stage_info)

    return (
        staged_temp,
        staged_dir,
        len(svg_paths),
        stage_info["staging_total_time"],
        stage_info,
    )


def is_local_work_svg_dir(svg_dir):
    try:
        resolved = Path(svg_dir).resolve()
    except OSError:
        resolved = Path(svg_dir)
    return str(resolved).startswith("/tmp/")


def use_svg_files_directly(svg_dir):
    source_dir = Path(svg_dir)
    start = time.perf_counter()
    svg_paths = sorted(source_dir.glob("*.svg"))
    source_list_time = time.perf_counter() - start
    stage_info = {
        "staging_mode": "skipped-local",
        "staged_svg_count": len(svg_paths),
        "staged_svg_dir": str(source_dir),
        "temp_dir_create_time": 0.0,
        "source_list_time": source_list_time,
        "copy_time": 0.0,
        "staging_total_time": source_list_time,
        "cleanup_time": 0.0,
        "content_modified": False,
        "modification_operations": {
            "xml_parse": False,
            "path_rewrite": False,
            "viewbox_modified": False,
            "transform_inserted": False,
            "filename_changed": False,
            "temporary_file_created": False,
        },
        "metrics_csv": "",
        "metrics_summary_json": "",
    }
    return None, source_dir, len(svg_paths), source_list_time, stage_info


def run_font_build(
    font_info,
    charset_path=CHARSET_PATH,
    svg_dir=SVG_DIR,
    font_quality="fast",
):
    svg_count = count_svg_files(svg_dir)
    print(f"SVG files found in {Path(svg_dir)}: {svg_count}\n", end="")

    if svg_count == 0:
        print("No SVG files found. Skipped TTF generation.\n", end="")
        return True

    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FONT_INFO_BUILD_PATH.write_text(
        json.dumps(font_info, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if is_local_work_svg_dir(svg_dir):
        staged_temp, staged_svg_dir, staged_count, staging_time, stage_info = (
            use_svg_files_directly(svg_dir)
        )
    else:
        staged_temp, staged_svg_dir, staged_count, staging_time, stage_info = (
            stage_svg_files(svg_dir)
        )

    command = [
        "fontforge",
        "-lang=py",
        "-script",
        str(FONTFORGE_SCRIPT_PATH),
        "--charset",
        str(charset_path),
        "--svg-dir",
        str(staged_svg_dir),
        "--fonts-dir",
        str(FONTS_DIR),
        "--font-info",
        str(FONT_INFO_BUILD_PATH),
        "--report",
        str(REPORT_PATH),
        "--quality",
        font_quality,
    ]

    try:
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            if staged_temp is not None:
                stage_info["cleanup_time"] = cleanup_staged_temp(staged_temp)
            update_staging_summary_cleanup(stage_info)
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or str(exc)).strip()
        REPORT_PATH.write_text(
            "handwrite2350 font build report\n"
            "========================================\n"
            f"FontForge command failed: {details}\n",
            encoding="utf-8",
        )
        print(REPORT_PATH.read_text(encoding="utf-8"), end="")
        return False

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")

    if REPORT_PATH.exists():
        report_text = REPORT_PATH.read_text(encoding="utf-8")
        report_text = report_text.replace(
            "font quality:",
            (
                f"staged SVG count: {staged_count}\n"
                f"SVG staging time: {staging_time:.2f}s\n"
                f"staged SVG dir: {staged_svg_dir}\n"
                f"SVG staging mode: {stage_info['staging_mode']}\n"
                f"SVG temp dir create time: {stage_info['temp_dir_create_time']:.4f}s\n"
                f"SVG source list time: {stage_info['source_list_time']:.4f}s\n"
                f"SVG copy/write time: {stage_info['copy_time']:.2f}s\n"
                f"SVG cleanup time: {stage_info['cleanup_time']:.4f}s\n"
                f"SVG content modified: {stage_info['content_modified']}\n"
                f"SVG staging metrics CSV: {stage_info['metrics_csv']}\n"
                f"SVG staging metrics summary JSON: {stage_info['metrics_summary_json']}\n"
                "font quality:"
            ),
            1,
        )
        REPORT_PATH.write_text(report_text, encoding="utf-8")
        print(report_text, end="")

    return True
