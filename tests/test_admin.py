from fastapi.testclient import TestClient
from fastapi import Depends
from fastapi.routing import APIRoute
from xservice.api.dependencies import get_provider
from xservice.auth import get_api_key


def test_unauthenticated_get_api_keys(client: TestClient):
    response = client.get("/api/v1/admin/api-keys")
    assert response.status_code == 403
    assert response.json() == {"detail": "Missing API key"}


def test_api_key_crud(client: TestClient, auth_headers: dict[str, str]):
    # Get initial API keys (should be 1 from conftest.py)
    response = client.get("/api/v1/admin/api-keys", headers=auth_headers)
    assert response.status_code == 200
    initial_keys = response.json()
    assert len(initial_keys) == 1
    assert "key" not in initial_keys[0]

    # Create another key using the fixture's key
    response = client.post(
        "/api/v1/admin/api-keys",
        json={"comment": "test key"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    test_key = response.json()
    assert "key" in test_key

    # Get API keys again
    response = client.get("/api/v1/admin/api-keys", headers=auth_headers)
    assert response.status_code == 200
    all_keys = response.json()
    assert len(all_keys) == 2
    assert "key" not in all_keys[0]
    assert "key" not in all_keys[1]


    # Delete test key
    response = client.delete(
        f"/api/v1/admin/api-keys/{test_key['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Verify deletion
    response = client.get("/api/v1/admin/api-keys", headers=auth_headers)
    assert response.status_code == 200
    remaining_keys = response.json()
    assert len(remaining_keys) == 1
    assert remaining_keys[0]["id"] == initial_keys[0]["id"]


def test_session_crud(client: TestClient, auth_headers: dict[str, str]):
    # Get initial sessions (should be 0)
    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Create session
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

    # Get sessions
    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Update session
    update_data = {"label": "new label"}
    response = client.patch(
        f"/api/v1/admin/sessions/{session_id}",
        json=update_data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["label"] == "new label"

    # Delete session
    response = client.delete(
        f"/api/v1/admin/sessions/{session_id}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Verify deletion
    response = client.get("/api/v1/admin/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 0


def test_get_provider_no_sessions(client: TestClient, auth_headers: dict[str, str]):
    # Dynamically add a test route to the client's app instance
    @client.app.get("/test-provider")
    async def test_provider_route(
        provider=Depends(get_provider), _: str = Depends(get_api_key)
    ):
        return {"status": "ok"}

    response = client.get("/test-provider", headers=auth_headers)
    assert response.status_code == 503
    assert response.json() == {"detail": "No active X account sessions available."}




def test_get_provider_with_sessions(client: TestClient, auth_headers: dict[str, str]):
    # Create an active session
    session_data = {"username": "testuser_active", "is_active": True}
    response = client.post(
        "/api/v1/admin/sessions", json=session_data, headers=auth_headers
    )
    assert response.status_code == 200

    # Dynamically add a test route to the client's app instance
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
    # Get initial status (1 key from fixture, 0 sessions)
    response = client.get("/api/v1/admin/status", headers=auth_headers)
    assert response.status_code == 200
    status = response.json()

    assert status["service_status"] == "ok"
    assert status["api_key_count"] == 1
    assert status["session_count"] == 0
    assert status["active_session_count"] == 0
    assert status["inactive_session_count"] == 0
    assert len(status["sessions"]) == 0

    # Create an active session
    session_data = {
        "username": "testuser_active",
        "is_active": True,
        "rate_limit_state": {"test": 1},
    }
    response = client.post(
        "/api/v1/admin/sessions", json=session_data, headers=auth_headers
    )
    assert response.status_code == 200
    active_session = response.json()

    # Create an inactive session
    session_data = {"username": "testuser_inactive", "is_active": False}
    response = client.post(
        "/api/v1/admin/sessions", json=session_data, headers=auth_headers
    )
    assert response.status_code == 200

    # Get status again
    response = client.get("/api/v1/admin/status", headers=auth_headers)
    assert response.status_code == 200
    status = response.json()

    assert status["service_status"] == "ok"
    assert status["api_key_count"] == 1
    assert status["session_count"] == 2
    assert status["active_session_count"] == 1
    assert status["inactive_session_count"] == 1
    assert len(status["sessions"]) == 2

    # Check session details in status
    active_session_status = next(
        (s for s in status["sessions"] if s["id"] == active_session["id"]), None
    )
    assert active_session_status is not None
    assert active_session_status["username"] == "testuser_active"
    assert active_session_status["is_active"] is True
    assert active_session_status["rate_limit_state"] == {"test": 1}



