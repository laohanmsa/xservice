from fastapi.testclient import TestClient


def test_get_playground(client: TestClient):
    response = client.get("/playground")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>xservice API Playground</title>" in response.text
    assert 'id="operation-selector"' in response.text
    assert 'id="operation-meta"' in response.text
    assert 'id="operation-summary"' in response.text
    assert 'id="operation-description"' in response.text
    assert 'id="api-key"' in response.text
    assert "/openapi.json" in response.text


def test_follow_relationship_routes_describe_ordering_limits(client: TestClient):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    following = spec["paths"]["/api/v1/users/{username}/following/"]["get"]
    followers = spec["paths"]["/api/v1/users/{username}/followers/"]["get"]

    assert following["summary"] == "Get accounts this user follows"
    assert followers["summary"] == "Get this user's followers"
    assert "true asc/desc relationship-time ordering control" in following["description"]
    assert "true asc/desc relationship-time ordering control" in followers["description"]
