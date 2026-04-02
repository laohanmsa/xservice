from typing import Dict, List, Optional, Tuple, Any

from xservice.providers.models import Tweet, TweetUser, TweetMetrics, TweetPage
from .base import ParsingError, TweetEntriesParser, TweetParser

def _safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def find_key(obj: Any, key: str) -> list:
    results: list = []
    if isinstance(obj, dict):
        if key in obj:
            results.append(obj[key])
        for v in obj.values():
            results.extend(find_key(v, key))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_key(item, key))
    return results

def get_cursor(data: Any) -> Optional[str]:
    entries = find_key(data, "entries")
    for entry_list in entries:
        if not isinstance(entry_list, list):
            continue
        for entry in entry_list:
            entry_id = entry.get("entryId", "")
            if "cursor-bottom" in entry_id:
                content = entry.get("content", {})
                value = content.get("value") or content.get("itemContent", {}).get("value")
                if value:
                    return value
    return None

class DefaultTweetParser(TweetParser):
    def parse(self, data: Dict) -> Tweet:
        typename = data.get("__typename")
        if typename == "TweetWithVisibilityResults":
            data = data.get("tweet", data)
            
        legacy = data.get("legacy", {})
        core = data.get("core", {})
        user_result = core.get("user_results", {}).get("result", {})

        core_user = user_result.get("core", {})
        legacy_user = user_result.get("legacy", {})
        username = core_user.get("screen_name") or legacy_user.get("screen_name", "unknown")
        name = core_user.get("name") or legacy_user.get("name", "Unknown")

        user = TweetUser(
            id=user_result.get("rest_id", ""),
            username=username,
            name=name,
        )

        metrics = TweetMetrics(
            retweet_count=_safe_int(legacy.get("retweet_count")),
            favorite_count=_safe_int(legacy.get("favorite_count")),
            reply_count=_safe_int(legacy.get("reply_count")),
            quote_count=_safe_int(legacy.get("quote_count")),
            bookmark_count=_safe_int(legacy.get("bookmark_count")),
            view_count=_safe_int(data.get("views", {}).get("count")) if data.get("views", {}).get("count") is not None else None,
        )

        full_text = legacy.get("full_text", "")
        is_retweet = full_text.startswith("RT @")

        return Tweet(
            id=data.get("rest_id", ""),
            text=full_text,
            user_id=user.id,
            created_at=legacy.get("created_at") or "",
            user=user,
            metrics=metrics,
            is_retweet=is_retweet,
            is_quote_status=legacy.get("is_quote_status", False),
            quoted_tweet_id=legacy.get("quoted_status_id_str"),
            language=legacy.get("lang"),
            source=data.get("source")
        )

class DefaultTweetEntriesParser(TweetEntriesParser):
    def __init__(self, tweet_parser: TweetParser = None):
        self._tweet_parser = tweet_parser or DefaultTweetParser()

    def parse(self, data: List[Dict]) -> List[Tweet]:
        parsed_tweets = []
        seen_ids = set()
        
        for entry in data:
            entry_id = entry.get("entryId", "")
            
            if entry_id.startswith("tweet-") or entry_id.startswith("promoted-tweet-"):
                tweet_results = find_key(entry, "tweet_results")
                for tr in tweet_results:
                    result = tr.get("result", {})
                    if not result:
                        continue
                    try:
                        parsed = self._tweet_parser.parse(result)
                        if parsed.id and parsed.id not in seen_ids:
                            seen_ids.add(parsed.id)
                            parsed_tweets.append(parsed)
                    except Exception:
                        pass

            elif entry_id.startswith("profile-conversation-"):
                tweet_results = find_key(entry, "tweet_results")
                for tr in tweet_results:
                    result = tr.get("result", {})
                    if not result:
                        continue
                    try:
                        parsed = self._tweet_parser.parse(result)
                        if parsed.id and parsed.id not in seen_ids:
                            seen_ids.add(parsed.id)
                            parsed_tweets.append(parsed)
                    except Exception:
                        pass
                        
            elif entry_id.startswith("profile-grid-"):
                items = entry.get("content", {}).get("items", [])
                for item in items:
                    ic = item.get("item", {}).get("itemContent", {})
                    tr = ic.get("tweet_results", {})
                    result = tr.get("result", {})
                    if not result:
                        continue
                    try:
                        parsed = self._tweet_parser.parse(result)
                        if parsed.id and parsed.id not in seen_ids:
                            seen_ids.add(parsed.id)
                            parsed_tweets.append(parsed)
                    except Exception:
                        pass
                        
        return parsed_tweets

class DefaultTweetPageParser:
    def __init__(self, tweet_entries_parser: TweetEntriesParser = None):
        self._tweet_entries_parser = tweet_entries_parser or DefaultTweetEntriesParser()

    def parse(self, entries: List[Dict], data: Any = None) -> TweetPage:
        tweets = self._tweet_entries_parser.parse(entries)
        cursor = get_cursor(data) if data else None
        return TweetPage(tweets=tweets, count=len(tweets), next_cursor=cursor)
