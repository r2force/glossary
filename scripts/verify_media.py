#!/usr/bin/env python3
"""Decode site images, verify Git LFS objects and compare published image bytes."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import warnings

from PIL import Image, UnidentifiedImageError

REPO = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif", ".bmp", ".tif", ".tiff"}
POINTER = b"version https://git-lfs.github.com/spec/v1"
LFS_OBJECT = re.compile(rb"oid sha256:([0-9a-f]{64})\nsize ([0-9]+)(?:\n|$)")


def image_info(data: bytes) -> dict:
    """Verify the container and decode every frame, rejecting truncated images."""
    if data.startswith(POINTER):
        raise ValueError("Git LFS pointer instead of image bytes; run git lfs pull")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                info = {"format": image.format, "width": image.width, "height": image.height}
                for frame in range(getattr(image, "n_frames", 1)):
                    image.seek(frame)
                    image.load()
                return info
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError,
            Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError(f"cannot decode image: {exc}") from exc


def indexed_objects(source: Path) -> dict[str, bytes]:
    """Read pointer blobs from the Git index without requiring a git-lfs executable."""
    result = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise ValueError("source must belong to a Git repository for LFS verification")
    git_root = Path(result.stdout.strip()).resolve()
    relative = (source / "images").relative_to(git_root).as_posix()
    entries = subprocess.run(
        ["git", "-C", str(git_root), "ls-files", "--stage", "-z", "--", relative],
        check=True, capture_output=True,
    ).stdout
    blobs = {}
    for entry in entries.split(b"\0"):
        if not entry:
            continue
        meta, path_bytes = entry.split(b"\t", 1)
        _, oid, stage = meta.split()
        path = git_root / path_bytes.decode("utf-8")
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if stage != b"0":
            raise ValueError(f"unresolved Git conflict: {path}")
        blobs[path.relative_to(source).as_posix()] = subprocess.run(
            ["git", "-C", str(git_root), "cat-file", "blob", oid.decode()],
            check=True, capture_output=True,
        ).stdout
    return blobs


def verify(source: Path, built: Path | None = None) -> dict:
    source = source.resolve()
    errors = []
    entries = []
    image_root = source / "images"
    images = sorted(p for p in image_root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        errors.append(f"no images found in {image_root}")
    try:
        indexed = indexed_objects(source)
    except (ValueError, subprocess.CalledProcessError) as exc:
        errors.append(str(exc))
        indexed = {}
    current = {p.relative_to(source).as_posix() for p in images}
    for missing in sorted(set(indexed) - current):
        errors.append(f"tracked image missing from source: {missing}")
    lfs_checked = 0
    for path in images:
        relative = path.relative_to(source).as_posix()
        data = path.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        entry = {"path": relative, "bytes": len(data), "sha256": sha256}
        try:
            entry.update(image_info(data))
            entry["status"] = "ok"
        except ValueError as exc:
            entry["status"] = "error"
            errors.append(f"{relative}: {exc}")
        pointer = indexed.get(relative, b"")
        if pointer.startswith(POINTER):
            match = LFS_OBJECT.search(pointer)
            if match is None:
                errors.append(f"{relative}: malformed Git LFS pointer in index")
            elif match[1].decode() != sha256 or int(match[2]) != len(data):
                errors.append(f"{relative}: bytes differ from Git LFS oid/size in index; stage intentional image changes with git lfs installed")
            else:
                lfs_checked += 1
        if built is not None:
            target = built / relative
            if not target.is_file():
                errors.append(f"{relative}: missing from built site")
            elif target.read_bytes() != data:
                errors.append(f"{relative}: built image differs from source")
        entries.append(entry)
    if built is not None:
        published = {p.relative_to(built).as_posix() for p in (built / "images").rglob("*")
                     if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES}
        for extra in sorted(published - current):
            errors.append(f"unexpected image in built site: {extra}")
    return {"images": len(images), "lfs_verified": lfs_checked, "files": entries, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO / "site")
    parser.add_argument("--site", type=Path, help="also compare every built image with its source")
    parser.add_argument("--report", type=Path, default=REPO / "reports/verify_media.json")
    args = parser.parse_args()
    report = verify(args.source, args.site.resolve() if args.site else None)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Images: {report['images']}; LFS objects verified: {report['lfs_verified']}; errors: {len(report['errors'])}")
    for error in report["errors"]:
        print(f"  ERROR: {error}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
