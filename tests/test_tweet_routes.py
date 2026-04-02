import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from xservice.providers.models import Tweet as ProviderTweet, UserPage as ProviderUserPage
from xservice.main import create_app
from xservice.providers.base import Provider
from xservice.providers.exceptions import ProviderError, SessionAcquisitionError
from xservice.api.dependencies import get_provider
from xservice.auth import get_api_key

# --- Test setup ---

@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=Provider)
    provider.tweet_detail = AsyncMock()
    provider.tweet_retweeters = AsyncMock()
    provider.tweet_favoriters = AsyncMock()
    return provider


@pytest.fixture
def client(mock_provider):
    app = create_app()
    app.dependency_overrides[get_provider] = lambda: mock_provider
    app.dependency_overrides[get_api_key] = lambda: {"key": "test-key"}
    return TestClient(app)


# --- Tests for /tweets/{tweet_id}/ ---

def test_get_tweet_detail_success(client, mock_provider):
    mock_tweet = ProviderTweet(id="123", text="Hello", user_id="456", created_at="...")
    mock_provider.tweet_detail.return_value = mock_tweet
    response = client.get("/api/v1/tweets/123/")
    assert response.status_code == 200
    assert response.json()["id"] == "123"
    assert response.json()["lang"] is None  # Mapped from language
    mock_provider.tweet_detail.assert_called_once_with(tweet_id="123")


def test_get_tweet_detail_not_found(client, mock_provider):
    mock_provider.tweet_detail.return_value = None
    response = client.get("/api/v1/tweets/456/")
    assert response.status_code == 404
    assert response.json() == {"detail": "Tweet not found"}


def test_get_tweet_detail_provider_error(client, mock_provider):
    mock_provider.tweet_detail.side_effect = ProviderError("Provider failed")
    response = client.get("/api/v1/tweets/123/")
    assert response.status_code == 502


def test_get_tweet_detail_no_session_error(client, mock_provider):
    mock_provider.tweet_detail.side_effect = SessionAcquisitionError("No sessions")
    response = client.get("/api/v1/tweets/123/")
    assert response.status_code == 503


# --- Tests for paginated tweet endpoints ---

def test_get_tweet_retweeters_success(client, mock_provider):
    mock_page = ProviderUserPage(users=[], count=0)
    mock_provider.tweet_retweeters.return_value = mock_page
    response = client.get("/api/v1/tweets/123/retweeters/?limit=50")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["users"] == []
    mock_provider.tweet_retweeters.assert_called_once_with(tweet_id="123", limit=50)


def test_get_tweet_favoriters_success(client, mock_provider):
    mock_page = ProviderUserPage(users=[], count=0)
    mock_provider.tweet_favoriters.return_value = mock_page
    response = client.get("/api/v1/tweets/123/favoriters/?limit=75")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["users"] == []
    mock_provider.tweet_favoriters.assert_called_once_with(tweet_id="123", limit=75)
