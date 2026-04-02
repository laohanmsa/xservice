from typing import Union, Optional
import pytest
from xservice.providers import contracts
from xservice.providers.models import SearchPage, Tweet, UserProfile, TweetPage, UserPage

@pytest.mark.asyncio
async def test_provider_protocol_adherence():
    class MyProvider(contracts.Provider):
        async def search(self, query: str, category: str = "Latest", limit: int = 20) -> SearchPage:
            return SearchPage(tweets=[], count=0)

        async def user_by_username(self, username: str) -> Optional[UserProfile]:
            if username == "exists":
                return UserProfile(id="1", username="exists", name="Test User")
            return None
            
        async def user_by_id(self, user_id: str) -> Optional[UserProfile]:
            return None

        async def user_info(self, username: str) -> Optional[UserProfile]:
            return await self.user_by_username(username)

        async def user_timeline(self, username: str, limit: int = 20) -> TweetPage:
            return TweetPage(tweets=[], count=0)

        async def user_tweets(self, username: str, limit: int = 20) -> TweetPage:
            return TweetPage(tweets=[], count=0)
            
        async def user_following(self, username: str, limit: int = 100) -> UserPage:
            return UserPage(users=[], count=0)
            
        async def user_followers(self, username: str, limit: int = 100) -> UserPage:
            return UserPage(users=[], count=0)
            
        async def user_likes(self, username: str, limit: int = 20) -> TweetPage:
            return TweetPage(tweets=[], count=0)
            
        async def user_media(self, username: str, limit: int = 20) -> TweetPage:
            return TweetPage(tweets=[], count=0)
            
        async def user_tweets_and_replies(self, username: str, limit: int = 20) -> TweetPage:
            return TweetPage(tweets=[], count=0)
            
        async def tweet_detail(self, tweet_id: str) -> Optional[Tweet]:
            return None
            
        async def tweet_retweeters(self, tweet_id: str, limit: int = 100) -> UserPage:
            return UserPage(users=[], count=0)
            
        async def tweet_favoriters(self, tweet_id: str, limit: int = 100) -> UserPage:
            return UserPage(users=[], count=0)

        async def close(self) -> None:
            pass

    provider: contracts.Provider = MyProvider()

    assert isinstance(provider, contracts.Provider)
    search_result = await provider.search("test")
    assert isinstance(search_result, SearchPage)

    user_info = await provider.user_info("exists")
    assert isinstance(user_info, UserProfile)

    user_info_none = await provider.user_info("doesnotexist")
    assert user_info_none is None

    user_tweets = await provider.user_tweets("test")
    assert isinstance(user_tweets, TweetPage)

def test_twitter_graphql_provider_instantiation():
    from xservice.providers.session_pool import SessionPool
    from xservice.providers.twitter_graphql import TwitterGraphQLProvider
    try:
        session_pool = SessionPool()
        provider = TwitterGraphQLProvider(session_pool)
        import asyncio
        asyncio.run(provider.close())
    except Exception as e:
        pytest.fail(f"TwitterGraphQLProvider instantiation failed: {e}")
