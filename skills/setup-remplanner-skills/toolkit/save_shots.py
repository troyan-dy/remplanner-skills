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

from rpkit.console import say

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# заголовок PNG: сигнатура (8 байт), длина чанка (4), тип чанка IHDR (4), ширина и высота (по 4)
CHUNK_TYPE_AT = 12
SIZE_AT = 16
HEADER_BYTES = 24
TEMP_VARS = ("TMPDIR", "TEMP", "TMP")


def png_size(path):
    """Ширина и высота из заголовка PNG (чанк IHDR сразу после сигнатуры)."""
    with open(path, "rb") as png:
        head = png.read(HEADER_BYTES)
    signature = head[:len(PNG_SIGNATURE)]
    if signature != PNG_SIGNATURE or head[CHUNK_TYPE_AT:SIZE_AT] != b"IHDR":
        return None
    return struct.unpack(">II", head[SIZE_AT:HEADER_BYTES])


def temp_dirs():
    """Где расширение оставляет снимки: системная временная папка (+ папки пользователей macOS в /var/folders)."""
    dirs = {tempfile.gettempdir(), "/tmp"}
    dirs.update(glob.glob("/var/folders/*/*/T"))
    dirs.update(
        os.environ[name] for name in TEMP_VARS if os.environ.get(name)
    )
    return dirs


def latest_shots(count):
    """Последние count снимков по времени изменения (или меньше, если столько нет)."""
    shots = set()
    for folder in temp_dirs():
        pattern = os.path.join(folder, "claude-chrome-screenshots-*", "*.png")
        shots.update(glob.glob(pattern))
    return sorted(shots, key=os.path.getmtime)[-count:]


def copy_shot(source, dest):
    """Копирует снимок и печатает его размер."""
    folder = os.path.dirname(os.path.abspath(dest))
    os.makedirs(folder, exist_ok=True)
    shutil.copyfile(source, dest)
    size = png_size(dest)
    shown = "×".join(map(str, size)) if size else "не PNG"
    name = os.path.basename(source)
    say(f"{name} → {dest} ({shown})")


if __name__ == "__main__":
    dests = sys.argv[1:]
    if not dests:
        sys.exit(__doc__)
    shots = latest_shots(len(dests))
    if len(shots) < len(dests):
        sys.exit(f"нашлось {len(shots)} снимков, нужно {len(dests)}")
    for shot, dest in zip(shots, dests):
        copy_shot(shot, dest)
