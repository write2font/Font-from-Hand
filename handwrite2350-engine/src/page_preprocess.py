from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np


INPUT_DIR = Path("samples/input")
WARPED_DIR = Path("outputs/warped")
DEBUG_DIR = Path("outputs/debug")
REPORT_PATH = Path("outputs/preprocess_report.txt")
WARPED_SIZE = (4960, 7016)
MARKER_DETECTION_MAX_DIMENSION = 1800
PNG_COMPRESSION = 1

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def list_input_images(input_dir=INPUT_DIR):
    input_path = Path(input_dir)
    if not input_path.exists():
        return []

    return sorted(
        path
        for path in input_path.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def order_markers(points):
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


def resize_for_marker_detection(image):
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


def find_marker_candidates(image):
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


def detect_markers(image):
    height, width = image.shape[:2]
    detection_image, scale = resize_for_marker_detection(image)
    candidates = find_marker_candidates(detection_image)

    if scale != 1.0:
        inverse_scale = 1.0 / scale
        for candidate in candidates:
            candidate["center"] = candidate["center"] * inverse_scale
            x, y, w, h = candidate["bbox"]
            candidate["bbox"] = (
                int(round(x * inverse_scale)),
                int(round(y * inverse_scale)),
                int(round(w * inverse_scale)),
                int(round(h * inverse_scale)),
            )
            candidate["area"] = candidate["area"] * inverse_scale * inverse_scale

    if len(candidates) < 4:
        raise ValueError(f"expected 4 markers, found {len(candidates)} candidates")

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
        selected.append(candidates[best_index])

    return order_markers([candidate["center"] for candidate in selected]), candidates


def warp_page(image, ordered_markers, interpolation=cv2.INTER_CUBIC):
    destination = np.array(
        [
            [0, 0],
            [WARPED_SIZE[0] - 1, 0],
            [WARPED_SIZE[0] - 1, WARPED_SIZE[1] - 1],
            [0, WARPED_SIZE[1] - 1],
        ],
        dtype=np.float32,
    )

    matrix = cv2.getPerspectiveTransform(ordered_markers, destination)
    return cv2.warpPerspective(image, matrix, WARPED_SIZE, flags=interpolation)


def draw_debug_image(image, ordered_markers, candidates):
    debug = image.copy()

    for candidate in candidates:
        x, y, w, h = candidate["bbox"]
        cv2.rectangle(debug, (x, y), (x + w, y + h), (180, 180, 180), 2)

    labels = ["TL", "TR", "BR", "BL"]
    for label, point in zip(labels, ordered_markers):
        x, y = int(round(point[0])), int(round(point[1]))
        cv2.circle(debug, (x, y), 14, (0, 0, 255), 3)
        cv2.putText(
            debug,
            label,
            (x + 12, y - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    cv2.polylines(debug, [ordered_markers.astype(np.int32)], True, (0, 255, 0), 3)
    return debug


def resolve_interpolation(interpolation):
    if interpolation in ("cubic", cv2.INTER_CUBIC):
        return cv2.INTER_CUBIC, "cubic"
    if interpolation in ("linear", cv2.INTER_LINEAR):
        return cv2.INTER_LINEAR, "linear"
    raise ValueError(f"unsupported warp interpolation: {interpolation}")


def preprocess_image(
    image_path,
    save_debug=False,
    save_warped=True,
    interpolation=cv2.INTER_CUBIC,
):
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"failed to read image: {image_path}")

    interpolation_flag, interpolation_name = resolve_interpolation(interpolation)
    ordered_markers, candidates = detect_markers(image)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    warped_gray = warp_page(gray, ordered_markers, interpolation=interpolation_flag)

    warped_path = WARPED_DIR / f"{image_path.stem}.png"

    warped_text = f"warped={warped_path}"
    if save_warped:
        WARPED_DIR.mkdir(parents=True, exist_ok=True)
        if not cv2.imwrite(
            str(warped_path),
            warped_gray,
            [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION],
        ):
            raise ValueError(f"failed to write warped image: {warped_path}")
    else:
        warped_text = f"warped=skipped expected_path={warped_path}"

    debug_text = "debug=skipped"
    if save_debug:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        debug = draw_debug_image(image, ordered_markers, candidates)
        debug_path = DEBUG_DIR / f"{image_path.stem}_markers.jpg"
        if not cv2.imwrite(str(debug_path), debug):
            raise ValueError(f"failed to write debug image: {debug_path}")
        debug_text = f"debug={debug_path}"

    marker_text = ", ".join(
        f"({int(round(point[0]))},{int(round(point[1]))})" for point in ordered_markers
    )
    return (
        (
            f"OK {image_path.name}: markers={marker_text} {warped_text} "
            f"interpolation={interpolation_name} {debug_text}"
        ),
        {
            "name": image_path.stem,
            "path": warped_path,
            "image": warped_gray,
        },
    )


def preprocess_image_task(
    index_and_path,
    save_debug=False,
    save_warped=True,
    interpolation=cv2.INTER_CUBIC,
):
    index, image_path = index_and_path
    try:
        line, warped_record = preprocess_image(
            image_path,
            save_debug=save_debug,
            save_warped=save_warped,
            interpolation=interpolation,
        )
        return index, True, line, warped_record
    except Exception as exc:
        line = f"FAIL {image_path.name}: {type(exc).__name__}: {exc}"
        return index, False, line, None


def run_preprocess(
    input_dir=INPUT_DIR,
    save_debug=False,
    workers=None,
    save_warped=True,
    interpolation=cv2.INTER_CUBIC,
):
    image_paths = list_input_images(input_dir)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    interpolation_flag, interpolation_name = resolve_interpolation(interpolation)

    if not image_paths:
        report = "No input images found. Skipped preprocessing.\n"
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(report, end="")
        return True, []

    worker_count = max(1, int(workers)) if workers else 1
    worker_count = min(worker_count, len(image_paths))
    lines = [
        "handwrite2350 page preprocess report",
        "=" * 40,
        f"worker count: {worker_count}",
        f"save warped PNG: {save_warped}",
        f"warp interpolation: {interpolation_name}",
    ]
    success = True
    warped_records = []
    results = [None] * len(image_paths)

    if worker_count == 1:
        for item in enumerate(image_paths):
            index, ok, line, warped_record = preprocess_image_task(
                item,
                save_debug=save_debug,
                save_warped=save_warped,
                interpolation=interpolation_flag,
            )
            results[index] = (ok, line, warped_record)
    else:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    preprocess_image_task,
                    item,
                    save_debug,
                    save_warped,
                    interpolation_flag,
                )
                for item in enumerate(image_paths)
            ]
            for future in as_completed(futures):
                index, ok, line, warped_record = future.result()
                results[index] = (ok, line, warped_record)

    for ok, line, warped_record in results:
        success = success and ok
        lines.append(line)
        if warped_record is not None:
            warped_records.append(warped_record)

    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")
    return success, warped_records


if __name__ == "__main__":
    ok, _ = run_preprocess()
    raise SystemExit(0 if ok else 1)
