from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
MARKER_DETECTION_MAX_DIMENSION = 1800
WARPED_SIZE = (4960, 7016)
DEFAULT_ROWS = 17
DEFAULT_COLS = 11
DEFAULT_MARGIN_RATIO = 0.08


def load_chars(path: Path) -> list[str]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_image_files(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
        return [path]
    return sorted(
        [p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.name.lower(),
    )


def content_bbox(gray: np.ndarray) -> tuple[int, int, int, int] | None:
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = []
    area_min = max(8, gray.shape[0] * gray.shape[1] * 0.0005)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h >= area_min:
            boxes.append((x, y, x + w, y + h))
    if not boxes:
        return None
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def order_markers(points: list[np.ndarray]) -> np.ndarray:
    pts = np.array(points, dtype=np.float32)
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).reshape(-1)

    return np.array(
        [
            pts[np.argmin(sums)],
            pts[np.argmin(diffs)],
            pts[np.argmax(sums)],
            pts[np.argmax(diffs)],
        ],
        dtype=np.float32,
    )


def resize_for_marker_detection(image: np.ndarray) -> tuple[np.ndarray, float]:
    height, width = image.shape[:2]
    largest_dimension = max(width, height)
    if largest_dimension <= MARKER_DETECTION_MAX_DIMENSION:
        return image, 1.0

    scale = MARKER_DETECTION_MAX_DIMENSION / largest_dimension
    resized = cv2.resize(
        image,
        (int(round(width * scale)), int(round(height * scale))),
        interpolation=cv2.INTER_AREA,
    )
    return resized, scale


def find_marker_candidates(image: np.ndarray) -> list[dict]:
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 140, 255, cv2.THRESH_BINARY_INV)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    image_area = width * height
    min_area = image_area * 0.00015
    max_area = image_area * 0.04
    candidates = []

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area or area > max_area:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        if w == 0 or h == 0:
            continue

        aspect = w / h
        fill_ratio = area / (w * h)
        if not 0.45 <= aspect <= 2.2:
            continue
        if fill_ratio < 0.45:
            continue

        candidates.append(
            {
                "center": np.array([x + w / 2, y + h / 2], dtype=np.float32),
                "bbox": (x, y, w, h),
                "area": area,
            }
        )

    return candidates


