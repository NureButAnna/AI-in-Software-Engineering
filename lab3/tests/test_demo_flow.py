"""Сценарій демонстрації з розділу 7 методички в адаптації до PaperTrail."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app

API = "/api/v1"
CREDENTIALS = {"email": "demo@example.com", "password": "demoPass123"}


def test_demo_register_create_edit_close_filter_restart(db_file):
    app = create_app(db_file, secret_key="demo")
    with TestClient(app) as client:
        assert client.post(f"{API}/auth/register", json=CREDENTIALS).status_code == 201
        token = client.post(f"{API}/auth/login", json=CREDENTIALS).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        passport = client.post(f"{API}/cases", json={"title": "Паспорт", "deadline": "2026-11-05"}, headers=headers).json()
        visa = client.post(f"{API}/cases", json={"title": "Віза", "deadline": "2026-11-12"}, headers=headers).json()

        client.patch(f"{API}/cases/{passport['id']}", json={"title": "Закордонний паспорт"}, headers=headers)
        for status in ("SUBMITTED", "IN_REVIEW", "APPROVED"):
            assert client.patch(f"{API}/cases/{passport['id']}/status", json={"status": status}, headers=headers).status_code == 200

        reopen = client.patch(f"{API}/cases/{passport['id']}/status", json={"status": "PREPARING"}, headers=headers)
        assert reopen.status_code == 409

        both = client.get(f"{API}/cases", params={"status": "PREPARING", "due": "upcoming", "today": "2026-11-09"}, headers=headers)
        assert [c["id"] for c in both.json()] == [visa["id"]]
        none = client.get(f"{API}/cases", params={"status": "APPROVED", "due": "overdue", "today": "2026-11-09"}, headers=headers)
        assert none.status_code == 200 and none.json() == []
    app.state.engine.dispose()

    restarted = create_app(db_file, secret_key="demo")  # перезапуск із тим самим файлом БД
    with TestClient(restarted) as client:
        token = client.post(f"{API}/auth/login", json=CREDENTIALS).json()["access_token"]
        cases = client.get(f"{API}/cases", headers={"Authorization": f"Bearer {token}"}).json()
    assert [(c["title"], c["status"]) for c in cases] == [
        ("Закордонний паспорт", "APPROVED"),
        ("Віза", "PREPARING"),
    ]
