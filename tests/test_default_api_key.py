from fastapi.testclient import TestClient

from xservice.settings import settings


def test_default_playground_api_key_grants_access(client: TestClient):
    response = client.get(
        "/api/v1/admin/status",
        headers={"X-API-KEY": settings.PLAYGROUND_DEFAULT_API_KEY},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["service_status"] == "ok"
    assert payload["api_key_count"] == 0
    assert payload["session_count"] == 0
