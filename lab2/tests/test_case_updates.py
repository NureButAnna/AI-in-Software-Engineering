"""Зріз C: часткове редагування справи й зміна статусу (T10–T13)."""

from __future__ import annotations

import pytest

from app.models import Case

CASES = "/api/v1/cases"
STATUSES = ["PREPARING", "SUBMITTED", "IN_REVIEW", "APPROVED", "REJECTED", "CANCELLED"]

# Матриця з lab1/docs/requirements.md, розділ 2.2, записана окремо від коду сервісу.
# Рядок — поточний статус, символ — запитаний: «✓» дозволено, «=» повтор, «✗» заборонено.
MATRIX = {
    "PREPARING": "=✓✗✗✗✓",
    "SUBMITTED": "✓=✓✗✗✓",
    "IN_REVIEW": "✗✗=✓✓✓",
    "APPROVED": "✗✗✗=✗✗",
    "REJECTED": "✗✗✗✗=✗",
    "CANCELLED": "✗✗✗✗✗=",
}
TERMINAL = {"APPROVED", "REJECTED", "CANCELLED"}


def assert_error(response, status, code):
    assert response.status_code == status
    error = response.json()["error"]
    assert error["code"] == code
    return error


@pytest.fixture
def make_case(client, auth, db):
    def _make(title="Справа", deadline="2026-11-30", status="PREPARING") -> int:
        payload = {"title": title}
        if deadline is not None:
            payload["deadline"] = deadline
        case_id = client.post(CASES, json=payload, headers=auth).json()["id"]
        if status != "PREPARING":
            db.get(Case, case_id).status = status
            db.commit()
        return case_id

    return _make


def stored(db, case_id) -> Case:
    db.expire_all()
    return db.get(Case, case_id)


def snapshot(db, case_id) -> tuple:
    case = stored(db, case_id)
    return (case.title, case.deadline, case.status, case.updated_at)


# --- T10 ---------------------------------------------------------------------


def test_t10_patch_title_keeps_deadline(client, auth, make_case):
    case_id = make_case(title="Стара", deadline="2026-11-30")
    response = client.patch(f"{CASES}/{case_id}", json={"title": "  Нова  "}, headers=auth)
    assert response.status_code == 200
    assert response.json()["title"] == "Нова"
    assert response.json()["deadline"] == "2026-11-30"


def test_t10_patch_deadline_keeps_title(client, auth, make_case):
    case_id = make_case(title="Назва", deadline="2026-11-30")
    response = client.patch(f"{CASES}/{case_id}", json={"deadline": "2027-01-15"}, headers=auth)
    assert response.status_code == 200
    assert (response.json()["title"], response.json()["deadline"]) == ("Назва", "2027-01-15")


def test_t10_null_deadline_clears_it(client, auth, make_case):
    case_id = make_case(deadline="2026-11-30")
    response = client.patch(f"{CASES}/{case_id}", json={"deadline": None}, headers=auth)
    assert response.status_code == 200 and response.json()["deadline"] is None
    assert client.get(f"{CASES}/{case_id}", headers=auth).json()["deadline"] is None


def test_t10_patch_both_fields(client, auth, make_case):
    case_id = make_case()
    response = client.patch(
        f"{CASES}/{case_id}", json={"title": "Обидва", "deadline": "2026-12-12"}, headers=auth
    )
    assert response.status_code == 200
    assert (response.json()["title"], response.json()["deadline"]) == ("Обидва", "2026-12-12")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": None},
        {"title": ""},
        {"title": "   "},
        {"title": 7},
        {"deadline": "2026-13-01"},
        {"deadline": "завтра"},
        {"deadline": 5},
        {"status": "SUBMITTED"},
        {"id": 5},
        {"owner_id": 2},
        {"created_at": "2026-01-01T00:00:00Z"},
        {"updated_at": "2026-01-01T00:00:00Z"},
        {"title": "Нова", "unknown": 1},
    ],
)
def test_t10_invalid_patch_is_422_and_changes_nothing(client, auth, db, make_case, payload):
    case_id = make_case()
    before = snapshot(db, case_id)
    response = client.patch(f"{CASES}/{case_id}", json=payload, headers=auth)
    assert_error(response, 422, "VALIDATION_ERROR")
    assert snapshot(db, case_id) == before


def test_t10_patch_unknown_or_foreign_case_is_404(client, auth, make_user, make_case):
    other = make_user("other@example.com")
    foreign = client.post(CASES, json={"title": "Чужа"}, headers=other).json()["id"]
    missing = client.patch(f"{CASES}/999", json={"title": "X"}, headers=auth)
    foreign_resp = client.patch(f"{CASES}/{foreign}", json={"title": "X"}, headers=auth)
    assert_error(missing, 404, "NOT_FOUND")
    assert missing.json() == foreign_resp.json()
    # перевірка власника йде раніше за валідацію тіла (розділ 4 контракту даних)
    assert_error(client.patch(f"{CASES}/{foreign}", json={}, headers=auth), 404, "NOT_FOUND")


# --- T11 ---------------------------------------------------------------------


def test_t11_valid_title_with_invalid_deadline_changes_nothing(client, auth, db, make_case):
    case_id = make_case(title="Стара", deadline="2026-11-30")
    before = snapshot(db, case_id)
    response = client.patch(
        f"{CASES}/{case_id}", json={"title": "Нова", "deadline": "2026-02-30"}, headers=auth
    )
    error = assert_error(response, 422, "VALIDATION_ERROR")
    assert [d["field"] for d in error["details"]] == ["deadline"]
    assert snapshot(db, case_id) == before


