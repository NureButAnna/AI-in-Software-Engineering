"""Порядок списку справ (AC-04.3, lab1/docs/requirements.md, розділ 5.3)."""

from __future__ import annotations

from datetime import date

# SQLite порівнює рядки побайтово: Є, І, Ї стоять перед «А», а «ґ» — після «я».
# Тому текстове сортування виконується тут за українською абеткою без урахування регістру.
_UK_ALPHABET = "абвгґдеєжзиіїйклмнопрстуфхцчшщьюя"
_UK_RANK = {letter: index for index, letter in enumerate(_UK_ALPHABET)}
_IGNORED = {"'", "’", "ʼ"}  # апостроф не впливає на порядок


def uk_key(text: str) -> tuple[tuple[int, int], ...]:
    key = []
    for char in text.casefold():
        if char in _IGNORED:
            continue
        if char in _UK_RANK:
            key.append((1, _UK_RANK[char]))
        else:
            key.append((0, ord(char)))  # цифри й латиниця — перед кирилицею
    return tuple(key)


def case_sort_key(case) -> tuple:
    """deadline ASC (без дедлайну — в кінці), далі title А–Я, created_at ASC, id."""
    return (
        case.deadline is None,
        case.deadline or date.min,
        uk_key(case.title),
        case.created_at,
        case.id,
    )
