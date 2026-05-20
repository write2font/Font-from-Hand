from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> None:
    print("[write2font]", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run crop -> AI inference -> TTF build for write2font.")
    parser.add_argument("--input", required=True, help="Reference sheet image or directory")
    parser.add_argument("--out-ttf", required=True)
    parser.add_argument("--family-name", required=True)
    parser.add_argument("--model", choices=["LF", "MX"], default="MX")
    parser.add_argument("--weight", required=True)
    parser.add_argument("--python", default="python")
    parser.add_argument("--result-dir", default="write2font/result")
    parser.add_argument("--font-key", default="upload")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    font_key = args.font_key
    png_dir = root / "write2font" / "png" / font_key
    result_root = root / args.result_dir / args.model
    generated_dir = result_root / font_key

    if result_root.exists():
        shutil.rmtree(result_root)

    run(
        [
            args.python,
            "-X",
            "utf8",
            "write2font/crop_ref_sheet.py",
            "--input",
            str(Path(args.input).resolve()),
            "--out-dir",
            str(png_dir),
        ],
        root,
    )

    if args.model == "LF":
        inference_script = "inference_cpu.py"
        model_config = "cfgs/LF/p2/eval.yaml"
        model_args = ["--model", "LF"]
    else:
        inference_script = "inference_cpu.py"
        model_config = "cfgs/MX/eval.yaml"
        model_args = ["--model", "MX"]

    run(
        [
            args.python,
            "-X",
            "utf8",
            inference_script,
            model_config,
            "cfgs/data/eval/kor_png.yaml",
            *model_args,
            "--weight",
            str(Path(args.weight).resolve()),
            "--result_dir",
            str(result_root),
        ],
        root,
    )

    run(
        [
            args.python,
            "-X",
            "utf8",
            "write2font/png_to_ttf.py",
            "--input-dir",
            str(generated_dir),
            "--out-ttf",
            str(Path(args.out_ttf).resolve()),
            "--family-name",
            args.family_name,
        ],
        root,
    )


if __name__ == "__main__":
    main()
