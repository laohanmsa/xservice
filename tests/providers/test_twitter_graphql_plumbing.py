import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from xservice.providers.registry import GRAPHQL_OPERATIONS
from xservice.providers.session_pool import SessionPool
from xservice.providers.twitter_graphql import TwitterGraphQLProvider


@pytest.fixture
def mock_session_pool():
    # Mock the session pool and its methods
    mock_pool = AsyncMock(spec=SessionPool)
    mock_session = MagicMock()
    mock_session.session_id = "test-session-id"
    mock_session.headers = {"User-Agent": "Test Agent"}
    mock_session.cookies = {"auth_token": "test-token"}
    mock_pool.get_session.return_value = mock_session
    mock_pool.release_session = AsyncMock()
    return mock_pool


DUMMY_HOME_HTML = """
<html>
<body>
    <script src="https://abs.twimg.com/responsive-web/client-web/main.e4339b5f.js"></script>
    <script src="https://abs.twimg.com/responsive-web/client-web/ondemand.s.86e6fd09.js"></script>
</body>
</html>
"""

DUMMY_ONDEMAND_JS = """
/* Some dummy javascript */
window.transaction = 'mock';
"""


@pytest.mark.asyncio
async def test_search_timeline_uses_post_with_correct_payload(
    mock_session_pool
):
    """
    Verify that the search method uses POST for SearchTimeline and sends the correct payload.
    """
    # Arrange
    provider = TwitterGraphQLProvider(session_pool=mock_session_pool)
    provider._request = AsyncMock(return_value={"data": {}})

    # Act
    await provider.search(query="test query", category="Latest", limit=50)

    # Assert
    provider._request.assert_called_once()
    call_args = provider._request.call_args

    assert call_args.args[0] == "POST"  # method
    op = GRAPHQL_OPERATIONS["SearchTimeline"]
    assert call_args.args[1] == f"https://twitter.com/i/api/graphql/{op.query_id}/SearchTimeline"

    # Check JSON payload
    payload = call_args.kwargs["json"]
    assert payload["variables"]["rawQuery"] == "test query"
    assert payload["variables"]["count"] == 50
    assert payload["variables"]["product"] == "Latest"
    assert payload["variables"]["withGrokTranslatedBio"] is False
    assert "cursor" not in payload["variables"] # Not provided in this test case

    assert payload["features"] == op.features
    assert payload["fieldToggles"] == op.field_toggles


@pytest.mark.asyncio
async def test_search_timeline_top_sets_with_grok_translated_bio_true(
    mock_session_pool
):
    """
    Verify that SearchTimeline with product=Top sets withGrokTranslatedBio=True.
    """
    # Arrange
    provider = TwitterGraphQLProvider(session_pool=mock_session_pool)
    provider._request = AsyncMock(return_value={"data": {}})

    # Act
    await provider.search(query="test query", category="Top", limit=20)

    # Assert
    provider._request.assert_called_once()
    payload = provider._request.call_args.kwargs["json"]
    assert payload["variables"]["product"] == "Top"
    assert payload["variables"]["withGrokTranslatedBio"] is True


@pytest.mark.asyncio
@patch("xservice.providers.twitter_graphql.get_ondemand_file_url")
@patch("xservice.providers.twitter_graphql.ClientTransaction")
async def test_followers_uses_transaction_id(mock_client_transaction_class, mock_get_ondemand_url, mock_session_pool):
    """
    Verify that user_followers method generates and includes the x-client-transaction-id header.
    """
    # Arrange
    mock_get_ondemand_url.return_value = "https://abs.twimg.com/ondemand.js"
    # Mock the transaction ID generator
    mock_generator_instance = mock_client_transaction_class.return_value
    mock_generator_instance.generate_transaction_id.return_value = "mock-tx-id"

    import httpx
    # Mock the HTTP client used for initialization
    mock_http_client_instance = AsyncMock()
    mock_http_client_instance.get.side_effect = [
        Response(200, text=DUMMY_HOME_HTML, request=httpx.Request("GET", "https://x.com")),   # For home page
        Response(200, text=DUMMY_ONDEMAND_JS, request=httpx.Request("GET", "https://abs.twimg.com/ondemand.js"))  # For ondemand.js
    ]
    # To satisfy context manager in AsyncClient
    mock_http_client_instance.__aenter__.return_value = mock_http_client_instance

    provider = TwitterGraphQLProvider(session_pool=mock_session_pool)
    provider._request = AsyncMock(return_value={"data": {}})

    # Since _init_client_transaction uses its own client, we patch it there
    httpx_async_client_patcher = patch(
        "xservice.providers.twitter_graphql.httpx.AsyncClient",
        return_value=mock_http_client_instance
    )
    # Patch the user_info call to avoid another network request
    provider.user_info = AsyncMock(return_value=MagicMock(id="12345"))

    # Act
    with httpx_async_client_patcher:
        await provider.user_followers(username="testuser", limit=50)

    # Assert
    # 1. Check that the transaction ID was generated with the correct parameters
    mock_generator_instance.generate_transaction_id.assert_called_once()
    gen_args = mock_generator_instance.generate_transaction_id.call_args
    op = GRAPHQL_OPERATIONS["Followers"]
    assert gen_args.kwargs["method"] == "GET"
    assert gen_args.kwargs["path"] == f"/i/api/graphql/{op.query_id}/Followers"

    # 2. Check that the main request was called with the correct headers
    provider._request.assert_called_once()
    call_args = provider._request.call_args
    assert call_args.kwargs["headers"]["x-client-transaction-id"] == "mock-tx-id"
    assert call_args.args[0] == "GET" # Followers is a GET request

    # 3. Check variables
    params = call_args.kwargs["params"]
    variables = json.loads(params["variables"])
    assert variables["userId"] == "12345"
    assert variables["count"] == 50
    assert variables["withGrokTranslatedBio"] is False
