"""Перевірені пропозиції з reports/lr3/t-ai-draft.txt."""

CASES = "/api/v1/cases"


def test_t28_patch_both_fields_persists(client, auth):
    """AC-03.8: обидві зміни доступні після повторного читання."""
    created = client.post(CASES, headers=auth, json={"title": "Початкова"})
    assert created.status_code == 201
    url = f"{CASES}/{created.json()['id']}"
    changes = {"title": "Оновлена", "deadline": "2026-12-12"}
    changed = client.patch(url, headers=auth, json=changes)
    assert changed.status_code == 200
    loaded = client.get(url, headers=auth)
    assert loaded.status_code == 200
    assert all(loaded.json()[key] == value for key, value in changes.items())


def test_t29_repeat_status_keeps_stored_status_and_updated_at(client, auth):
    """AC-06.4: повтор кінцевого статусу не змінює збереженого стану."""
    created = client.post(CASES, headers=auth, json={"title": "Повтор"})
    assert created.status_code == 201
    url = f"{CASES}/{created.json()['id']}"
    cancelled = client.patch(f"{url}/status", headers=auth, json={"status": "CANCELLED"})
    assert cancelled.status_code == 200
    initial = client.get(url, headers=auth)
    assert initial.status_code == 200
    before = initial.json()
    assert before["status"] == "CANCELLED"

    repeated = client.patch(f"{url}/status", headers=auth, json={"status": "CANCELLED"})
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "CANCELLED"
    after = client.get(url, headers=auth)
    assert after.status_code == 200
    assert after.json() == before
