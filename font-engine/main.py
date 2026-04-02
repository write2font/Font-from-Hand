from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

import cv2
import numpy as np

from config import (
    CELL_MARGIN_RATIO_X,
    CELL_MARGIN_RATIO_Y,
    DEFAULT_FONTFORGE_CMD,
    DEFAULT_MAPPING_PATH,
    DEFAULT_POTRACE_CMD,
)
from glyphs import rasterize_cell, save_debug_png, save_pbm

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
WARP_CELL_PX = 256


def natural_key(path: Path):
    parts = re.split(r"(\d+)", path.name)
    key = []
    for part in parts:
        if part.isdigit():
            key.append(int(part))
        else:
            key.append(part.lower())
    return key


def load_mapping(mapping_path: Path) -> List[str]:
    text = mapping_path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError(f"매핑 파일이 비어 있습니다: {mapping_path}")
    return list(text)


def resolve_mapping_path(input_dir: Path, explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise RuntimeError(f"지정한 매핑 파일이 없습니다: {path}")
        return path

    local = input_dir / "mapping.txt"
    if local.exists():
        return local

    if DEFAULT_MAPPING_PATH.exists():
        return DEFAULT_MAPPING_PATH

    raise RuntimeError("mapping.txt를 찾지 못했습니다.")


def collect_images(input_dir: Path) -> List[Path]:
    files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS]
    files.sort(key=natural_key)
    if not files:
        raise RuntimeError("입력 폴더에서 이미지 파일을 찾지 못했습니다.")
    return files


def run_command(cmd: List[str], cwd: Path | None = None, stream: bool = False) -> None:
    if stream:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"외부 명령 실행 실패: {' '.join(cmd)}")
        return

    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(stderr or f"외부 명령 실행 실패: {' '.join(cmd)}")


def vectorize_pbm(potrace_cmd: str, pbm_path: Path, svg_path: Path) -> None:
    run_command(
        [
            potrace_cmd,
            str(pbm_path),
            "-s",
            "-o",
            str(svg_path),
            "--turdsize",
            "2",
        ]
    )


def build_font_with_fontforge(fontforge_cmd: str, manifest_path: Path, out_ttf: Path) -> None:
    script_path = Path(__file__).resolve().parent / "build_font.py"
    run_command([fontforge_cmd, "-script", str(script_path), str(manifest_path), str(out_ttf)], stream=True)


def _vectorize_job(job: tuple[str, str, str]) -> str:
    potrace_cmd, pbm_path, svg_path = job
    vectorize_pbm(potrace_cmd, Path(pbm_path), Path(svg_path))
    return svg_path


