#!/usr/bin/env python3
"""Build a standalone executable using PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    cmd = [
        "pyinstaller",
        "-n",
        "IGScheduler",
        "--exclude-module=tkinter",
        "--onefile",
        str(root / "main.py"),
    ]
    if sys.platform.startswith("win"):
        cmd.insert(-1, "--add-binary=bin/ffmpeg.exe;bin")

    subprocess.check_call(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
