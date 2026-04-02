from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import (
    BORDER_CLEAR_PX,
    CANVAS_SIZE,
    COMPONENT_MIN_AREA_ABS,
    COMPONENT_MIN_AREA_DIVISOR,
    INNER_CROP_MIN_PX,
    INNER_CROP_RATIO_X,
    INNER_CROP_RATIO_Y,
    MORPH_CLOSE_KERNEL,
    NORMALIZE_PADDING_RATIO,
    NORMALIZE_VERTICAL_SHIFT_RATIO,
)


def crop_inner_cell(cell_bgr: np.ndarray) -> np.ndarray:
    h, w = cell_bgr.shape[:2]
    mx = max(INNER_CROP_MIN_PX, int(round(w * INNER_CROP_RATIO_X)))
    my = max(INNER_CROP_MIN_PX, int(round(h * INNER_CROP_RATIO_Y)))
    x1, x2 = mx, max(mx + 1, w - mx)
    y1, y2 = my, max(my + 1, h - my)
    return cell_bgr[y1:y2, x1:x2].copy()


def _remove_small_components(mask: np.ndarray) -> np.ndarray:
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    cleaned = np.zeros_like(mask)
    min_area = max(
        COMPONENT_MIN_AREA_ABS,
        (mask.shape[0] * mask.shape[1]) // COMPONENT_MIN_AREA_DIVISOR,
    )

    for i in range(1, num_labels):
        _x, _y, _w, _h, area = stats[i]
        if area >= min_area:
            cleaned[labels == i] = 255

    return cleaned


def threshold_handwriting(inner_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(inner_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    bw = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        35,
        15,
    )

    bw[:BORDER_CLEAR_PX, :] = 0
    bw[-BORDER_CLEAR_PX:, :] = 0
    bw[:, :BORDER_CLEAR_PX] = 0
    bw[:, -BORDER_CLEAR_PX:] = 0

    cleaned = _remove_small_components(bw)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (MORPH_CLOSE_KERNEL, MORPH_CLOSE_KERNEL),
    )
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
    return cleaned


def _content_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0 or len(ys) == 0:
        return None
    x1 = int(xs.min())
    x2 = int(xs.max()) + 1
    y1 = int(ys.min())
    y2 = int(ys.max()) + 1
    return x1, y1, x2, y2


def fit_to_canvas(mask: np.ndarray) -> np.ndarray:
    canvas = np.zeros((CANVAS_SIZE, CANVAS_SIZE), dtype=np.uint8)
    bbox = _content_bbox(mask)
    if bbox is None:
        return canvas

    x1, y1, x2, y2 = bbox
    glyph = mask[y1:y2, x1:x2]
    gh, gw = glyph.shape[:2]
    if gh <= 0 or gw <= 0:
        return canvas

    inner_size = max(1, int(round(CANVAS_SIZE * (1.0 - 2.0 * NORMALIZE_PADDING_RATIO))))
    scale = min(inner_size / max(gw, 1), inner_size / max(gh, 1))
    nw = max(1, int(round(gw * scale)))
    nh = max(1, int(round(gh * scale)))

    interp = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    resized = cv2.resize(glyph, (nw, nh), interpolation=interp)
    resized = cv2.GaussianBlur(resized, (3, 3), 0)
    _, resized = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)

    xoff = (CANVAS_SIZE - nw) // 2
    yoff = (CANVAS_SIZE - nh) // 2
    vertical_shift = int(round(CANVAS_SIZE * NORMALIZE_VERTICAL_SHIFT_RATIO))
    yoff += vertical_shift
    yoff = max(0, min(yoff, CANVAS_SIZE - nh))

    canvas[yoff:yoff + nh, xoff:xoff + nw] = resized
    return canvas


def rasterize_cell(cell_bgr: np.ndarray) -> np.ndarray:
    inner = crop_inner_cell(cell_bgr)
    mask = threshold_handwriting(inner)
    return fit_to_canvas(mask)


def save_debug_png(mask: np.ndarray, path: Path) -> None:
    debug_img = Image.fromarray(255 - mask)
    debug_img.save(path)


def save_pbm(mask: np.ndarray, path: Path) -> None:
    # PIL 1비트 저장보다 빠른 바이너리 PGM/PBM 직렬화를 직접 작성합니다.
    binary = (mask > 0).astype(np.uint8) * 255
    inverted = 255 - binary
    pil = Image.fromarray(inverted).convert("1")
    pil.save(path)
