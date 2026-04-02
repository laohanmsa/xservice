import json
from typing import Any, Dict, List, Optional

from xservice.parsers.search import DefaultSearchResultParser
from xservice.parsers.tweets import DefaultTweetEntriesParser, DefaultTweetPageParser, DefaultTweetParser
from xservice.parsers.users import DefaultUserParser, DefaultUserPageParser

from .base import BaseProvider
from .exceptions import OperationError
from .models import SearchPage, Tweet, TweetPage, UserPage, UserProfile
from .registry import GRAPHQL_OPERATIONS
from .session_pool import SessionPool

def _extract_instructions(data: dict) -> list[dict]:
    d = data.get("data", data)

    threaded = d.get("threaded_conversation_with_injections_v2", {})
    if threaded.get("instructions"):
        return threaded["instructions"]

    rt_tl = d.get("retweeters_timeline", {}).get("timeline", {})
    if rt_tl.get("instructions"):
        return rt_tl["instructions"]

    fav_tl = d.get("favoriters_timeline", {}).get("timeline", {})
    if fav_tl.get("instructions"):
        return fav_tl["instructions"]

    search = d.get("search_by_raw_query", {}).get("search_timeline", {})
    if search:
        return search.get("timeline", {}).get("instructions", [])

    user_result = d.get("user", {}).get("result", {})

    tl = user_result.get("timeline", {}).get("timeline", {})
    if tl.get("instructions"):
        return tl["instructions"]

    tl2 = user_result.get("timeline_v2", {}).get("timeline", {})
    if tl2.get("instructions"):
        return tl2["instructions"]

    return []

def _extract_entries(data: dict) -> list[dict]:
    instructions = _extract_instructions(data)
    entries: list[dict] = []
    for instr in instructions:
        typ = instr.get("type", "")
        if typ == "TimelineAddEntries":
            entries.extend(instr.get("entries", []))
        elif typ == "TimelinePinEntry":
            entry = instr.get("entry")
            if entry:
                entries.append(entry)
    return entries

