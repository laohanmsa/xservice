import pytest
from fastapi.testclient import TestClient


def test_get_session_limits_nested_rate_limits(
    client: TestClient, auth_headers: dict[str, str]
):
    session_data = {
        "username": "testuser_rate_limits",
        "label": "test rate limits label",
        "rate_limit_state": {
            "UserTimeline": {"limit": 15, "remaining": 10, "reset": 1618700000},
            "Search": {"limit": 50, "remaining": 49, "reset": 1618701000},
        },
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
    assert our_limit["username"] == "testuser_rate_limits"
    assert our_limit["label"] == "test rate limits label"
    assert our_limit["rate_limit_state"] == {
        "UserTimeline": {"limit": 15, "remaining": 10, "reset": 1618700000},
        "Search": {"limit": 50, "remaining": 49, "reset": 1618701000},
    }


def test_get_status_nested_rate_limits(
    client: TestClient, auth_headers: dict[str, str]
):
    session_data = {
        "username": "testuser_status_rate_limits",
        "is_active": True,
        "rate_limit_state": {
            "UserTimeline": {"limit": 15, "remaining": 10, "reset": 1618700000},
        },
    }
    response = client.post(
        "/api/v1/admin/sessions", json=session_data, headers=auth_headers
    )
    assert response.status_code == 200
    active_session = response.json()

    response = client.get("/api/v1/admin/status", headers=auth_headers)
    assert response.status_code == 200
    status = response.json()

    active_session_status = next(
        (
            session
            for session in status["sessions"]
            if session["id"] == active_session["id"]
        ),
        None,
    )
    assert active_session_status is not None
    assert active_session_status["username"].startswith("testuser_status")
    assert active_session_status["is_active"] is True
    assert active_session_status["rate_limit_state"] == {
        "UserTimeline": {"limit": 15, "remaining": 10, "reset": 1618700000},
    }
