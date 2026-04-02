import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from xservice.providers.models import SearchPage as ProviderSearchPage
from xservice.main import create_app
from xservice.providers.base import Provider
from xservice.providers.exceptions import ProviderError, SessionAcquisitionError
from xservice.api.dependencies import get_provider
from xservice.auth import get_api_key

# --- Test setup ---

@pytest.fixture
def mock_provider():
    mock = MagicMock(spec=Provider)
    mock.search = AsyncMock()
    return mock

@pytest.fixture
def client(mock_provider):
    app = create_app()
    app.dependency_overrides[get_provider] = lambda: mock_provider
    # Mock authentication
    app.dependency_overrides[get_api_key] = lambda: {"key": "test-key"}
    return TestClient(app)

# --- Tests ---

def test_search_success(client, mock_provider):
    # Arrange
    mock_response = ProviderSearchPage(tweets=[], users=[], count=0, category="Latest")
    mock_provider.search.return_value = mock_response
    
    # Act
    response = client.get("/api/v1/search/?q=test")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"tweets": [], "users": [], "count": 0, "category": "Latest", "next_cursor": None}
    mock_provider.search.assert_called_once_with(query="test", category="Latest", limit=20)

def test_search_with_params(client, mock_provider):
    # Arrange
    mock_response = ProviderSearchPage(tweets=[], users=[], count=0, category="People")
    mock_provider.search.return_value = mock_response

    # Act
    response = client.get("/api/v1/search/?q=test&category=People&limit=50")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"tweets": [], "users": [], "count": 0, "category": "People", "next_cursor": None}
    mock_provider.search.assert_called_once_with(query="test", category="People", limit=50)

def test_search_no_session_error(client, mock_provider):
    # Arrange
    mock_provider.search.side_effect = SessionAcquisitionError("No available sessions.")

    # Act
    response = client.get("/api/v1/search/?q=test")

    # Assert
    assert response.status_code == 503
    assert response.json() == {"detail": "No available sessions."}

def test_search_provider_error(client, mock_provider):
    # Arrange
    mock_provider.search.side_effect = ProviderError("Something went wrong.")

    # Act
    response = client.get("/api/v1/search/?q=test")

    # Assert
    assert response.status_code == 502
    assert response.json() == {"detail": "Something went wrong."}

def test_search_no_query_param(client):
    # Act
    response = client.get("/api/v1/search/")

    # Assert
    assert response.status_code == 422 # Unprocessable Entity for missing query

def test_search_invalid_category(client):
    # Act
    response = client.get("/api/v1/search/?q=test&category=Invalid")
    
    # Assert
    assert response.status_code == 422 # Unprocessable Entity for invalid enum value
