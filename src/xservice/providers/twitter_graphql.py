import json
import asyncio
from typing import Any, Coroutine, Dict, List, Optional

import bs4
import httpx
from x_client_transaction import ClientTransaction
from x_client_transaction.utils import get_ondemand_file_url

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

        # For x-client-transaction-id
        self._client_transaction: Optional[ClientTransaction] = None
        self._ct_lock = asyncio.Lock()
        self._ct_init_task: Optional[asyncio.Task] = None

    async def _ensure_client_transaction_initialized(self):
        """Ensure the ClientTransaction object is initialized, handling concurrency."""
        async with self._ct_lock:
            if self._client_transaction:
                return
            if self._ct_init_task and not self._ct_init_task.done():
                await self._ct_init_task
                return
            self._ct_init_task = asyncio.create_task(self._init_client_transaction())

        await self._ct_init_task
        async with self._ct_lock:
            self._ct_init_task = None


    async def _init_client_transaction(self):
        """
        Fetches x.com homepage and the ondemand.js file to initialize
        the ClientTransaction object needed for generating X-Client-Transaction-Id.
        """
        if self._client_transaction:
            return

        session = await self._session_pool.get_session()
        if not session:
            raise OperationError("No available sessions in the pool to initialize ClientTransaction.")

        try:
            # HTTP/2 is not required for the txid bootstrap fetches.
            async with httpx.AsyncClient(follow_redirects=True) as client:
                headers = session.headers.copy()
                cookies = session.cookies.copy()
                
                # Step 1: Fetch x.com homepage
                home_resp = await client.get("https://x.com", headers=headers, cookies=cookies)
                home_resp.raise_for_status()
                home_html = home_resp.text
                home_page_soup = bs4.BeautifulSoup(home_html, "lxml")

                # Step 2: Get and fetch the ondemand.js file
                ondemand_url = get_ondemand_file_url(response=home_page_soup)
                if not ondemand_url:
                    raise OperationError("Could not find ondemand.js URL in x.com homepage.")

                ondemand_resp = await client.get(ondemand_url, headers=headers, cookies=cookies)
                ondemand_resp.raise_for_status()
                ondemand_text = ondemand_resp.text

                # Step 3: Create the ClientTransaction object
                self._client_transaction = ClientTransaction(
                    home_page_response=home_page_soup, ondemand_file_response=ondemand_text
                )
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            raise OperationError("Failed to fetch resources for X-Client-Transaction-Id generation", underlying_error=e) from e
        except Exception as e:
            # Catch any other exception during init and wrap it
            raise OperationError("Failed to initialize X-Client-Transaction-Id generator", underlying_error=e) from e
        finally:
            if session:
                await self._session_pool.release_session(session.session_id)


    async def _execute_graphql_query(self, op_name: str, variables: dict) -> dict:
        operation = GRAPHQL_OPERATIONS[op_name]
        api_path = f"/{operation.query_id}/{op_name}"
        headers = {}

        if operation.use_transaction_id:
            await self._ensure_client_transaction_initialized()
            if self._client_transaction:
                try:
                    tid = self._client_transaction.generate_transaction_id(method=operation.method, path=f"/i/api/graphql{api_path}")
                    headers["x-client-transaction-id"] = tid
                except Exception as e:
                    raise OperationError("Failed to generate x-client-transaction-id", underlying_error=e)
            else:
                raise OperationError("x-client-transaction-id is required but generator is not initialized.")


        if operation.method == "POST":
            payload = {
                "variables": variables,
                "features": operation.features,
                "fieldToggles": operation.field_toggles,
            }
            return await self._request("POST", f"{self._api_url}{api_path}", json=payload, headers=headers)
        else:  # Default to GET
            params = {
                "variables": json.dumps(variables),
                "features": json.dumps(operation.features),
                "fieldToggles": json.dumps(operation.field_toggles),
            }
            return await self._request("GET", f"{self._api_url}{api_path}", params=params, headers=headers)

    async def search(self, query: str, category: str = "Latest", limit: int = 20, cursor: Optional[str] = None) -> SearchPage:
        product = category if category in ("Top", "Latest", "People", "Photos", "Videos") else "Latest"
        variables = {
            "rawQuery": query,
            "count": limit,
            "querySource": "typed_query",
            "product": product,
            "withGrokTranslatedBio": product in ("Top", "People"),
        }
        if cursor:
            variables["cursor"] = cursor

        response = await self._execute_graphql_query("SearchTimeline", variables)
        entries = _extract_entries(response)
        return self._search_parser.parse(entries, category=category, raw_data=response)

    async def user_by_username(self, username: str) -> Optional[UserProfile]:
        variables = {"screen_name": username, "withSafetyModeUserFields": True}
        response = await self._execute_graphql_query("UserByScreenName", variables)
        try:
            user_data = response.get("data", {}).get("user", {}).get("result", {})
            if not user_data:
                return None
            return self._user_parser.parse(user_data)
        except KeyError as e:
            raise OperationError("Failed to parse user info: key not found", underlying_error=e)

    async def user_by_id(self, user_id: str) -> Optional[UserProfile]:
        variables = {"userId": user_id, "withSafetyModeUserFields": True}
        response = await self._execute_graphql_query("UserByRestId", variables)
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
        response = await self._execute_graphql_query("UserTweets", variables)
        entries = _extract_entries(response)
        return self._tweet_page_parser.parse(entries, data=response)

    async def user_timeline(self, username: str, limit: int = 20) -> TweetPage:
        return await self.user_tweets(username, limit)

    async def user_following(self, username: str, limit: int = 100) -> UserPage:
        user = await self.user_info(username)
        if not user:
            return UserPage(users=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False, "withGrokTranslatedBio": False}
        response = await self._execute_graphql_query("Following", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)

    async def user_followers(self, username: str, limit: int = 100) -> UserPage:
        user = await self.user_info(username)
        if not user:
            return UserPage(users=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False, "withGrokTranslatedBio": False}
        response = await self._execute_graphql_query("Followers", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)

    async def user_likes(self, username: str, limit: int = 20) -> TweetPage:
        user = await self.user_info(username)
        if not user:
            return TweetPage(tweets=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False}
        response = await self._execute_graphql_query("Likes", variables)
        entries = _extract_entries(response)
        return self._tweet_page_parser.parse(entries, data=response)

    async def user_media(self, username: str, limit: int = 20) -> TweetPage:
        user = await self.user_info(username)
        if not user:
            return TweetPage(tweets=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": False, "withVoice": True, "withV2Timeline": True}
        response = await self._execute_graphql_query("UserMedia", variables)
        entries = _extract_entries(response)
        return self._tweet_page_parser.parse(entries, data=response)

    async def user_tweets_and_replies(self, username: str, limit: int = 20) -> TweetPage:
        user = await self.user_info(username)
        if not user:
            return TweetPage(tweets=[], count=0)
        variables = {"userId": user.id, "count": limit, "includePromotedContent": True, "withVoice": True, "withV2Timeline": True}
        response = await self._execute_graphql_query("UserTweetsAndReplies", variables)
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
        response = await self._execute_graphql_query("TweetDetail", variables)
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
        response = await self._execute_graphql_query("Retweeters", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)

    async def tweet_favoriters(self, tweet_id: str, limit: int = 100) -> UserPage:
        variables = {"tweetId": tweet_id, "count": limit, "includePromotedContent": True}
        response = await self._execute_graphql_query("Favoriters", variables)
        entries = _extract_entries(response)
        return self._user_page_parser.parse(entries, data=response)
