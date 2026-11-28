"""Зріз D: видалення справи з каскадами й дашборд (T14–T16)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from app.models import (
    Case,
    CaseDocument,
    CaseInstitution,
    Document,
    Institution,
    Reminder,
    Task,
    User,
)

CASES = "/api/v1/cases"
DASHBOARD = "/api/v1/dashboard"
TODAY = "2026-11-09"
TERMINAL = ["APPROVED", "REJECTED", "CANCELLED"]
NON_TERMINAL = ["PREPARING", "SUBMITTED", "IN_REVIEW"]


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    return response.json()["error"]


def count(db, model) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(model))


@pytest.fixture
def owner_id(auth, db):
    return db.scalar(select(User.id).where(User.email == "user@example.com"))


@pytest.fixture
def add_case(db, owner_id):
    def _add(title="Справа", deadline=None, status="PREPARING", owner=None) -> int:
        case = Case(
            owner_id=owner or owner_id,
            title=title,
            status=status,
            deadline=date.fromisoformat(deadline) if deadline else None,
        )
        db.add(case)
        db.commit()
        return case.id

    return _add


@pytest.fixture
def add_reminder(db, owner_id):
    def _add(reminder_date, case_id=None, text="Нагадування", owner=None) -> int:
        reminder = Reminder(
            owner_id=owner or owner_id,
            case_id=case_id,
            reminder_date=date.fromisoformat(reminder_date),
            text=text,
        )
        db.add(reminder)
        db.commit()
        return reminder.id

    return _add


# --- T14 ---------------------------------------------------------------------


def test_t14_delete_returns_204_and_case_disappears(client, auth, add_case):
    case_id = add_case(deadline="2026-11-01")
    response = client.delete(f"{CASES}/{case_id}", headers=auth)
    assert response.status_code == 204 and response.content == b""
    assert client.get(f"{CASES}/{case_id}", headers=auth).status_code == 404
    assert client.get(CASES, headers=auth).json() == []
    dashboard = client.get(DASHBOARD, params={"today": TODAY}, headers=auth).json()
    assert dashboard["overdue_cases"] == [] and dashboard["upcoming_cases"] == []


@pytest.mark.parametrize("status", TERMINAL)
def test_t14_delete_is_allowed_in_terminal_status(client, auth, add_case, status):
    case_id = add_case(status=status)
    assert client.delete(f"{CASES}/{case_id}", headers=auth).status_code == 204


def test_t14_cascade_removes_tasks_and_links_but_keeps_related_records(
    client, auth, db, add_case, add_reminder, owner_id
):
    case_id = add_case()
    other_case_id = add_case(title="Інша")
    document = Document(owner_id=owner_id, title="Паспорт", received_date=date(2015, 4, 2))
    shared = Document(owner_id=owner_id, title="Спільний", received_date=date(2020, 1, 1))
    institution = Institution(owner_id=owner_id, name="ДМС")
    db.add_all([document, shared, institution, Task(case_id=case_id, title="Фото"),
                Task(case_id=case_id, title="Анкета"), Task(case_id=other_case_id, title="Чужа задача")])
    db.flush()
    db.add_all([
        CaseDocument(case_id=case_id, document_id=document.id),
        CaseDocument(case_id=case_id, document_id=shared.id),
        CaseDocument(case_id=other_case_id, document_id=shared.id),
        CaseInstitution(case_id=case_id, institution_id=institution.id),
    ])
    db.commit()
    reminder_id = add_reminder("2026-12-01", case_id=case_id)
    other_reminder = add_reminder("2026-12-02", case_id=other_case_id)

    assert client.delete(f"{CASES}/{case_id}", headers=auth).status_code == 204

    db.expire_all()
    assert db.scalars(select(Task.title)).all() == ["Чужа задача"]
    assert db.scalars(select(CaseDocument.document_id).order_by(CaseDocument.document_id)).all() == [shared.id]
    assert db.scalar(select(CaseDocument.case_id)) == other_case_id
    assert count(db, CaseInstitution) == 0
    assert count(db, Document) == 2 and count(db, Institution) == 1  # самі записи лишаються
    assert db.get(Reminder, reminder_id).case_id is None  # нагадування лишилось без прив'язки
    assert db.get(Reminder, other_reminder).case_id == other_case_id
    assert db.get(Case, other_case_id) is not None


def test_t14_foreign_or_missing_case_is_404_and_nothing_is_deleted(
    client, auth, db, make_user, add_case
):
    other = make_user("other@example.com")
    foreign = client.post(CASES, json={"title": "Чужа"}, headers=other).json()["id"]
    assert_error(client.delete(f"{CASES}/{foreign}", headers=auth), 404, "NOT_FOUND")
    assert_error(client.delete(f"{CASES}/999", headers=auth), 404, "NOT_FOUND")
    assert count(db, Case) == 1


@pytest.mark.parametrize("case_id", ["0", "-5", "abc"])
def test_t14_invalid_id_is_422(client, auth, case_id):
    assert_error(client.delete(f"{CASES}/{case_id}", headers=auth), 422, "VALIDATION_ERROR")


def test_t14_delete_requires_token(client, auth, add_case):
    case_id = add_case()
    assert_error(client.delete(f"{CASES}/{case_id}"), 401, "AUTH_REQUIRED")


# --- T15 ---------------------------------------------------------------------


def ids(items):
    return [item["id"] for item in items]


def dashboard(client, auth, today=TODAY):
    response = client.get(DASHBOARD, params={"today": today}, headers=auth)
    assert response.status_code == 200
    return response.json()


def test_t15_overdue_boundaries(client, auth, add_case):
    yesterday = add_case("Вчора", "2026-11-08")
    add_case("Сьогодні", "2026-11-09")
    add_case("Без дедлайну")
    assert ids(dashboard(client, auth)["overdue_cases"]) == [yesterday]


def test_t15_upcoming_boundaries_are_inclusive(client, auth, add_case):
    today_case = add_case("Сьогодні", "2026-11-09")
    last = add_case("Останній день", "2026-11-23")  # today + 14
    add_case("Наступного дня після меж", "2026-11-24")
    add_case("Вчора", "2026-11-08")
    add_case("Без дедлайну")
    assert ids(dashboard(client, auth)["upcoming_cases"]) == [today_case, last]


@pytest.mark.parametrize("status", TERMINAL)
def test_t15_terminal_cases_never_appear(client, auth, add_case, status):
    add_case("Прострочена", "2026-11-01", status=status)
    add_case("Найближча", "2026-11-10", status=status)
    body = dashboard(client, auth)
    assert body["overdue_cases"] == [] and body["upcoming_cases"] == []


@pytest.mark.parametrize("status", NON_TERMINAL)
def test_t15_all_non_terminal_statuses_count(client, auth, add_case, status):
    overdue = add_case("Прострочена", "2026-11-01", status=status)
    upcoming = add_case("Найближча", "2026-11-10", status=status)
    body = dashboard(client, auth)
    assert ids(body["overdue_cases"]) == [overdue] and ids(body["upcoming_cases"]) == [upcoming]


def test_t15_lists_use_case_ordering(client, auth, add_case):
    later = add_case("Б", "2026-11-05")
    earlier = add_case("А", "2026-11-05")
    earliest = add_case("Я", "2026-11-01")
    assert ids(dashboard(client, auth)["overdue_cases"]) == [earliest, earlier, later]


def test_t15_reminders_visible_when_date_has_come(client, auth, add_case, add_reminder):
    past = add_reminder("2026-11-01", text="Минуле")
    today_reminder = add_reminder("2026-11-09", text="Сьогодні")
    add_reminder("2026-11-10", text="Завтра")
    body = dashboard(client, auth)
    assert ids(body["due_reminders"]) == [past, today_reminder]
    assert body["due_reminders"][0] == {
        "id": past, "reminder_date": "2026-11-01", "text": "Минуле", "case_id": None
    }


def test_t15_reminder_shown_regardless_of_case_status(client, auth, add_case, add_reminder):
    case_id = add_case(status="APPROVED")
    reminder = add_reminder("2026-11-09", case_id=case_id)
    assert ids(dashboard(client, auth)["due_reminders"]) == [reminder]


def test_t15_reminder_survives_case_deletion_without_link(client, auth, add_case, add_reminder):
    case_id = add_case()
    reminder = add_reminder("2026-11-09", case_id=case_id)
    client.delete(f"{CASES}/{case_id}", headers=auth)
    items = dashboard(client, auth)["due_reminders"]
    assert [(i["id"], i["case_id"]) for i in items] == [(reminder, None)]


def test_t15_empty_dashboard_has_three_empty_arrays(client, auth):
    assert dashboard(client, auth) == {
        "overdue_cases": [], "upcoming_cases": [], "due_reminders": []
    }


def test_t15_dashboard_depends_on_today_parameter(client, auth, add_case):
    case_id = add_case("Справа", "2026-11-20")
    assert ids(dashboard(client, auth, "2026-11-09")["upcoming_cases"]) == [case_id]
    assert dashboard(client, auth, "2026-11-20")["upcoming_cases"][0]["id"] == case_id
    assert ids(dashboard(client, auth, "2026-11-21")["overdue_cases"]) == [case_id]
    assert dashboard(client, auth, "2026-10-01")["upcoming_cases"] == []


def test_t15_dashboard_only_reads(client, auth, db, add_case, add_reminder):
    add_case("Прострочена", "2026-11-01")
    add_reminder("2026-11-01")
    before = [(c.id, c.status, c.updated_at) for c in db.scalars(select(Case))]
    dashboard(client, auth)
    db.expire_all()
    assert before == [(c.id, c.status, c.updated_at) for c in db.scalars(select(Case))]


# --- T16 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"today": ""},
        {"today": "09.11.2026"},
        {"today": "2026-11-31"},
        {"today": "2026-11-09T10:00:00"},
        {"today": TODAY, "extra": "1"},
        {"foo": "bar"},
    ],
)
def test_t16_missing_or_invalid_today_is_422(client, auth, params):
    response = client.get(DASHBOARD, params=params, headers=auth)
    assert_error(response, 422, "VALIDATION_ERROR")
    assert response.json()["error"]["details"]


def test_t16_repeated_today_is_422(client, auth):
    response = client.get(f"{DASHBOARD}?today={TODAY}&today=2026-11-10", headers=auth)
    assert_error(response, 422, "VALIDATION_ERROR")


def test_t16_dashboard_requires_token_before_validation(client):
    assert_error(client.get(DASHBOARD), 401, "AUTH_REQUIRED")
    assert_error(client.get(DASHBOARD, params={"today": TODAY}), 401, "AUTH_REQUIRED")


def test_t16_dashboard_shows_only_own_data(client, auth, make_user, db, add_case, add_reminder):
    other = make_user("other@example.com")
    other_id = db.scalar(select(User.id).where(User.email == "other@example.com"))
    mine = add_case("Моя", "2026-11-01")
    add_case("Чужа", "2026-11-01", owner=other_id)
    my_reminder = add_reminder("2026-11-01")
    add_reminder("2026-11-01", owner=other_id)
    body = dashboard(client, auth)
    assert ids(body["overdue_cases"]) == [mine] and ids(body["due_reminders"]) == [my_reminder]
    other_body = dashboard(client, other)
    assert [c["title"] for c in other_body["overdue_cases"]] == ["Чужа"]