def order_points(pts: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def find_grid_rect(gray: np.ndarray) -> np.ndarray | None:
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    th = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        45,
        7,
    )

    h, w = gray.shape[:2]
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(40, w // 20), 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(40, h // 20)))
    h_lines = cv2.morphologyEx(th, cv2.MORPH_OPEN, h_kernel, iterations=1)
    v_lines = cv2.morphologyEx(th, cv2.MORPH_OPEN, v_kernel, iterations=1)
    grid = cv2.bitwise_or(h_lines, v_lines)

    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    image_area = float(h * w)
    best = None
    best_area = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < image_area * 0.10:
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        if cw < w * 0.4 or ch < h * 0.4:
            continue
        if area > best_area:
            best = c
            best_area = area

    if best is None:
        best = max(contours, key=cv2.contourArea)

    peri = cv2.arcLength(best, True)
    approx = cv2.approxPolyDP(best, 0.02 * peri, True)
    if len(approx) == 4:
        return order_points(approx.reshape(4, 2))

    rect = cv2.minAreaRect(best)
    return order_points(cv2.boxPoints(rect))


def warp_page_to_grid(img_bgr: np.ndarray, rows: int, cols: int) -> tuple[np.ndarray, np.ndarray | None]:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    box = find_grid_rect(gray)
    if box is None:
        return img_bgr, None

    out_w = cols * WARP_CELL_PX
    out_h = rows * WARP_CELL_PX
    dst = np.array(
        [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
        dtype="float32",
    )
    M = cv2.getPerspectiveTransform(box, dst)
    warped = cv2.warpPerspective(
        img_bgr,
        M,
        (out_w, out_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return warped, box


def crop_page_grid(img_bgr: np.ndarray, rows: int, cols: int):
    warped, _box = warp_page_to_grid(img_bgr, rows=rows, cols=cols)
    h, w = warped.shape[:2]
    cell_h = h / rows
    cell_w = w / cols

    for r in range(rows):
        for c in range(cols):
            y1 = int(round(r * cell_h))
            y2 = int(round((r + 1) * cell_h))
            x1 = int(round(c * cell_w))
            x2 = int(round((c + 1) * cell_w))

            margin_h = int(round((y2 - y1) * CELL_MARGIN_RATIO_Y))
            margin_w = int(round((x2 - x1) * CELL_MARGIN_RATIO_X))

            cy1 = min(y2, y1 + margin_h)
            cy2 = max(cy1 + 1, y2 - margin_h)
            cx1 = min(x2, x1 + margin_w)
            cx2 = max(cx1 + 1, x2 - margin_w)

            yield (cx1, cy1, cx2, cy2), warped[cy1:cy2, cx1:cx2].copy(), warped


def create_manifest(family_name: str, glyphs: list[dict], path: Path) -> None:
    manifest = {
        "family_name": family_name,
        "glyphs": glyphs,
    }
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def build_pipeline(
    input_dir: Path,
    output_ttf: Path,
    rows: int,
    cols: int,
    family_name: str,
    mapping_path: Path,
    potrace_cmd: str,
    fontforge_cmd: str,
    save_normalized_debug: bool,
    workers: int,
    keep_pbm: bool,
) -> None:
    chars = load_mapping(mapping_path)
    images = collect_images(input_dir)

    total_cells = len(images) * rows * cols
    if total_cells < len(chars):
        raise RuntimeError(
            f"칸 수가 부족합니다. images({len(images)}) * rows({rows}) * cols({cols}) = {total_cells}, 매핑 길이 = {len(chars)}"
        )

    work_dir = output_ttf.parent / f"{output_ttf.stem}_debug"
    if work_dir.exists():
        shutil.rmtree(work_dir)
    pbm_dir = work_dir / "pbm"
    svg_dir = work_dir / "svg"
    warped_dir = work_dir / "warped_pages"
    pbm_dir.mkdir(parents=True, exist_ok=True)
    svg_dir.mkdir(parents=True, exist_ok=True)
    warped_dir.mkdir(parents=True, exist_ok=True)

    normalized_dir = None
    if save_normalized_debug:
        normalized_dir = work_dir / "normalized_png"
        normalized_dir.mkdir(parents=True, exist_ok=True)

    glyphs: list[dict] = []
    vector_jobs: list[tuple[str, str, str]] = []
    char_idx = 0
    total = len(chars)

    for page_no, image_path in enumerate(images, start=1):
        img = cv2.imread(str(image_path))
        if img is None:
            raise RuntimeError(f"이미지를 읽지 못했습니다: {image_path}")

        page_cells = crop_page_grid(img, rows=rows, cols=cols)
        saved_warp = False
        for cell_no, (_box, cell_img, warped_img) in enumerate(page_cells, start=1):
            if not saved_warp:
                cv2.imwrite(str(warped_dir / f"page_{page_no:02d}.png"), warped_img)
                saved_warp = True
            if char_idx >= total:
                break

            current = char_idx + 1
            if current == 1 or current % 50 == 0 or current == total:
                print(f"[raster] {current}/{total}", flush=True)

            ch = chars[char_idx]
            code = ord(ch)
            mask = rasterize_cell(cell_img)

            base_name = f"{char_idx + 1:04d}_U{code:04X}_p{page_no:02d}_c{cell_no:03d}"
            pbm_path = pbm_dir / f"{base_name}.pbm"
            svg_path = svg_dir / f"{base_name}.svg"

            if normalized_dir is not None:
                norm_path = normalized_dir / f"{base_name}.png"
                save_debug_png(mask, norm_path)

            save_pbm(mask, pbm_path)
            vector_jobs.append((potrace_cmd, str(pbm_path), str(svg_path)))

            glyphs.append(
                {
                    "char": ch,
                    "svg_path": str(svg_path.resolve()),
                    "page": page_no,
                    "cell": cell_no,
                }
            )
            char_idx += 1

        if char_idx >= total:
            break

    if char_idx != total:
        raise RuntimeError(f"글자 수가 맞지 않습니다. 처리={char_idx}, 기대={total}")

    workers = max(1, workers)
    print(f"[vectorize] start: {len(vector_jobs)} jobs, workers={workers}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(_vectorize_job, job) for job in vector_jobs]
        done = 0
        total_jobs = len(futures)
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done == 1 or done % 50 == 0 or done == total_jobs:
                print(f"[vectorize] {done}/{total_jobs}", flush=True)

    if not keep_pbm:
        shutil.rmtree(pbm_dir, ignore_errors=True)

    manifest_path = work_dir / "manifest.json"
    create_manifest(family_name=family_name, glyphs=glyphs, path=manifest_path)

    output_ttf.parent.mkdir(parents=True, exist_ok=True)
    build_font_with_fontforge(fontforge_cmd, manifest_path, output_ttf)

    summary = {
        "family_name": family_name,
        "mapping_path": str(mapping_path),
        "image_count": len(images),
        "rows": rows,
        "cols": cols,
        "glyph_count": len(glyphs),
        "output_ttf": str(output_ttf),
    }
    (work_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="스캔 이미지 여러 장을 잘라 TTF 폰트를 만듭니다.")
    parser.add_argument("input_dir", help="스캔 이미지들이 들어 있는 폴더")
    parser.add_argument("output_ttf", help="생성할 TTF 파일 경로")
    parser.add_argument("--mapping", help="매핑 파일 경로 (기본: input_dir/mapping.txt 또는 font-engine/mapping.txt)")
    parser.add_argument("--rows", type=int, default=14, help="페이지당 행 수 (기본: 14)")
    parser.add_argument("--cols", type=int, default=10, help="페이지당 열 수 (기본: 10)")
    parser.add_argument("--family-name", default="MyHandFont", help="폰트 family name")
    parser.add_argument("--potrace", default=DEFAULT_POTRACE_CMD, help="potrace 실행 파일 경로 또는 명령어")
    parser.add_argument("--fontforge", default=DEFAULT_FONTFORGE_CMD, help="fontforge 실행 파일 경로 또는 명령어")
    parser.add_argument(
        "--save-normalized-debug",
        action="store_true",
        help="정규화 PNG 디버그 이미지를 저장합니다. 기본값은 꺼짐입니다.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min((os.cpu_count() or 4), 8),
        help="potrace 병렬 작업 수 (기본: CPU 개수 기준 최대 8)",
    )
    parser.add_argument(
        "--keep-pbm",
        action="store_true",
        help="중간 PBM 파일을 디버그용으로 남깁니다. 기본값은 완료 후 삭제입니다.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_ttf = Path(args.output_ttf).resolve()

    if not input_dir.exists() or not input_dir.is_dir():
        print(f"입력 폴더가 없습니다: {input_dir}", file=sys.stderr)
        return 1

    try:
        mapping_path = resolve_mapping_path(input_dir, args.mapping)
        build_pipeline(
            input_dir=input_dir,
            output_ttf=output_ttf,
            rows=args.rows,
            cols=args.cols,
            family_name=args.family_name,
            mapping_path=mapping_path,
            potrace_cmd=args.potrace,
            fontforge_cmd=args.fontforge,
            save_normalized_debug=args.save_normalized_debug,
            workers=args.workers,
            keep_pbm=args.keep_pbm,
        )
        print(f"완료: {output_ttf}")
        print(f"디버그 폴더: {output_ttf.parent / (output_ttf.stem + '_debug')}")
        return 0
    except Exception as e:
        print(f"실패: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
