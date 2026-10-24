"""Неизменяемые словари-константы модулей."""

from types import MappingProxyType


def frozen(mapping):
    """Словарь только для чтения (копия mapping)."""
    # frozendict появился только в Python 3.15, а инструменты работают на 3.9+ (CLAUDE.md)
    return MappingProxyType(dict(mapping))  # noqa: WPS483
