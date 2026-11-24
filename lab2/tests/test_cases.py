"""Зріз B: створення й читання справ (T06–T09)."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import func, select

from app.models import (
    Case,
    CaseDocument,
    CaseInstitution,
    Document,
    Institution,
    Task,
    User,
)

CASES = "/api/v1/cases"


def assert_error(response, status, code):
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    assert error["details"] is not None
    return error


def count_cases(db) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Case))


# --- T06 ---------------------------------------------------------------------


def test_t06_create_minimal_case(client, auth):
    response = client.post(CASES, json={"title": "Отримання паспорта"}, headers=auth)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "status", "deadline", "created_at", "updated_at"}
    assert body["title"] == "Отримання паспорта"
    assert body["status"] == "PREPARING"
    assert body["deadline"] is None
    assert body["created_at"].endswith("Z") and body["created_at"] == body["updated_at"]


def test_t06_create_with_deadline_and_trimmed_title(client, auth):
    response = client.post(
        CASES, json={"title": "  Віза  до  Польщі ", "deadline": "2026-11-30"}, headers=auth
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Віза  до  Польщі"  # лише крайні пробіли
    assert response.json()["deadline"] == "2026-11-30"


def test_t06_explicit_null_deadline_is_allowed(client, auth):
    response = client.post(CASES, json={"title": "A", "deadline": None}, headers=auth)
    assert response.status_code == 201 and response.json()["deadline"] is None


def test_t06_created_case_is_listed_and_owner_is_not_exposed(client, auth):
    created = client.post(CASES, json={"title": "Справа"}, headers=auth).json()
    listed = client.get(CASES, headers=auth).json()
    assert [c["id"] for c in listed] == [created["id"]]
    assert "owner_id" not in listed[0]


# --- T07 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": ""},
        {"title": "   "},
        {"title": None},
        {"title": 5},
        {"title": "Справа", "deadline": "2026-02-30"},
        {"title": "Справа", "deadline": "30.11.2026"},
        {"title": "Справа", "deadline": "2026-11-30T10:00:00Z"},
        {"title": "Справа", "deadline": 20261130},
        {"title": "Справа", "status": "APPROVED"},
        {"title": "Справа", "status": "PREPARING"},
        {"title": "Справа", "owner_id": 99},
        {"title": "Справа", "id": 1},
        {"title": "Справа", "created_at": "2026-01-01T00:00:00Z"},
        {"deadline": "2026-11-30"},
    ],
)
def test_t07_create_invalid_is_422_and_creates_nothing(client, auth, db, payload):
    error = assert_error(client.post(CASES, json=payload, headers=auth), 422, "VALIDATION_ERROR")
    assert error["details"]
    assert count_cases(db) == 0


def test_t07_leap_day_is_valid_and_non_leap_is_not(client, auth):
    ok = client.post(CASES, json={"title": "A", "deadline": "2028-02-29"}, headers=auth)
    bad = client.post(CASES, json={"title": "A", "deadline": "2027-02-29"}, headers=auth)
    assert ok.status_code == 201 and bad.status_code == 422


# --- T08 ---------------------------------------------------------------------


def test_t08_list_empty_is_200_empty_array(client, auth):
    response = client.get(CASES, headers=auth)
    assert response.status_code == 200 and response.json() == []


def test_t08_details_match_created_data(client, auth):
    created = client.post(
        CASES, json={"title": "Паспорт", "deadline": "2026-12-01"}, headers=auth
    ).json()
    response = client.get(f"{CASES}/{created['id']}", headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert {k: body[k] for k in created} == created
    assert body["tasks"] == [] and body["documents"] == [] and body["institutions"] == []


def test_t08_unknown_id_is_404(client, auth):
    assert_error(client.get(f"{CASES}/12345", headers=auth), 404, "NOT_FOUND")


@pytest.mark.parametrize("case_id", ["0", "-1", "abc", "1.5"])
def test_t08_invalid_path_id_is_422(client, auth, case_id):
    assert_error(client.get(f"{CASES}/{case_id}", headers=auth), 422, "VALIDATION_ERROR")


def test_t08_foreign_case_looks_like_missing_one(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    alice_case = client.post(CASES, json={"title": "Alice"}, headers=alice).json()
    client.post(CASES, json={"title": "Bob"}, headers=bob)

    foreign = client.get(f"{CASES}/{alice_case['id']}", headers=bob)
    missing = client.get(f"{CASES}/9999", headers=bob)
    assert_error(foreign, 404, "NOT_FOUND")
    assert foreign.json() == missing.json()  # існування чужого запису не розкривається
    assert [c["title"] for c in client.get(CASES, headers=bob).json()] == ["Bob"]
    assert [c["title"] for c in client.get(CASES, headers=alice).json()] == ["Alice"]


def test_t08_details_include_tasks_documents_institutions(client, auth, db):
    case = client.post(CASES, json={"title": "Справа"}, headers=auth).json()
    owner = db.scalar(select(User)).id
    db.add_all(
        [
            Task(case_id=case["id"], title="Фото", is_completed=True),
            Task(case_id=case["id"], title="Анкета", is_completed=False),
            Document(owner_id=owner, title="Паспорт", received_date=date(2015, 4, 2)),
            Institution(owner_id=owner, name="ДМС"),
            Institution(owner_id=owner, name="Ґміна"),
            Institution(owner_id=owner, name="Агенція"),
        ]
    )
    db.flush()
    document_id = db.scalar(select(Document.id))
    db.add(CaseDocument(case_id=case["id"], document_id=document_id))
    for institution_id in db.scalars(select(Institution.id)).all():
        db.add(CaseInstitution(case_id=case["id"], institution_id=institution_id))
    db.commit()

    body = client.get(f"{CASES}/{case['id']}", headers=auth).json()
    assert body["tasks"] == [
        {"id": 1, "title": "Фото", "is_completed": True},
        {"id": 2, "title": "Анкета", "is_completed": False},
    ]
    assert body["documents"] == [{"id": 1, "title": "Паспорт", "received_date": "2015-04-02"}]
    assert [i["name"] for i in body["institutions"]] == ["Агенція", "Ґміна", "ДМС"]


# --- T09 ---------------------------------------------------------------------


def titles(client, auth):
    return [c["title"] for c in client.get(CASES, headers=auth).json()]


def test_t09_deadline_ascending_and_no_deadline_last(client, auth):
    client.post(CASES, json={"title": "Без дедлайну"}, headers=auth)
    client.post(CASES, json={"title": "Пізніше", "deadline": "2026-12-31"}, headers=auth)
    client.post(CASES, json={"title": "Раніше", "deadline": "2026-01-05"}, headers=auth)
    assert titles(client, auth) == ["Раніше", "Пізніше", "Без дедлайну"]


def test_t09_same_deadline_sorted_by_ukrainian_alphabet_case_insensitive(client, auth):
    expected = ["абрикос", "Бакалія", "Гора", "Ґанок", "Дім", "Єдність", "Іванів", "Їжак", "Яблуко"]
    for title in reversed(expected):
        client.post(CASES, json={"title": title, "deadline": "2026-05-01"}, headers=auth)
    assert titles(client, auth) == expected


def test_t09_status_does_not_change_order(client, auth, db):
    first = client.post(CASES, json={"title": "Б", "deadline": "2026-05-01"}, headers=auth).json()
    client.post(CASES, json={"title": "А", "deadline": "2026-05-01"}, headers=auth)
    db.get(Case, first["id"]).status = "CANCELLED"
    db.commit()
    assert titles(client, auth) == ["А", "Б"]


def test_t09_equal_deadline_and_title_fall_back_to_created_at(client, auth, db):
    owner = db.scalar(select(User)).id
    later = Case(owner_id=owner, title="Однакова", deadline=date(2026, 5, 1),
                 created_at=datetime(2026, 3, 1), updated_at=datetime(2026, 3, 1))
    earlier = Case(owner_id=owner, title="Однакова", deadline=date(2026, 5, 1),
                   created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1))
    db.add_all([later, earlier])  # id раніше створеної справи більший, ніж у пізнішої
    db.commit()
    ids = [c["id"] for c in client.get(CASES, headers=auth).json()]
    assert ids == [earlier.id, later.id]


def test_t09_sort_key_helpers():
    from app.sorting import uk_key

    assert uk_key("Іванів") < uk_key("Їжак") < uk_key("Яблуко")
    assert uk_key("Ґанок") > uk_key("Гора") and uk_key("Ґанок") < uk_key("Дім")
    assert uk_key("Єдність") > uk_key("Дім") and uk_key("Єдність") < uk_key("Іванів")
    assert uk_key("Об'єкт") == uk_key("Обєкт")  # апостроф ігнорується
    assert uk_key("Zebra") < uk_key("Абрикос")  # латиниця й цифри — перед кирилицею
