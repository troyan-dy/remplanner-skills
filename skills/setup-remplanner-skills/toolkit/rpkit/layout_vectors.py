"""Векторы на плоскости плана — кортежи (x, y): разность, скалярное произведение, сдвиг, угол по косинусу.
Порядок операций — как в исходных формулах, чтобы результаты совпадали до бита."""

import math


def minus(first, second):
    """first − second."""
    return (
        first[0] - second[0],
        first[1] - second[1],
    )


def dot(first, second):
    """Скалярное произведение."""
    along_x = first[0] * second[0]
    return along_x + first[1] * second[1]


def moved(point, direction, length):
    """Точка point, сдвинутая на length по direction."""
    return (
        point[0] + direction[0] * length,
        point[1] + direction[1] * length,
    )


def scaled(vector, factor):
    """vector / factor по каждой координате."""
    return vector[0] / factor, vector[1] / factor


def negated(vector):
    """−vector."""
    return -vector[0], -vector[1]


def degrees_of(cosine):
    """Угол в градусах по косинусу (косинус обрезается до [−1, 1])."""
    clamped = max(-1, min(1, cosine))
    return math.degrees(math.acos(clamped))
