"""Контрольні запити ЛР3, окремі від T0/T1. Запуск: python -m experiment.lr3_probe m1."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from app.main import create_app

API = "/api/v1"
CASES = f"{API}/cases"


def create(client, auth, **payload):
    response = client.post(CASES, headers=auth, json=payload)
    assert response.status_code == 201, response.text
    return response.status_code, f"{CASES}/{response.json()['id']}"


def read(client, auth, url):
    response = client.get(url, headers=auth)
    assert response.status_code == 200, response.text
    return response.json()


def m1(client, auth):
    _, url = create(client, auth, title="Контроль M1")
    for status in ("SUBMITTED", "IN_REVIEW", "APPROVED"):
        response = client.patch(f"{url}/status", headers=auth, json={"status": status})
        assert response.status_code == 200 and response.json()["status"] == status
    before = read(client, auth, url)
    response = client.patch(f"{url}/status", headers=auth, json={"status": "PREPARING"})
    after = read(client, auth, url)
    return {"before": before["status"], "patch": response.status_code, "after": after["status"],
            "updated_at_unchanged": before["updated_at"] == after["updated_at"]}


def m2(client, auth):
    _, url = create(client, auth, title="Стара", deadline="2026-11-30")
    before = read(client, auth, url)
    response = client.patch(url, headers=auth, json={"title": "Нова", "deadline": "2026-02-30"})
    after = read(client, auth, url)
    return {"before": {k: before[k] for k in ("title", "deadline")}, "patch": response.status_code,
            "after": {k: after[k] for k in ("title", "deadline")}}


def m3(client, auth):
    rows = []
    for title in ("Save button", "O'Brien"):
        status, url = create(client, auth, title=title)
        rows.append({"sent": title, "post": status, "loaded": read(client, auth, url)["title"]})
    return rows


def main():
    probes = {"m1": m1, "m2": m2, "m3": m3}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("card", choices=probes)
    args = parser.parse_args()
    with TemporaryDirectory() as tmp:
        app = create_app(Path(tmp) / "probe.db", secret_key="lr3-test-only")
        try:
            with TestClient(app) as client:
                user = {"email": "probe@example.com", "password": "synthetic-pass"}
                assert client.post(f"{API}/auth/register", json=user).status_code == 201
                login = client.post(f"{API}/auth/login", json=user)
                assert login.status_code == 200
                auth = {"Authorization": f"Bearer {login.json()['access_token']}"}
                print(json.dumps(probes[args.card](client, auth), ensure_ascii=False))
        finally:
            app.state.engine.dispose()


if __name__ == "__main__":
    main()
