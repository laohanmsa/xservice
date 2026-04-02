import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from xservice.providers.models import (
    UserProfile as ProviderUserProfile,
    TweetPage as ProviderTweetPage,
    UserPage as ProviderUserPage,
)
from xservice.main import create_app
from xservice.providers.base import Provider
from xservice.providers.exceptions import ProviderError, SessionAcquisitionError
from xservice.api.dependencies import get_provider
from xservice.auth import get_api_key

# --- Test setup ---

@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=Provider)
    # The methods are async, so we need AsyncMocks
    provider.user_by_username = AsyncMock()
    provider.user_by_id = AsyncMock()
    provider.user_tweets = AsyncMock()
    provider.user_followers = AsyncMock()
    # Add other methods as you test them
    return provider


@pytest.fixture
def client(mock_provider):
    app = create_app()
    app.dependency_overrides[get_provider] = lambda: mock_provider
    app.dependency_overrides[get_api_key] = lambda: {"key": "test-key"}
    return TestClient(app)


# --- Tests for /users/{username}/ ---

def test_get_user_by_username_success(client, mock_provider):
    mock_user = ProviderUserProfile(id="123", username="testuser", name="Test User", is_blue_verified=True, tweet_count=100)
    mock_provider.user_by_username.return_value = mock_user
    response = client.get("/api/v1/users/testuser/")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
    assert response.json()["verified"] is True
    assert response.json()["statuses_count"] == 100
    mock_provider.user_by_username.assert_called_once_with(username="testuser")


def test_get_user_by_username_not_found(client, mock_provider):
    mock_provider.user_by_username.return_value = None
    response = client.get("/api/v1/users/nonexistent/")
    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}


def test_get_user_provider_error(client, mock_provider):
    mock_provider.user_by_username.side_effect = ProviderError("Provider failed")
    response = client.get("/api/v1/users/testuser/")
    assert response.status_code == 502
    assert response.json() == {"detail": "Provider failed"}


def test_get_user_no_session_error(client, mock_provider):
    mock_provider.user_by_username.side_effect = SessionAcquisitionError("No sessions")
    response = client.get("/api/v1/users/testuser/")
    assert response.status_code == 503
    assert response.json() == {"detail": "No sessions"}


# --- Tests for /users/id/{user_id}/ ---

def test_get_user_by_id_success(client, mock_provider):
    mock_user = ProviderUserProfile(id="123", username="testuser", name="Test User", tweet_count=50)
    mock_provider.user_by_id.return_value = mock_user
    response = client.get("/api/v1/users/id/123/")
    assert response.status_code == 200
    assert response.json()["id"] == "123"
    assert response.json()["statuses_count"] == 50
    mock_provider.user_by_id.assert_called_once_with(user_id="123")


def test_get_user_by_id_not_found(client, mock_provider):
    mock_provider.user_by_id.return_value = None
    response = client.get("/api/v1/users/id/456/")
    assert response.status_code == 404


# --- Tests for paginated user endpoints ---

def test_get_user_tweets_success(client, mock_provider):
    mock_page = ProviderTweetPage(tweets=[], count=0)
    mock_provider.user_tweets.return_value = mock_page
    response = client.get("/api/v1/users/testuser/tweets/?limit=10")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["tweets"] == []
    mock_provider.user_tweets.assert_called_once_with(username="testuser", limit=10)


def test_get_user_followers_success(client, mock_provider):
    mock_page = ProviderUserPage(users=[], count=0)
    mock_provider.user_followers.return_value = mock_page
    response = client.get("/api/v1/users/testuser/followers/?limit=50")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["users"] == []
    mock_provider.user_followers.assert_called_once_with(username="testuser", limit=50)
