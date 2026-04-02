import pytest
from xservice.parsers.base import ParsingError
from xservice.parsers.search import DefaultSearchResultParser
from xservice.parsers.tweets import DefaultTweetParser, DefaultTweetEntriesParser, DefaultTweetPageParser
from xservice.parsers.users import DefaultUserParser, DefaultUserPageParser
from xservice.providers.models import SearchPage, Tweet, UserProfile, TweetPage, UserPage

def test_user_parser_success():
    parser = DefaultUserParser()
    data = {
        "rest_id": "12345",
        "legacy": {
            "name": "Test User",
            "screen_name": "testuser",
            "profile_image_url_https": "https://example.com/profile.jpg",
        },
        "core": {
            "screen_name": "testuser",
            "name": "Test User"
        }
    }
    user = parser.parse(data)
    assert isinstance(user, UserProfile)
    assert user.id == "12345"
    assert user.name == "Test User"
    assert user.username == "testuser"

def test_tweet_parser_success():
    parser = DefaultTweetParser()
    data = {
        "rest_id": "54321",
        "legacy": {
            "full_text": "This is a test tweet.",
            "created_at": "Sun Apr 02 12:34:56 +0000 2023",
        },
        "core": {"user_results": {"result": {"rest_id": "12345", "core": {"screen_name": "testuser", "name": "Test User"}}}},
    }
    tweet = parser.parse(data)
    assert isinstance(tweet, Tweet)
    assert tweet.id == "54321"
    assert tweet.text == "This is a test tweet."
    assert tweet.user_id == "12345"

def test_tweet_entries_parser():
    parser = DefaultTweetEntriesParser()
    data = [
        {
            "entryId": "tweet-111",
            "content": {
                "itemContent": {
                    "tweet_results": {
                        "result": {
                            "rest_id": "111",
                            "legacy": {
                                "full_text": "First tweet",
                                "created_at": "Sun Apr 02 12:34:56 +0000 2023",
                            },
                            "core": {"user_results": {"result": {"rest_id": "user1"}}},
                        }
                    }
                }
            }
        },
        {
            "entryId": "tweet-222",
            "content": {
                "itemContent": {
                    "tweet_results": {
                        "result": {
                            "rest_id": "222",
                            "legacy": {
                                "full_text": "Second tweet",
                                "created_at": "Sun Apr 02 12:34:56 +0000 2023",
                            },
                            "core": {"user_results": {"result": {"rest_id": "user2"}}},
                        }
                    }
                }
            }
        },
    ]
    # Hack the find_key since the input format isn't fully mocked
    def mock_find_key(obj, key):
        if key == "tweet_results":
            return [obj["content"]["itemContent"]["tweet_results"]]
        return []
    import xservice.parsers.tweets
    xservice.parsers.tweets.find_key = mock_find_key
    
    tweets = parser.parse(data)
    assert len(tweets) == 2
    assert tweets[0].id == "111"
    assert tweets[1].id == "222"

def test_search_result_parser():
    parser = DefaultSearchResultParser()
    data = []
    result = parser.parse(data)
    assert isinstance(result, SearchPage)
    assert len(result.tweets) == 0
