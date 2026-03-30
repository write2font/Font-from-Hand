"""
cli_utils.py - CLI 래퍼 공통 유틸리티
"""
import json
import sys
import os


def exit_error(msg: str) -> None:
    print(json.dumps({"error": msg}, ensure_ascii=False))
    sys.exit(1)


def load_json_file(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def setup_path() -> None:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
