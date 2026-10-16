#!/usr/bin/env python3
"""save_shots.py screenshots/run-NN_<name>.png… — копирует последние N снимков, сохранённых расширением Claude in Chrome
(zoom с save_to_disk), в DEST по порядку съёмки: первый снимок → первый DEST.
Порядок DEST = порядок планов в пакете браузера. Печатает размер каждого снимка для сверки."""

import glob
import os
import shutil
import struct
import sys
import tempfile


def png_size(path):
    """Ширина и высота из заголовка PNG (чанк IHDR сразу после сигнатуры)."""
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def temp_dirs():
    """Где расширение оставляет снимки: системная временная папка (+ папки пользователей macOS в /var/folders)."""
    dirs = {tempfile.gettempdir(), "/tmp"}
    dirs.update(glob.glob("/var/folders/*/*/T"))
    for var in ("TMPDIR", "TEMP", "TMP"):
        if os.environ.get(var):
            dirs.add(os.environ[var])
    return dirs


if __name__ == "__main__":
    dests = sys.argv[1:]
    if not dests:
        sys.exit(__doc__)
    shots = set()
    for tmp in temp_dirs():
        shots.update(glob.glob(os.path.join(tmp, "claude-chrome-screenshots-*", "*.png")))
    shots = sorted(shots, key=os.path.getmtime)[-len(dests) :]
    if len(shots) < len(dests):
        sys.exit(f"нашлось {len(shots)} снимков, нужно {len(dests)}")
    for src, dst in zip(shots, dests):
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        shutil.copyfile(src, dst)
        size = png_size(dst)
        print(f"{os.path.basename(src)} → {dst} ({'×'.join(map(str, size)) if size else 'не PNG'})")
