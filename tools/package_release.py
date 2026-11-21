"""Đóng gói bản phát hành chạy được cho GitHub Release v1.0.0.

Chạy:
    python3 tools/package_release.py [--out dist/quan-an-cho-noi-v1.0.0.zip]
"""

import argparse
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOP_FILES = ("game.contract.json", "README.md", "CHANGELOG.md", "LICENSE", "CREDITS.md")

RUN_SH = """#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m chonoi.live --mode day --days 5 "$@"
"""

RUN_BAT = """@echo off
cd /d "%~dp0"
python -m chonoi.live --mode day --days 5 %*
"""


def build_package(out_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fname in TOP_FILES:
            src = os.path.join(ROOT, fname)
            if os.path.exists(src):
                zf.write(src, arcname=f"quan-an-cho-noi-v1.0.0/{fname}")
        chonoi_dir = os.path.join(ROOT, "chonoi")
        for dirpath, dirnames, filenames in os.walk(chonoi_dir):
            dirnames[:] = [d for d in sorted(dirnames) if d != "__pycache__"]
            for fn in sorted(filenames):
                if fn.endswith(".pyc"):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, ROOT).replace("\\", "/")
                zf.write(full, arcname=f"quan-an-cho-noi-v1.0.0/{rel}")

        zi_sh = zipfile.ZipInfo("quan-an-cho-noi-v1.0.0/run.sh")
        zi_sh.external_attr = 0o755 << 16
        zf.writestr(zi_sh, RUN_SH.encode("utf-8"))
        zf.writestr("quan-an-cho-noi-v1.0.0/run.bat", RUN_BAT.encode("utf-8"))
    return out_path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Đóng gói bản phát hành Quán Ăn Chợ Nổi v1.0.0.")
    p.add_argument("--out", default=os.path.join(ROOT, "dist", "quan-an-cho-noi-v1.0.0.zip"))
    a = p.parse_args(argv)
    out = build_package(a.out)
    print(f"Đã đóng gói thành công: {out} ({os.path.getsize(out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
