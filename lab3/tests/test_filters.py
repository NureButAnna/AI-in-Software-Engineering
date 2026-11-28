"""Зріз E: фільтри списку справ status, due і їх поєднання (T17–T19)."""

from __future__ import annotations

from datetime import date

import pytest

from app.models import Case

CASES = "/api/v1/cases"
TODAY = "2026-11-09"


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    return response.json()["error"]


@pytest.fixture
def seed(db, auth):
    """Чотири справи з різними поєднаннями статусу й дедлайну (today = 2026-11-09)."""
    from sqlalchemy import select

    from app.models import User

    owner = db.scalar(select(User.id))
    rows = {
        "overdue_prep": ("PREPARING", "2026-11-01"),
        "overdue_review": ("IN_REVIEW", "2026-11-05"),
        "upcoming_prep": ("PREPARING", "2026-11-15"),
        "approved_old": ("APPROVED", "2026-10-01"),
        "no_deadline": ("PREPARING", None),
        "far_future": ("SUBMITTED", "2027-05-05"),
    }
    ids = {}
    for key, (status, deadline) in rows.items():
        case = Case(
            owner_id=owner, title=key, status=status,
            deadline=date.fromisoformat(deadline) if deadline else None,
        )
        db.add(case)
        db.commit()
        ids[key] = case.id
    return ids


def titles(client, auth, **params):
    response = client.get(CASES, params=params, headers=auth)
    assert response.status_code == 200, response.text
    return [c["title"] for c in response.json()]


# --- T17 ---------------------------------------------------------------------


def test_t17_status_filter_alone(client, auth, seed):
    assert titles(client, auth, status="PREPARING") == ["overdue_prep", "upcoming_prep", "no_deadline"]
    assert titles(client, auth, status="APPROVED") == ["approved_old"]


def test_t17_status_filter_without_matches_is_200_and_empty(client, auth, seed):
    assert titles(client, auth, status="REJECTED") == []


def test_t17_no_filters_returns_everything_in_order(client, auth, seed):
    assert titles(client, auth) == [
        "approved_old", "overdue_prep", "overdue_review", "upcoming_prep", "far_future", "no_deadline"
    ]


# --- T18 ---------------------------------------------------------------------


def test_t18_due_overdue_alone(client, auth, seed):
    assert titles(client, auth, due="overdue", today=TODAY) == ["overdue_prep", "overdue_review"]


def test_t18_due_upcoming_alone(client, auth, seed):
    assert titles(client, auth, due="upcoming", today=TODAY) == ["upcoming_prep"]


@pytest.mark.parametrize(
    ("deadline", "due", "expected"),
    [
        ("2026-11-08", "overdue", True),
        ("2026-11-09", "overdue", False),   # сьогодні не є простроченою
        ("2026-11-09", "upcoming", True),
        ("2026-11-23", "upcoming", True),   # today + 14 включно
        ("2026-11-24", "upcoming", False),
        (None, "overdue", False),
        (None, "upcoming", False),
    ],
)
def test_t18_due_boundaries(client, auth, db, deadline, due, expected):
    from sqlalchemy import select

    from app.models import User

    db.add(Case(owner_id=db.scalar(select(User.id)), title="Межа",
                deadline=date.fromisoformat(deadline) if deadline else None))
    db.commit()
    assert (titles(client, auth, due=due, today=TODAY) == ["Межа"]) is expected


def test_t18_due_depends_on_today(client, auth, seed):
    assert titles(client, auth, due="overdue", today="2026-11-16") == [
        "overdue_prep", "overdue_review", "upcoming_prep"
    ]
    assert titles(client, auth, due="upcoming", today="2026-11-16") == []
    # today + 14 = 2026-11-15: межа вікна «найближчі» включається
    assert titles(client, auth, due="upcoming", today="2026-11-01") == [
        "overdue_prep", "overdue_review", "upcoming_prep"
    ]


def test_t18_today_alone_is_accepted_and_ignored(client, auth, seed):
    assert len(titles(client, auth, today=TODAY)) == 6


def test_t18_terminal_cases_are_not_overdue(client, auth, seed):
    assert "approved_old" not in titles(client, auth, due="overdue", today=TODAY)


# --- T19 ---------------------------------------------------------------------


def test_t19_two_filters_return_intersection_not_union(client, auth, seed):
    assert titles(client, auth, status="PREPARING", due="overdue", today=TODAY) == ["overdue_prep"]
    assert titles(client, auth, status="IN_REVIEW", due="overdue", today=TODAY) == ["overdue_review"]
    assert titles(client, auth, status="PREPARING", due="upcoming", today=TODAY) == ["upcoming_prep"]


def test_t19_combination_without_matches_is_200_and_empty(client, auth, seed):
    assert titles(client, auth, status="APPROVED", due="overdue", today=TODAY) == []
    assert titles(client, auth, status="SUBMITTED", due="upcoming", today=TODAY) == []


@pytest.mark.parametrize(
    "query",
    [
        "status=DONE",
        "status=preparing",
        "status=",
        "due=late",
        "due=OVERDUE",
        "due=overdue",                      # без today
        "due=overdue&today=",
        "due=overdue&today=2026-02-30",
        "due=overdue&today=09.11.2026",
        "today=not-a-date",
        "page=2",
        "status=PREPARING&sort=title",
        "status=PREPARING&status=SUBMITTED",
        "due=overdue&due=upcoming&today=2026-11-09",
    ],
)
def test_t19_invalid_query_is_422_not_empty_list(client, auth, seed, query):
    error = assert_error(client.get(f"{CASES}?{query}", headers=auth), 422, "VALIDATION_ERROR")
    assert error["details"]


def test_t19_filters_apply_only_to_own_cases(client, auth, make_user, seed):
    other = make_user("other@example.com")
    client.post(CASES, json={"title": "Чужа", "deadline": "2026-11-01"}, headers=other)
    assert "Чужа" not in titles(client, auth, due="overdue", today=TODAY)
    assert titles(client, other, due="overdue", today=TODAY) == ["Чужа"]


def test_t19_invalid_query_requires_token_first(client):
    assert_error(client.get(f"{CASES}?status=DONE"), 401, "AUTH_REQUIRED")
