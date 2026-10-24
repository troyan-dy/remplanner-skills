"""Чтение и запись файлов набора: JSON и текст в UTF-8."""

import json

ENCODING = "utf-8"


def read_json(path):
    """JSON из файла."""
    with open(path, encoding=ENCODING) as source:
        return json.load(source)


def write_json(path, document, **options):
    """JSON в файл; options — как у json.dump (ensure_ascii, indent, separators…)."""
    with open(path, "w", encoding=ENCODING) as target:
        json.dump(document, target, **options)


def read_text(path):
    """Текст файла целиком."""
    with open(path, encoding=ENCODING) as source:
        return source.read()


def read_lines(path):
    """Строки файла без перевода строки в конце."""
    with open(path, encoding=ENCODING) as source:
        return [line.rstrip("\n") for line in source]


def write_text(path, text):
    """Текст в файл."""
    with open(path, "w", encoding=ENCODING) as target:
        target.write(text)
