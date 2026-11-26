#!/usr/bin/env python3
"""Проверка иллюстраций репозитория: LFS-указатели, реальные байты, размеры.

Запускается после checkout с lfs: true. Пишет migration/build/media_report.json
и печатает сводку; завершается с ошибкой, если LFS-файл остался указателем.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(os.path.dirname(ROOT), "site", "images")
OUT = os.path.join(ROOT, "build")
POINTER = b"version https://git-lfs.github.com/spec"


def jpeg_size(data: bytes):
    index = 2
    while index < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3):
            height, width = struct.unpack(">HH", data[index + 5:index + 9])
            return width, height
        length = struct.unpack(">H", data[index + 2:index + 4])[0]
        index += 2 + length
    return None


def png_size(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    report = []
    pointers = []
    broken = []
    for dirpath, _, files in os.walk(IMAGES):
        for name in sorted(files):
            if not name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, os.path.join(ROOT, ".."))
            with open(path, "rb") as fh:
                data = fh.read()
            entry = {"path": rel, "bytes": len(data)}
            if data.startswith(POINTER):
                entry["status"] = "lfs-pointer"
                pointers.append(rel)
            else:
                entry["status"] = "ok"
                entry["sha256"] = hashlib.sha256(data).hexdigest()
                size = None
                if name.lower().endswith(".png"):
                    size = png_size(data)
                else:
                    size = jpeg_size(data)
                if size:
                    entry["width"], entry["height"] = size
                else:
                    broken.append(rel)
            report.append(entry)

    with open(os.path.join(OUT, "media_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)

    print("файлов:", len(report))
    print("реальных изображений:", len(report) - len(pointers))
    print("LFS-указателей без содержимого:", len(pointers))
    for rel in pointers[:10]:
        print("  pointer:", rel)
    print("не удалось прочитать размеры:", len(broken))
    for rel in broken[:10]:
        print("  broken:", rel)
    return 1 if pointers or broken else 0


if __name__ == "__main__":
    sys.exit(main())
