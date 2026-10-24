#!/usr/bin/env python3
"""Make the Pro build from index.html: the same file with PRO_UNLOCKED set to true.

The output is NOT meant for this repository. By default it goes to a sibling
folder, ../workshop-timers-pro/pro-bundle/, so a stray `git add .` cannot
publish it. Usage:

    python3 scripts/build_pro.py [output_folder]

The script refuses to run if the flag line is missing or appears twice, and it
checks that the result differs from index.html by exactly one line.
"""
import difflib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FREE = "const PRO_UNLOCKED = false;"
PRO = "const PRO_UNLOCKED = true;"
OUT_NAME = "workshop-timer-pro.html"


def build(source: str) -> str:
    if source.count(FREE) != 1:
        raise SystemExit(f"expected exactly one {FREE!r} in index.html, found {source.count(FREE)}")
    result = source.replace(FREE, PRO)
    changed = [d for d in difflib.unified_diff(source.splitlines(), result.splitlines(), lineterm="", n=0)
               if d[:1] in "+-" and d[:3] not in ("+++", "---")]
    if len(changed) != 2:  # one line removed, one added
        raise SystemExit(f"Pro build should differ by exactly one line, differs by {len(changed) // 2}")
    return result


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "workshop-timers-pro" / "pro-bundle"
    out_dir = out_dir.resolve()
    if ROOT in (out_dir, *out_dir.parents):
        raise SystemExit(f"refusing to write the Pro build inside the repository ({out_dir})")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OUT_NAME).write_text(build((ROOT / "index.html").read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {out_dir / OUT_NAME}")


if __name__ == "__main__":
    main()
