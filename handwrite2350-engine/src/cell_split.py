from pathlib import Path

import cv2
import numpy as np


WARPED_DIR = Path("outputs/warped")
CELLS_DIR = Path("outputs/cells")
CONTACT_SHEETS_DIR = Path("outputs/contact_sheets")
REPORT_PATH = Path("outputs/cell_split_report.txt")
CHARSET_PATH = Path("charsets/basiclatin_ksx1001.txt")

COLS = 11
ROWS = 17
CELLS_PER_PAGE = COLS * ROWS
DEFAULT_MARGIN_RATIO = 0.08
IMAGE_EXTENSIONS = {".png"}


def list_warped_images(warped_dir=WARPED_DIR):
    warped_path = Path(warped_dir)
    if not warped_path.exists():
        return []

    return sorted(
        path
        for path in warped_path.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def load_charset_count(path=CHARSET_PATH):
    chars = Path(path).read_text(encoding="utf-8").replace("\r", "").replace("\n", "")
    return len(chars)


def detect_grid_bbox(image):
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


def binarize_page(image):
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    black_pixels = np.count_nonzero(binary == 0)
    white_pixels = np.count_nonzero(binary == 255)
    if black_pixels > white_pixels:
        binary = cv2.bitwise_not(binary)
    return binary


def crop_cell(image, grid_bbox, row, col, margin_ratio=DEFAULT_MARGIN_RATIO):
    x0, y0, x1, y1 = grid_bbox
    grid_width = x1 - x0
    grid_height = y1 - y0

    cell_x0 = x0 + int(round(col * grid_width / COLS))
    cell_x1 = x0 + int(round((col + 1) * grid_width / COLS))
    cell_y0 = y0 + int(round(row * grid_height / ROWS))
    cell_y1 = y0 + int(round((row + 1) * grid_height / ROWS))

    cell_width = cell_x1 - cell_x0
    cell_height = cell_y1 - cell_y0
    margin_x = int(round(cell_width * margin_ratio))
    margin_y = int(round(cell_height * margin_ratio))

    crop_x0 = min(max(cell_x0 + margin_x, 0), image.shape[1])
    crop_x1 = min(max(cell_x1 - margin_x, 0), image.shape[1])
    crop_y0 = min(max(cell_y0 + margin_y, 0), image.shape[0])
    crop_y1 = min(max(cell_y1 - margin_y, 0), image.shape[0])

    if crop_x1 <= crop_x0 or crop_y1 <= crop_y0:
        raise ValueError(f"invalid crop box for row={row}, col={col}")

    return image[crop_y0:crop_y1, crop_x0:crop_x1]


def crop_cell_bounds(image_shape, grid_bbox, row, col, margin_ratio):
    x0, y0, x1, y1 = grid_bbox
    grid_width = x1 - x0
    grid_height = y1 - y0

    cell_x0 = x0 + int(round(col * grid_width / COLS))
    cell_x1 = x0 + int(round((col + 1) * grid_width / COLS))
    cell_y0 = y0 + int(round(row * grid_height / ROWS))
    cell_y1 = y0 + int(round((row + 1) * grid_height / ROWS))

    cell_width = cell_x1 - cell_x0
    cell_height = cell_y1 - cell_y0
    margin_x = int(round(cell_width * margin_ratio))
    margin_y = int(round(cell_height * margin_ratio))

    height, width = image_shape[:2]
    crop_x0 = min(max(cell_x0 + margin_x, 0), width)
    crop_x1 = min(max(cell_x1 - margin_x, 0), width)
    crop_y0 = min(max(cell_y0 + margin_y, 0), height)
    crop_y1 = min(max(cell_y1 - margin_y, 0), height)

    if crop_x1 <= crop_x0 or crop_y1 <= crop_y0:
        raise ValueError(f"invalid crop box for row={row}, col={col}")

    return crop_x0, crop_y0, crop_x1, crop_y1


def crop_cell_pair(color_image, binary_image, grid_bbox, row, col, margin_ratio):
    crop_x0, crop_y0, crop_x1, crop_y1 = crop_cell_bounds(
        color_image.shape,
        grid_bbox,
        row,
        col,
        margin_ratio,
    )
    return (
        color_image[crop_y0:crop_y1, crop_x0:crop_x1],
        binary_image[crop_y0:crop_y1, crop_x0:crop_x1],
    )


def make_contact_sheet(cells_by_position, output_path, thumb_size=72):
    sheet = np.full(
        (ROWS * thumb_size, COLS * thumb_size, 3),
        245,
        dtype=np.uint8,
    )

    for (row, col), cell in cells_by_position.items():
        thumb = cv2.resize(cell, (thumb_size, thumb_size), interpolation=cv2.INTER_AREA)
        y0 = row * thumb_size
        x0 = col * thumb_size
        sheet[y0 : y0 + thumb_size, x0 : x0 + thumb_size] = thumb
        cv2.rectangle(
            sheet,
            (x0, y0),
            (x0 + thumb_size - 1, y0 + thumb_size - 1),
            (210, 210, 210),
            1,
        )

    CONTACT_SHEETS_DIR.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), sheet):
        raise ValueError(f"failed to write contact sheet: {output_path}")