def detect_markers(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    detection_image, scale = resize_for_marker_detection(image)
    candidates = find_marker_candidates(detection_image)

    if scale != 1.0:
        inverse_scale = 1.0 / scale
        for candidate in candidates:
            candidate["center"] = candidate["center"] * inverse_scale

    if len(candidates) < 4:
        raise RuntimeError(f"expected 4 template markers, found {len(candidates)}")

    corners = [
        np.array([0, 0], dtype=np.float32),
        np.array([width, 0], dtype=np.float32),
        np.array([width, height], dtype=np.float32),
        np.array([0, height], dtype=np.float32),
    ]

    selected = []
    used = set()
    for corner in corners:
        best_index = None
        best_distance = None
        for index, candidate in enumerate(candidates):
            if index in used:
                continue

            distance = np.linalg.norm(candidate["center"] - corner)
            if best_distance is None or distance < best_distance:
                best_index = index
                best_distance = distance

        used.add(best_index)
        selected.append(candidates[best_index]["center"])

    return order_markers(selected)


def warp_page(image: np.ndarray) -> np.ndarray:
    markers = detect_markers(image)
    destination = np.array(
        [
            [0, 0],
            [WARPED_SIZE[0] - 1, 0],
            [WARPED_SIZE[0] - 1, WARPED_SIZE[1] - 1],
            [0, WARPED_SIZE[1] - 1],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(markers, destination)
    return cv2.warpPerspective(image, matrix, WARPED_SIZE, flags=cv2.INTER_CUBIC)


def detect_grid_bbox(image: np.ndarray) -> tuple[int, int, int, int]:
    height, width = image.shape[:2]
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    binary = gray < 170

    row_counts = binary.sum(axis=1)
    col_counts = binary.sum(axis=0)
    row_indexes = np.where(row_counts > width * 0.35)[0]
    col_indexes = np.where(col_counts > height * 0.35)[0]

    if len(row_indexes) < 2 or len(col_indexes) < 2:
        return 0, 0, width, height

    x0 = int(col_indexes.min())
    x1 = int(col_indexes.max()) + 1
    y0 = int(row_indexes.min())
    y1 = int(row_indexes.max()) + 1

    if x1 <= x0 or y1 <= y0:
        return 0, 0, width, height

    return x0, y0, x1, y1


def crop_grid_cell(
    image: np.ndarray,
    grid_bbox: tuple[int, int, int, int],
    row: int,
    col: int,
    rows: int,
    cols: int,
    margin_ratio: float,
) -> np.ndarray:
    x0, y0, x1, y1 = grid_bbox
    grid_width = x1 - x0
    grid_height = y1 - y0

    cell_x0 = x0 + int(round(col * grid_width / cols))
    cell_x1 = x0 + int(round((col + 1) * grid_width / cols))
    cell_y0 = y0 + int(round(row * grid_height / rows))
    cell_y1 = y0 + int(round((row + 1) * grid_height / rows))

    cell_width = cell_x1 - cell_x0
    cell_height = cell_y1 - cell_y0
    margin_x = int(round(cell_width * margin_ratio))
    margin_y = int(round(cell_height * margin_ratio))

    crop_x0 = min(max(cell_x0 + margin_x, 0), image.shape[1])
    crop_x1 = min(max(cell_x1 - margin_x, 0), image.shape[1])
    crop_y0 = min(max(cell_y0 + margin_y, 0), image.shape[0])
    crop_y1 = min(max(cell_y1 - margin_y, 0), image.shape[0])

    if crop_x1 <= crop_x0 or crop_y1 <= crop_y0:
        raise RuntimeError(f"invalid crop box for row={row}, col={col}")

    return image[crop_y0:crop_y1, crop_x0:crop_x1]


def to_model_reference_image(image: Image.Image) -> Image.Image:
    return Image.fromarray(255 - np.array(image.convert("L")))


def normalize_glyph(cell_bgr: np.ndarray, size: int, padding: int, preserve_cell_scale: bool) -> Image.Image:
    gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
    if preserve_cell_scale:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.mean(binary) < 127:
            binary = 255 - binary
        max_side = max(1, size - padding * 2)
        scale = min(max_side / binary.shape[1], max_side / binary.shape[0])
        new_size = (
            max(1, int(round(binary.shape[1] * scale))),
            max(1, int(round(binary.shape[0] * scale))),
        )
        resized = Image.fromarray(binary).resize(new_size, Image.Resampling.LANCZOS)
        canvas = Image.new("L", (size, size), 255)
        x = (size - resized.width) // 2
        y = (size - resized.height) // 2
        canvas.paste(resized, (x, y))
        return to_model_reference_image(canvas)

    bbox = content_bbox(gray)
    canvas = Image.new("L", (size, size), 255)
    if bbox is None:
        return canvas

    x1, y1, x2, y2 = bbox
    glyph = gray[y1:y2, x1:x2]
    _, glyph = cv2.threshold(glyph, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    glyph = Image.fromarray(glyph)

    max_side = max(1, size - padding * 2)
    scale = min(max_side / glyph.width, max_side / glyph.height)
    new_size = (max(1, int(glyph.width * scale)), max(1, int(glyph.height * scale)))
    glyph = glyph.resize(new_size, Image.Resampling.LANCZOS)

    x = (size - glyph.width) // 2
    y = (size - glyph.height) // 2
    canvas.paste(glyph, (x, y))
    return to_model_reference_image(canvas)


def crop_sheet(
    sheet_path: Path,
    out_dir: Path,
    chars: list[str],
    rows: int,
    cols: int,
    size: int,
    padding: int,
    margin_ratio: float,
) -> None:
    image = cv2.imdecode(np.fromfile(str(sheet_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"failed to read image: {sheet_path}")

    expected = rows * cols
    if expected < len(chars):
        raise RuntimeError(f"grid has {expected} cells but {len(chars)} characters are required")

    warped = warp_page(image)
    grid_bbox = detect_grid_bbox(warped)

    for idx, char in enumerate(chars):
        row = idx // cols
        col = idx % cols
        cell = crop_grid_cell(warped, grid_bbox, row, col, rows, cols, margin_ratio)
        glyph = normalize_glyph(cell, size=size, padding=padding, preserve_cell_scale=False)
        glyph.save(out_dir / f"{char}.png")


def copy_named_images(files: list[Path], out_dir: Path, chars: list[str], size: int, padding: int) -> bool:
    by_stem = {path.stem: path for path in files}
    if not all(char in by_stem for char in chars):
        return False

    for char in chars:
        image = cv2.imdecode(np.fromfile(str(by_stem[char]), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"failed to read image: {by_stem[char]}")
        normalize_glyph(image, size=size, padding=padding, preserve_cell_scale=False).save(out_dir / f"{char}.png")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop a DM-Font reference sheet into write2font PNG inputs.")
    parser.add_argument("--input", required=True, help="Input image file or directory")
    parser.add_argument("--out-dir", required=True, help="Output directory, usually write2font/png/<font-key>")
    parser.add_argument("--ref-chars", default="write2font/ref_chars.json")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--cols", type=int, default=DEFAULT_COLS)
    parser.add_argument("--cell-margin", type=float, default=DEFAULT_MARGIN_RATIO)
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--padding", type=int, default=12)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    chars = load_chars(Path(args.ref_chars))

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = find_image_files(input_path)
    if not files:
        raise RuntimeError(f"no image files found: {input_path}")

    if len(files) >= len(chars) and copy_named_images(files, out_dir, chars, args.size, args.padding):
        return

    if len(files) != 1:
        raise RuntimeError(
            f"expected one marked reference sheet or {len(chars)} images named by character"
        )

    crop_sheet(files[0], out_dir, chars, args.rows, args.cols, args.size, args.padding, args.cell_margin)


if __name__ == "__main__":
    main()
