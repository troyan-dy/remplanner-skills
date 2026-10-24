"""Вывод CLI-инструментов: строка в stdout или в stderr."""

import sys


def say(text=""):
    """Строка в stdout (как print)."""
    sys.stdout.write(f"{text}\n")


def complain(text):
    """Строка в stderr."""
    sys.stderr.write(f"{text}\n")