def split_page(
    image_path,
    page_index,
    glyph_count,
    margin_ratio=DEFAULT_MARGIN_RATIO,
    save_cells=False,
    save_contact_sheet=False,
):
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"failed to read warped image: {image_path}")

    return split_page_image(
        image,
        image_path.stem,
        page_index,
        glyph_count,
        margin_ratio=margin_ratio,
        save_cells=save_cells,
        save_contact_sheet=save_contact_sheet,
    )


def split_page_image(
    image,
    page_name,
    page_index,
    glyph_count,
    margin_ratio=DEFAULT_MARGIN_RATIO,
    save_cells=False,
    save_contact_sheet=False,
):
    page_dir = CELLS_DIR / page_name

    if save_cells:
        page_dir.mkdir(parents=True, exist_ok=True)
        for old_cell in list(page_dir.glob("*.jpg")) + list(page_dir.glob("*.png")):
            old_cell.unlink()

    grid_bbox = detect_grid_bbox(image)
    cells_by_position = {} if save_contact_sheet else None
    cell_records = []
    saved_count = 0

    for row in range(ROWS):
        for col in range(COLS):
            glyph_index = page_index * CELLS_PER_PAGE + row * COLS + col
            if glyph_index >= glyph_count:
                continue

            crop_x0, crop_y0, crop_x1, crop_y1 = crop_cell_bounds(
                image.shape,
                grid_bbox,
                row,
                col,
                margin_ratio,
            )
            gray_cell = image[crop_y0:crop_y1, crop_x0:crop_x1]

            if save_cells:
                cell_path = page_dir / f"r{row:02d}_c{col:02d}.png"
                if not cv2.imwrite(str(cell_path), gray_cell):
                    raise ValueError(f"failed to write cell image: {cell_path}")

            if save_contact_sheet:
                contact_cell = image[crop_y0:crop_y1, crop_x0:crop_x1]
                if len(contact_cell.shape) == 2:
                    contact_cell = cv2.cvtColor(contact_cell, cv2.COLOR_GRAY2BGR)
                cells_by_position[(row, col)] = contact_cell

            cell_records.append(
                {
                    "index": glyph_index,
                    "page": page_name,
                    "row": row,
                    "col": col,
                    "gray_shape": gray_cell.shape,
                    "gray_bytes": gray_cell.tobytes(),
                }
            )
            saved_count += 1

    contact_path = None
    if save_contact_sheet:
        contact_path = CONTACT_SHEETS_DIR / f"{page_name}_contact.jpg"
        make_contact_sheet(cells_by_position, contact_path)

    return saved_count, grid_bbox, contact_path, cell_records


def run_cell_split(
    warped_dir=WARPED_DIR,
    charset_path=CHARSET_PATH,
    margin_ratio=DEFAULT_MARGIN_RATIO,
    save_cells=False,
    save_contact_sheets=False,
    warped_records=None,
):
    image_paths = [] if warped_records else list_warped_images(warped_dir)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not image_paths and not warped_records:
        report = "No warped images found. Skipped cell split.\n"
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(report, end="")
        return True, []

    glyph_count = load_charset_count(charset_path)
    total_count = 0
    all_cell_records = []
    success = True
    lines = [
        "handwrite2350 cell split report",
        "=" * 40,
        f"Expected glyph count: {glyph_count}",
        f"Pages found: {len(warped_records) if warped_records else len(image_paths)}",
        f"Saved cell PNGs: {save_cells}",
        "Binary page mode: False",
        "Glyph threshold mode: grayscale resize then final threshold",
        f"In-memory warped input: {bool(warped_records)}",
        "",
    ]

    page_sources = warped_records if warped_records else image_paths
    for page_index, page_source in enumerate(page_sources):
        try:
            if warped_records:
                image_name = page_source["name"]
                saved_count, grid_bbox, contact_path, cell_records = split_page_image(
                    page_source["image"],
                    image_name,
                    page_index,
                    glyph_count,
                    margin_ratio=margin_ratio,
                    save_cells=save_cells,
                    save_contact_sheet=save_contact_sheets,
                )
            else:
                image_name = page_source.name
                saved_count, grid_bbox, contact_path, cell_records = split_page(
                    page_source,
                    page_index,
                    glyph_count,
                    margin_ratio=margin_ratio,
                    save_cells=save_cells,
                    save_contact_sheet=save_contact_sheets,
                )
            total_count += saved_count
            all_cell_records.extend(cell_records)
            contact_text = contact_path if contact_path else "skipped"
            lines.append(
                f"OK {image_name}: cells={saved_count} "
                f"grid_bbox={grid_bbox} contact={contact_text}"
            )
        except Exception as exc:
            success = False
            image_name = page_source.get("name", "memory") if warped_records else page_source.name
            lines.append(f"FAIL {image_name}: {type(exc).__name__}: {exc}")

    lines.extend(
        [
            "",
            f"Total saved cells: {total_count}",
            f"Matches expected glyph count: {total_count == glyph_count}",
        ]
    )

    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")
    return success and total_count == glyph_count, all_cell_records


if __name__ == "__main__":
    ok, _ = run_cell_split(save_cells=True, save_contact_sheets=True)
    raise SystemExit(0 if ok else 1)
