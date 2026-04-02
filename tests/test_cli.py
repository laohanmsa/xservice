
import io
import json
import os
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock, ANY

import pytest

from xservice import cli


@pytest.fixture
def mock_urlopen():
    with patch("urllib.request.urlopen") as mock:
        yield mock


def capture_cli_output(argv):
    f = io.StringIO()
    # Capture stdout
    with redirect_stdout(f):
        # We also need to capture stderr for error cases, but for happy path this is fine
        return_code = cli.main(argv)
    return f.getvalue(), return_code


def test_health(mock_urlopen):
    mock_response = MagicMock()
    # This simulates the context manager `with urlopen(...) as response:`
    mock_response.__enter__.return_value.status = 200
    # The response from read() should be bytes
    mock_response.__enter__.return_value.read.return_value = b'{"status": "ok"}'
    # The return value of urlopen is the context manager itself
    mock_urlopen.return_value = mock_response

    output, return_code = capture_cli_output(["health"])

    assert return_code == 0
    assert json.loads(output) == {"status": "ok"}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://localhost:8000/api/v1/health/"
    assert request.method == "GET"


def test_search(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"tweets": []}'
    mock_urlopen.return_value = mock_response

    output, return_code = capture_cli_output(
        ["search", "test query", "--category", "Top", "--limit", "10"]
    )
    
    assert return_code == 0
    assert json.loads(output) == {"tweets": []}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://localhost:8000/api/v1/search/?q=test+query&category=Top&limit=10"


def test_user_profile(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"username": "testuser"}'
    mock_urlopen.return_value = mock_response

    output, return_code = capture_cli_output(["user", "profile", "testuser"])

    assert return_code == 0
    assert json.loads(output) == {"username": "testuser"}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://localhost:8000/api/v1/users/testuser/"

@pytest.mark.parametrize("command", [
    "timeline", "tweets", "followers", "following", "likes", "media"
])
def test_user_commands_with_limit(mock_urlopen, command):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"items": []}'
    mock_urlopen.return_value = mock_response

    output, return_code = capture_cli_output(["user", command, "testuser", "--limit", "5"])

    assert return_code == 0
    assert json.loads(output) == {"items": []}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == f"http://localhost:8000/api/v1/users/testuser/{command}/?limit=5"


def test_user_tweets_and_replies(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"items": []}'
    mock_urlopen.return_value = mock_response

    output, return_code = capture_cli_output(["user", "tweets-and-replies", "testuser", "--limit", "5"])

    assert return_code == 0
    assert json.loads(output) == {"items": []}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://localhost:8000/api/v1/users/testuser/tweets_and_replies/?limit=5"

def test_tweet_detail(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"id": "123"}'
    mock_urlopen.return_value = mock_response

    output, return_code = capture_cli_output(["tweet", "detail", "123"])

    assert return_code == 0
    assert json.loads(output) == {"id": "123"}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://localhost:8000/api/v1/tweets/123/"


@pytest.mark.parametrize("command", ["retweeters", "favoriters"])
def test_tweet_commands_with_limit(mock_urlopen, command):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"users": []}'
    mock_urlopen.return_value = mock_response

    output, return_code = capture_cli_output(["tweet", command, "123", "--limit", "5"])

    assert return_code == 0
    assert json.loads(output) == {"users": []}
    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == f"http://localhost:8000/api/v1/tweets/123/{command}/?limit=5"


def test_base_url_override(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"status": "ok"}'
    mock_urlopen.return_value = mock_response

    capture_cli_output(["--base-url", "http://test.com/api", "health"])

    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://test.com/api/health/"


def test_api_key_override(mock_urlopen):
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"status": "ok"}'
    mock_urlopen.return_value = mock_response

    capture_cli_output(["--api-key", "test-key", "health"])

    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    api_key_header = next((v for k, v in request.header_items() if k.lower() == 'x-api-key'), None)
    assert api_key_header == "test-key"


def test_api_key_env_var(mock_urlopen, monkeypatch):
    monkeypatch.setenv("XSERVICE_API_KEY", "env-key")
    mock_response = MagicMock()
    mock_response.__enter__.return_value.status = 200
    mock_response.__enter__.return_value.read.return_value = b'{"status": "ok"}'
    mock_urlopen.return_value = mock_response

    capture_cli_output(["health"])

    mock_urlopen.assert_called_once()
    request = mock_urlopen.call_args[0][0]
    api_key_header = next((v for k, v in request.header_items() if k.lower() == 'x-api-key'), None)
    assert api_key_header == "env-key"
