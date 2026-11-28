"""Наскрізні доповнення ЛР3: стан після запису перевіряється через API."""

import pytest

CASES = "/api/v1/cases"
DASHBOARD = "/api/v1/dashboard"


def create_case(client, auth, **data):
    response = client.post(CASES, headers=auth, json=data)
    assert response.status_code == 201
    return f"{CASES}/{response.json()['id']}"


def read_case(client, auth, url):
    response = client.get(url, headers=auth)
    assert response.status_code == 200
    return response.json()


def test_t23_approved_case_stays_closed_after_reopen_attempt(client, auth):
    url = create_case(client, auth, title="Заява")
    for status in ("SUBMITTED", "IN_REVIEW", "APPROVED"):
        response = client.patch(f"{url}/status", headers=auth, json={"status": status})
        assert response.status_code == 200
        assert response.json()["status"] == status

    before = read_case(client, auth, url)
    assert before["status"] == "APPROVED"
    response = client.patch(f"{url}/status", headers=auth, json={"status": "PREPARING"})
    after = read_case(client, auth, url)
    assert (response.status_code, after["status"], after["updated_at"]) == (
        409, "APPROVED", before["updated_at"]
    )
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_t24_rejected_patch_preserves_both_fields_in_get(client, auth):
    url = create_case(client, auth, title="Стара", deadline="2026-11-30")
    before = read_case(client, auth, url)
    assert (before["title"], before["deadline"]) == ("Стара", "2026-11-30")
    response = client.patch(
        url, headers=auth, json={"title": "Нова", "deadline": "2026-02-30"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    after = read_case(client, auth, url)
    fields = ("title", "deadline", "updated_at")
    assert tuple(after[key] for key in fields) == tuple(before[key] for key in fields)


def test_t25_cleared_deadline_disappears_from_dashboard(client, auth):
    url = create_case(client, auth, title="На дашборді", deadline="2026-11-10")
    case_id = read_case(client, auth, url)["id"]
    today = {"today": "2026-11-09"}
    before = client.get(DASHBOARD, headers=auth, params=today)
    assert before.status_code == 200
    assert case_id in [case["id"] for case in before.json()["upcoming_cases"]]

    response = client.patch(url, headers=auth, json={"deadline": None})
    assert response.status_code == 200
    assert read_case(client, auth, url)["deadline"] is None
    after = client.get(DASHBOARD, headers=auth, params=today)
    assert after.status_code == 200
    for block in ("upcoming_cases", "overdue_cases"):
        assert case_id not in [case["id"] for case in after.json()[block]]


@pytest.mark.parametrize("title", ["Save button", "O'Brien"], ids=["plain", "apostrophe"])
def test_t26_created_title_round_trips_exactly(client, auth, title):
    url = create_case(client, auth, title=title)
    assert read_case(client, auth, url)["title"] == title


def test_t27_intersection_keeps_contract_sort_order(client, auth):
    create_case(client, auth, title="Бета", deadline="2026-11-06")
    create_case(client, auth, title="Альфа", deadline="2026-11-06")
    create_case(client, auth, title="Якір", deadline="2026-11-05")
    create_case(client, auth, title="Не прострочена", deadline="2026-11-10")
    other = create_case(client, auth, title="Інший статус", deadline="2026-11-04")
    response = client.patch(f"{other}/status", headers=auth, json={"status": "SUBMITTED"})
    assert response.status_code == 200

    result = client.get(
        CASES, headers=auth, params={"status": "PREPARING", "due": "overdue", "today": "2026-11-09"}
    )
    assert result.status_code == 200
    assert [case["title"] for case in result.json()] == ["Якір", "Альфа", "Бета"]
