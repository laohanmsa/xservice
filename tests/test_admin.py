import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from xservice.api.dependencies import get_db, get_provider
from xservice.auth import get_api_key
from xservice.models import XAccountSession


def test_unauthenticated_get_api_keys(client: TestClient):
    response = client.get("/api/v1/admin/api-keys")
    assert response.status_code == 403
    assert response.json() == {"detail": "Missing API key"}


def test_api_key_crud(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/admin/api-keys", headers=auth_headers)
    assert response.status_code == 200
    initial_keys = response.json()
    assert len(initial_keys) == 1
    assert "key" not in initial_keys[0]

    response = client.post(
        "/api/v1/admin/api-keys",
        json={"comment": "test key"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    test_key = response.json()
    assert "key" in test_key

    response = client.get("/api/v1/admin/api-keys", headers=auth_headers)
    assert response.status_code == 200
    all_keys = response.json()
    assert len(all_keys) == 2
    assert "key" not in all_keys[0]
    assert "key" not in all_keys[1]

    response = client.delete(
        f"/api/v1/admin/api-keys/{test_key['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    response = client.get("/api/v1/admin/api-keys", headers=auth_headers)
    assert response.status_code == 200
    remaining_keys = response.json()
    assert len(remaining_keys) == 1
    assert remaining_keys[0]["id"] == initial_keys[0]["id"]


def test_session_crud(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    session_data = {
        "username": "testuser",
        "label": "test label",
        "is_active": True,
        "cookies": {"test": "cookie"},
        "headers": {"test": "header"},
    }
    response = client.post(
        "/api/v1/admin/sessions", json=session_data, headers=auth_headers
    )
    assert response.status_code == 200
    session = response.json()
    assert session["username"] == "testuser"
    session_id = session["id"]

    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.patch(
        f"/api/v1/admin/sessions/{session_id}",
        json={"label": "new label"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["label"] == "new label"

    response = client.delete(
        f"/api/v1/admin/sessions/{session_id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_import_cookie(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    cookie_data = {
        "cookie_string": 'ct0=test_csrf; twid=u%3D12345; auth_token=test_auth_token==',
        "label": "imported cookie",
    }
    response = client.post(
        "/api/v1/admin/sessions/import-cookie",
        json=cookie_data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    session = response.json()
    assert session["label"] == "imported cookie"
    assert session["username"] == "user_12345"
    assert session["cookies"]["ct0"] == "test_csrf"
    assert session["cookies"]["auth_token"] == "test_auth_token=="
    assert session["headers"]["authorization"].startswith("Bearer AAAAA")
    assert session["headers"]["x-csrf-token"] == "test_csrf"
    assert session["headers"]["x-twitter-auth-type"] == "OAuth2Session"

    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_session_limits(client: TestClient, auth_headers: dict[str, str]):
    session_data = {
        "username": "testuser",
        "label": "test label",
        "rate_limit_state": {"test": 123},
    }
    response = client.post(
        "/api/v1/admin/sessions", json=session_data, headers=auth_headers
    )
    assert response.status_code == 200
    session = response.json()

    response = client.get("/api/v1/admin/session-limits", headers=auth_headers)
    assert response.status_code == 200
    limits = response.json()
    assert len(limits) > 0

    our_limit = next((entry for entry in limits if entry["id"] == session["id"]), None)
    assert our_limit is not None
    assert our_limit["username"] == "testuser"
    assert our_limit["label"] == "test label"
    assert our_limit["rate_limit_state"] == {"test": 123}


def test_get_provider_no_sessions(client: TestClient, auth_headers: dict[str, str]):
    @client.app.get("/test-provider")
    async def test_provider_route(
        provider=Depends(get_provider), _: str = Depends(get_api_key)
    ):
        return {"status": "ok"}

    response = client.get("/test-provider", headers=auth_headers)
    assert response.status_code == 503
    assert response.json() == {"detail": "No active X account sessions available."}


def test_get_provider_with_sessions(client: TestClient, auth_headers: dict[str, str]):
    response = client.post(
        "/api/v1/admin/sessions",
        json={"username": "testuser_active", "is_active": True},
        headers=auth_headers,
    )
    assert response.status_code == 200

    @client.app.get("/test-provider-ok")
    async def test_provider_ok_route(
        provider=Depends(get_provider), _: str = Depends(get_api_key)
    ):
        assert provider is not None
        return {"status": "ok"}

    response = client.get("/test-provider-ok", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_status_unauthenticated(client: TestClient):
    response = client.get("/api/v1/admin/status")
    assert response.status_code == 403
    assert response.json() == {"detail": "Missing API key"}


def test_get_status(client: TestClient, auth_headers: dict[str, str]):
    response = client.get("/api/v1/admin/status", headers=auth_headers)
    assert response.status_code == 200
    status = response.json()

    assert status["service_status"] == "ok"
    assert status["api_key_count"] == 1
    assert status["session_count"] == 0
    assert status["active_session_count"] == 0
    assert status["inactive_session_count"] == 0
    assert len(status["sessions"]) == 0

    response = client.post(
        "/api/v1/admin/sessions",
        json={
            "username": "testuser_active",
            "is_active": True,
            "rate_limit_state": {"test": 1},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    active_session = response.json()

    response = client.post(
        "/api/v1/admin/sessions",
        json={"username": "testuser_inactive", "is_active": False},
        headers=auth_headers,
    )
    assert response.status_code == 200

    response = client.get("/api/v1/admin/status", headers=auth_headers)
    assert response.status_code == 200
    status = response.json()

    assert status["service_status"] == "ok"
    assert status["api_key_count"] == 1
    assert status["session_count"] == 2
    assert status["active_session_count"] == 1
    assert status["inactive_session_count"] == 1
    assert len(status["sessions"]) == 2

    active_session_status = next(
        (session for session in status["sessions"] if session["id"] == active_session["id"]),
        None,
    )
    assert active_session_status is not None
    assert active_session_status["username"].startswith("testuser")
    assert active_session_status["is_active"] is True
    assert active_session_status["rate_limit_state"] == {"test": 1}
