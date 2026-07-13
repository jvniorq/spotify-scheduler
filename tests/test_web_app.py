from __future__ import annotations

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from pwdlib import PasswordHash

from spoxu_web.app import create_app
from spoxu_web.config import WebSettings

PASSWORD = "correct-horse-battery-staple"


def make_settings(tmp_path) -> WebSettings:
    return WebSettings(
        environment="test",
        base_url="http://testserver",
        data_dir=tmp_path,
        timezone="America/Lima",
        cookie_secure=False,
        automation_enabled=False,
        session_secret="s" * 64,
        admin_password_hash=PasswordHash.recommended().hash(PASSWORD),
        token_encryption_key=Fernet.generate_key().decode("ascii"),
        spotify_client_id="test-client-id",
        spotify_client_secret="test-client-secret",
        spotify_redirect_uri="http://127.0.0.1:8000/oauth/spotify/callback",
    )


def login(client: TestClient) -> dict[str, str]:
    response = client.post("/api/login", json={"password": PASSWORD})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf_token"]}


def weekly_payload(**changes):
    payload = {
        "name": "Mañanas",
        "kind": "weekly",
        "day_of_week": 0,
        "specific_date": None,
        "start_time": "08:00:00",
        "end_time": "09:30:00",
        "playlist_id": "playlist-id",
        "playlist_name": "Café tranquilo",
        "device_name": "Sala",
        "random_queue": True,
        "skip_explicit": True,
        "enabled": True,
        "priority": 10,
    }
    payload.update(changes)
    return payload


def test_health_is_public_and_does_not_expose_secrets(tmp_path):
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "spoxu-web"}
    assert settings.session_secret not in response.text
    assert settings.spotify_client_secret not in response.text


def test_private_api_requires_login(tmp_path):
    with TestClient(create_app(make_settings(tmp_path))) as client:
        assert client.get("/api/schedules").status_code == 401
        assert client.get("/api/status").status_code == 401


def test_wrong_password_is_rejected(tmp_path):
    with TestClient(create_app(make_settings(tmp_path))) as client:
        response = client.post("/api/login", json={"password": "wrong"})
    assert response.status_code == 401
    assert "spoxu_session" not in response.cookies


def test_login_cookie_and_csrf_protection(tmp_path):
    with TestClient(create_app(make_settings(tmp_path))) as client:
        response = client.post("/api/login", json={"password": PASSWORD})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        assert client.post("/api/schedules", json=weekly_payload()).status_code == 403


def test_schedule_crud_keeps_automation_rules(tmp_path):
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as client:
        headers = login(client)
        created = client.post(
            "/api/schedules",
            json=weekly_payload(),
            headers=headers,
        )
        assert created.status_code == 201
        schedule = created.json()
        assert schedule["random_queue"] is True
        assert schedule["skip_explicit"] is True
        assert schedule["priority"] == 10

        overnight = weekly_payload(
            name="Noche",
            day_of_week=4,
            start_time="22:00:00",
            end_time="02:00:00",
            priority=40,
        )
        second = client.post("/api/schedules", json=overnight, headers=headers)
        assert second.status_code == 201
        assert second.json()["end_time"] == "02:00:00"

        rows = client.get("/api/schedules")
        assert rows.status_code == 200
        assert len(rows.json()) == 2

        updated_payload = weekly_payload(name="Mañanas editadas", enabled=False)
        updated = client.put(
            "/api/schedules/" + str(schedule["id"]),
            json=updated_payload,
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Mañanas editadas"
        assert updated.json()["enabled"] is False

        deleted = client.delete(
            "/api/schedules/" + str(schedule["id"]),
            headers=headers,
        )
        assert deleted.status_code == 204
        assert client.get("/api/schedules/" + str(schedule["id"])).status_code == 404


def test_date_schedule_and_validation(tmp_path):
    with TestClient(create_app(make_settings(tmp_path))) as client:
        headers = login(client)
        valid = weekly_payload(
            kind="date",
            day_of_week=None,
            specific_date="2026-08-01",
            start_time="22:00:00",
            end_time="02:00:00",
        )
        assert client.post("/api/schedules", json=valid, headers=headers).status_code == 201

        invalid = weekly_payload(start_time="08:00:00", end_time="08:00:00")
        assert client.post("/api/schedules", json=invalid, headers=headers).status_code == 422


def test_schedule_persists_after_restart(tmp_path):
    settings = make_settings(tmp_path)
    with TestClient(create_app(settings)) as first:
        headers = login(first)
        created = first.post("/api/schedules", json=weekly_payload(), headers=headers)
        schedule_id = created.json()["id"]

    with TestClient(create_app(settings)) as second:
        login(second)
        response = second.get("/api/schedules/" + str(schedule_id))
        assert response.status_code == 200
        assert response.json()["name"] == "Mañanas"
