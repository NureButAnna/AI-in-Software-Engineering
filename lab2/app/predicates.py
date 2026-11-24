"""Чисті предикати фільтрації справ (AC-04.9, lab1/docs/requirements.md, розділи 1.8, 5.4, 5.5).

Не змінюють вхідну справу й не звертаються до БД. value=None означає «не фільтрувати».
"""

from __future__ import annotations

from datetime import date, timedelta

from app.models import TERMINAL_STATUSES

DUE_VALUES = ("overdue", "upcoming")
UPCOMING_DAYS = 14


def matches_status(case, value: str | None) -> bool:
    return value is None or case.status == value


def matches_due(case, value: str | None, today: date | None) -> bool:
    """overdue: deadline < today; upcoming: today <= deadline <= today + 14 днів.

    Справи без дедлайну й у кінцевому статусі не збігаються ні з одним значенням.
    """
    if value is None:
        return True
    if value not in DUE_VALUES:
        raise ValueError(f"Невідоме значення due: {value!r}")
    if today is None:
        raise ValueError("Для фільтра due потрібна дата today")
    if case.deadline is None or case.status in TERMINAL_STATUSES:
        return False
    if value == "overdue":
        return case.deadline < today
    return today <= case.deadline <= today + timedelta(days=UPCOMING_DAYS)
