#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

LIMIT_BYTES = 100 * 1024
IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "data/exchange",
    "data/dis_captures",
    "data/out",
    "data/logs",
}


def is_ignored(path: Path) -> bool:
    parts = path.parts
    joined = "/".join(parts)
    return any(part in IGNORE_DIRS for part in parts) or any(joined.startswith(d + "/") for d in IGNORE_DIRS)


def main() -> int:
    root = Path.cwd()
    large_files: list[tuple[int, Path]] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_ignored(rel):
            continue
        size = path.stat().st_size
        if size > LIMIT_BYTES:
            large_files.append((size, rel))

    if not large_files:
        print(f"OK: no tracked-candidate files over {LIMIT_BYTES} bytes")
        return 0

    print(f"Files over {LIMIT_BYTES} bytes:")
    for size, rel in sorted(large_files, reverse=True):
        print(f"{size:>10}  {rel}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
