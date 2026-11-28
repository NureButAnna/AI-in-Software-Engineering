"""Спільні перевірки двох предикатів мікроексперименту (однакові за логікою для обох).

Контракт: чиста функція над справою; value=None означає «не фільтрувати»; інше значення
перевіряється точно; вхід не змінюється; до БД немає звернень.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from types import SimpleNamespace

import pytest

from app.predicates import matches_due
from experiment.status_manual import matches_status

TODAY = date(2026, 11, 9)
STATUSES = ["PREPARING", "SUBMITTED", "IN_REVIEW", "APPROVED", "REJECTED", "CANCELLED"]


def make_case(status="PREPARING", deadline=None):
    return SimpleNamespace(status=status, deadline=deadline)


# --- matches_status ----------------------------------------------------------


@pytest.mark.parametrize("status", STATUSES)
def test_status_none_means_do_not_filter(status):
    assert matches_status(make_case(status), None) is True


@pytest.mark.parametrize("case_status", STATUSES)
@pytest.mark.parametrize("value", STATUSES)
def test_status_exact_comparison(case_status, value):
    assert matches_status(make_case(case_status), value) is (case_status == value)


@pytest.mark.parametrize("value", ["preparing", "Preparing", "PREPARING ", "", "DONE"])
def test_status_is_not_normalized(value):
    assert matches_status(make_case("PREPARING"), value) is False


def test_status_does_not_mutate_input():
    case = make_case("SUBMITTED", date(2026, 1, 1))
    before = deepcopy(case)
    matches_status(case, "SUBMITTED")
    assert case == before


# --- matches_due -------------------------------------------------------------


@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("deadline", [None, date(2026, 1, 1), TODAY, date(2027, 1, 1)])
def test_due_none_means_do_not_filter(status, deadline):
    assert matches_due(make_case(status, deadline), None, TODAY) is True
    assert matches_due(make_case(status, deadline), None, None) is True


@pytest.mark.parametrize(
    ("deadline", "overdue", "upcoming"),
    [
        (date(2026, 11, 8), True, False),    # вчора
        (date(2026, 11, 9), False, True),    # сьогодні — не прострочена, а найближча
        (date(2026, 11, 10), False, True),
        (date(2026, 11, 23), False, True),   # today + 14 включно
        (date(2026, 11, 24), False, False),  # today + 15
        (date(2020, 1, 1), True, False),
        (None, False, False),                # без дедлайну ніколи не збігається
    ],
)
def test_due_boundaries_for_non_terminal_status(deadline, overdue, upcoming):
    for status in ("PREPARING", "SUBMITTED", "IN_REVIEW"):
        case = make_case(status, deadline)
        assert matches_due(case, "overdue", TODAY) is overdue
        assert matches_due(case, "upcoming", TODAY) is upcoming


@pytest.mark.parametrize("status", ["APPROVED", "REJECTED", "CANCELLED"])
@pytest.mark.parametrize("deadline", [date(2026, 11, 1), TODAY, date(2026, 11, 20)])
@pytest.mark.parametrize("value", ["overdue", "upcoming"])
def test_due_terminal_status_never_matches(status, deadline, value):
    assert matches_due(make_case(status, deadline), value, TODAY) is False


def test_due_depends_on_today_argument():
    case = make_case("PREPARING", date(2026, 11, 20))
    assert matches_due(case, "upcoming", date(2026, 11, 9)) is True
    assert matches_due(case, "upcoming", date(2026, 11, 21)) is False
    assert matches_due(case, "overdue", date(2026, 11, 21)) is True


@pytest.mark.parametrize("value", ["OVERDUE", "late", "", "all"])
def test_due_unknown_value_is_rejected(value):
    with pytest.raises(ValueError):
        matches_due(make_case(), value, TODAY)


def test_due_requires_today_when_filtering():
    with pytest.raises(ValueError):
        matches_due(make_case("PREPARING", date(2026, 11, 9)), "overdue", None)


def test_due_does_not_mutate_input():
    case = make_case("SUBMITTED", date(2026, 11, 9))
    before = deepcopy(case)
    matches_due(case, "upcoming", TODAY)
    assert case == before