def test_t11_invalid_title_with_valid_deadline_changes_nothing(client, auth, db, make_case):
    case_id = make_case(title="Стара", deadline="2026-11-30")
    before = snapshot(db, case_id)
    response = client.patch(
        f"{CASES}/{case_id}", json={"title": "  ", "deadline": "2027-01-01"}, headers=auth
    )
    assert_error(response, 422, "VALIDATION_ERROR")
    assert snapshot(db, case_id) == before


@pytest.mark.parametrize("terminal", sorted(TERMINAL))
@pytest.mark.parametrize("payload", [{"title": "Нова"}, {"deadline": None}, {"title": "Справа"}])
def test_t11_patch_in_terminal_status_is_409_even_without_real_change(
    client, auth, db, make_case, terminal, payload
):
    case_id = make_case(title="Справа", deadline="2026-11-30", status=terminal)
    before = snapshot(db, case_id)
    response = client.patch(f"{CASES}/{case_id}", json=payload, headers=auth)
    assert_error(response, 409, "INVALID_STATE_TRANSITION")
    assert snapshot(db, case_id) == before


def test_t11_validation_comes_before_terminal_check(client, auth, make_case):
    case_id = make_case(status="APPROVED")
    response = client.patch(f"{CASES}/{case_id}", json={"title": None}, headers=auth)
    assert_error(response, 422, "VALIDATION_ERROR")


def test_t11_updated_at_changes_only_on_real_change(client, auth, db, make_case):
    case_id = make_case(title="Назва", deadline="2026-11-30")
    before = stored(db, case_id).updated_at
    client.patch(f"{CASES}/{case_id}", json={"title": "Назва", "deadline": "2026-11-30"}, headers=auth)
    assert stored(db, case_id).updated_at == before
    client.patch(f"{CASES}/{case_id}", json={"title": "Інша"}, headers=auth)
    assert stored(db, case_id).updated_at > before


# --- T12 ---------------------------------------------------------------------


@pytest.mark.parametrize("current", STATUSES)
@pytest.mark.parametrize("requested", STATUSES)
def test_t12_transition_matrix(client, auth, db, make_case, current, requested):
    mark = MATRIX[current][STATUSES.index(requested)]
    case_id = make_case(status=current)
    before = snapshot(db, case_id)
    response = client.patch(f"{CASES}/{case_id}/status", json={"status": requested}, headers=auth)
    if mark in "✓=":
        assert response.status_code == 200
        assert response.json()["status"] == requested
        assert stored(db, case_id).status == requested
    else:
        error = assert_error(response, 409, "INVALID_STATE_TRANSITION")
        assert f"{current} → {requested}" in error["message"]
        assert snapshot(db, case_id) == before


def test_t12_allowed_transition_updates_updated_at_and_response(client, auth, db, make_case):
    case_id = make_case()
    before = stored(db, case_id).updated_at
    response = client.patch(f"{CASES}/{case_id}/status", json={"status": "SUBMITTED"}, headers=auth)
    assert response.status_code == 200 and response.json()["status"] == "SUBMITTED"
    assert stored(db, case_id).updated_at > before


def test_t12_full_happy_path_preparing_to_approved(client, auth, make_case):
    case_id = make_case()
    for status in ("SUBMITTED", "IN_REVIEW", "APPROVED"):
        response = client.patch(f"{CASES}/{case_id}/status", json={"status": status}, headers=auth)
        assert response.json()["status"] == status


# --- T13 ---------------------------------------------------------------------


@pytest.mark.parametrize("status", STATUSES)
def test_t13_repeating_current_status_is_200_and_changes_nothing(client, auth, db, make_case, status):
    case_id = make_case(status=status)
    before = snapshot(db, case_id)
    response = client.patch(f"{CASES}/{case_id}/status", json={"status": status}, headers=auth)
    assert response.status_code == 200 and response.json()["status"] == status
    assert snapshot(db, case_id) == before


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": "DONE"},
        {"status": "submitted"},
        {"status": ""},
        {"status": None},
        {"status": 1},
        {"status": "SUBMITTED", "title": "X"},
        {"title": "X"},
    ],
)
def test_t13_invalid_status_body_is_422_and_changes_nothing(client, auth, db, make_case, payload):
    case_id = make_case()
    before = snapshot(db, case_id)
    response = client.patch(f"{CASES}/{case_id}/status", json=payload, headers=auth)
    assert_error(response, 422, "VALIDATION_ERROR")
    assert snapshot(db, case_id) == before


def test_t13_status_of_unknown_or_foreign_case_is_404(client, auth, make_user):
    other = make_user("other@example.com")
    foreign = client.post(CASES, json={"title": "Чужа"}, headers=other).json()["id"]
    for case_id in (999, foreign):
        response = client.patch(f"{CASES}/{case_id}/status", json={"status": "SUBMITTED"}, headers=auth)
        assert_error(response, 404, "NOT_FOUND")
    assert client.get(f"{CASES}/{foreign}", headers=other).json()["status"] == "PREPARING"


def test_t13_status_can_not_be_changed_via_general_patch(client, auth, make_case):
    case_id = make_case()
    assert client.patch(f"{CASES}/{case_id}", json={"status": "SUBMITTED"}, headers=auth).status_code == 422
    assert client.get(f"{CASES}/{case_id}", headers=auth).json()["status"] == "PREPARING"


@pytest.mark.parametrize("method_path", [("patch", ""), ("patch", "/status")])
def test_t13_patch_routes_require_token(client, make_case, method_path):
    case_id = make_case()
    method, suffix = method_path
    response = getattr(client, method)(f"{CASES}/{case_id}{suffix}", json={"status": "SUBMITTED"})
    assert_error(response, 401, "AUTH_REQUIRED")
