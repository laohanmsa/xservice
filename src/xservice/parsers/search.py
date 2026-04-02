from typing import Any, List, Optional
from xservice.providers.models import SearchPage
from .base import SearchResultParser
from .tweets import DefaultTweetEntriesParser, get_cursor
from .users import DefaultUserPageParser

class DefaultSearchResultParser(SearchResultParser):
    def __init__(self, tweet_entries_parser: Optional[DefaultTweetEntriesParser] = None, user_page_parser: Optional[DefaultUserPageParser] = None):
        self._tweet_entries_parser = tweet_entries_parser or DefaultTweetEntriesParser()
        self._user_page_parser = user_page_parser or DefaultUserPageParser()

    def parse(self, data: List[dict], category: str = "Latest", raw_data: Any = None) -> SearchPage:
        cursor = get_cursor(raw_data) if raw_data else None

        if category == "People":
            user_page = self._user_page_parser.parse(data, raw_data)
            return SearchPage(
                users=user_page.users,
                tweets=[],
                count=user_page.count,
                category=category,
                next_cursor=user_page.next_cursor,
            )
        
        tweets = self._tweet_entries_parser.parse(data)
        return SearchPage(
            tweets=tweets,
            users=[],
            count=len(tweets),
            category=category,
            next_cursor=cursor,
        )
