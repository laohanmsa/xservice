from fastapi.testclient import TestClient


def test_get_playground(client: TestClient):
    response = client.get("/playground")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>xservice API Playground</title>" in response.text
    assert 'id="operation-selector"' in response.text
    assert 'id="api-key"' in response.text
    assert "/openapi.json" in response.text