class TwitterGraphQLProvider(BaseProvider):
    def __init__(self, session_pool: SessionPool):
        super().__init__(session_pool)
        self._api_url = "https://twitter.com/i/api/graphql"
        self._search_parser = DefaultSearchResultParser()
        self._user_parser = DefaultUserParser()
        self._tweet_entries_parser = DefaultTweetEntriesParser()
        self._tweet_page_parser = DefaultTweetPageParser()
        self._user_page_parser = DefaultUserPageParser()
        self._single_tweet_parser = DefaultTweetParser()

    async def _execute(self, op_name: str, variables: dict) -> dict:
        operation = GRAPHQL_OPERATIONS[op_name]
        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(operation.features),
            "fieldToggles": json.dumps(operation.field_toggles),
        }
        return await self._request("GET", f"{self._api_url}/{operation.query_id}/{op_name}", params=params)

    async def search(self, query: str, category: str = "Latest", limit: int = 20) -> SearchPage:
        # Category mappings (SearchCategory equivalent)
        # We can map top, latest, people, photos, videos to search logic, but actually the GraphQL endpoint
        # usually handles product. For SearchTimeline, 'product': 'Top' or 'Latest'
        product = category if category in ("Top", "Latest", "People", "Photos", "Videos") else "Latest"
        variables = {
            "rawQuery": query,
            "count": limit,
            "querySource": "typed_query",
            "product": product
        }
        response = await self._execute("SearchTimeline", variables)
        entries = _extract_entries(response)
        return self._search_parser.parse(entries, category=category, raw_data=response)

    async def user_by_username(self, username: str) -> Optional[UserProfile]:
        variables = {"screen_name": username, "withSafetyModeUserFields": True}
        response = await self._execute("UserByScreenName", variables)
        try:
            user_data = response.get("data", {}).get("user", {}).get("result", {})
            if not user_data:
                return None
            return self._user_parser.parse(user_data)
        except KeyError as e:
            raise OperationError("Failed to parse user info: key not found", underlying_error=e)

    async def user_by_id(self, user_id: str) -> Optional[UserProfile]:
        variables = {"userId": user_id, "withSafetyModeUserFields": True}
        response = await self._execute("UserByRestId", variables)
        try:
            user_data = response.get("data", {}).get("user", {}).get("result", {})
            if not user_data:
                return None
            return self._user_parser.parse(user_data)
        except KeyError as e:
            raise OperationError("Failed to parse user info: key not found", underlying_error=e)

    async def user_info(self, username: str) -> Optional[UserProfile]:
        return await self.user_by_username(username)

    async def user_tweets(self, username: str, limit: int = 20) -> TweetPage:
        user = await self.user_info(username)
        if not user:
            return TweetPage(tweets=[], count=0)

        variables = {"userId": user.id, "count": limit, "includePromotedContent": True, "withQuickPromoteEligibilityTweetFields": True, "withVoice": True, "withV2Timeline": True}
        response = await self._execute("UserTweets", variables)
        entries = _extract_entries(response)
        return self._tweet_page_parser.parse(entries, data=response)

    async def user_timeline(self, username: str, limit: int = 20) -> TweetPage:
        return await self.user_tweets(username, limit)

    async def user_following(self, username: str, limit: int = 100) -> UserPage:
        user = await self.user_info(username)
        if not user:
            return UserPage(users=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False}
        response = await self._execute("Following", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)

    async def user_followers(self, username: str, limit: int = 100) -> UserPage:
        user = await self.user_info(username)
        if not user:
            return UserPage(users=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False}
        response = await self._execute("Followers", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)

    async def user_likes(self, username: str, limit: int = 20) -> TweetPage:
        user = await self.user_info(username)
        if not user:
            return TweetPage(tweets=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False}
        response = await self._execute("Likes", variables)
        entries = _extract_entries(response)
        return self._tweet_page_parser.parse(entries, data=response)

    async def user_media(self, username: str, limit: int = 20) -> TweetPage:
        user = await self.user_info(username)
        if not user:
            return TweetPage(tweets=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False, "withVoice": True, "withV2Timeline": True}
        response = await self._execute("UserMedia", variables)
        entries = _extract_entries(response)
        return self._tweet_page_parser.parse(entries, data=response)

    async def user_tweets_and_replies(self, username: str, limit: int = 20) -> TweetPage:
        user = await self.user_info(username)
        if not user:
            return TweetPage(tweets=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": True, "withVoice": True, "withV2Timeline": True}
        response = await self._execute("UserTweetsAndReplies", variables)
        entries = _extract_entries(response)
        return self._tweet_page_parser.parse(entries, data=response)

    async def tweet_detail(self, tweet_id: str) -> Optional[Tweet]:
        variables = {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withV2Timeline": True
        }
        response = await self._execute("TweetDetail", variables)
        entries = _extract_entries(response)
        if not entries:
            tweet_result = response.get("data", {}).get("tweetResult", {}).get("result", {})
            if tweet_result:
                try:
                    return self._single_tweet_parser.parse(tweet_result)
                except Exception:
                    pass
            return None

        # Find the focal tweet
        for entry in entries:
            entry_id = entry.get("entryId", "")
            if entry_id.startswith("tweet-"):
                tweet_results = self._tweet_entries_parser.find_key(entry, "tweet_results") if hasattr(self._tweet_entries_parser, "find_key") else []
                # Fallback to local search
                if not tweet_results:
                    from xservice.parsers.tweets import find_key
                    tweet_results = find_key(entry, "tweet_results")
                
                for tr in tweet_results:
                    result = tr.get("result", {})
                    if result.get("rest_id") == tweet_id:
                        try:
                            return self._single_tweet_parser.parse(result)
                        except Exception:
                            pass
        return None

    async def tweet_retweeters(self, tweet_id: str, limit: int = 100) -> UserPage:
        variables = {"tweetId": tweet_id, "count": limit, "includePromotedContent": True}
        response = await self._execute("Retweeters", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)

    async def tweet_favoriters(self, tweet_id: str, limit: int = 100) -> UserPage:
        variables = {"tweetId": tweet_id, "count": limit, "includePromotedContent": True}
        response = await self._execute("Favoriters", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)
