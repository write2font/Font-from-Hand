from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a character JSON file from PNG filenames.")
    parser.add_argument("--png-dir", default="write2font/png", help="Directory containing <char>.png files")
    parser.add_argument("--out", default="write2font/ref_chars.json", help="JSON file to write")
    parser.add_argument("--backup", action="store_true", help="Back up the existing output file before writing")
    args = parser.parse_args()

    png_dir = Path(args.png_dir)
    out_path = Path(args.out)

    if not png_dir.is_dir():
        raise FileNotFoundError(f"PNG directory not found: {png_dir}")

    if args.backup and out_path.exists():
        backup_path = out_path.with_name(f"{out_path.stem}_backup{out_path.suffix}")
        shutil.copy(out_path, backup_path)
        print(f"Backed up existing JSON to {backup_path}")

    chars = sorted(path.stem for path in png_dir.iterdir() if path.suffix.lower() == ".png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(chars, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"Wrote {len(chars)} characters to {out_path}")


if __name__ == "__main__":
    main()
