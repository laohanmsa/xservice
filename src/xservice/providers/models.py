import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class Session:
    session_id: str
    headers: Dict[str, str]
    cookies: Dict[str, str]
    db_id: int | None = None
    rate_limit_info: Dict[str, int] = field(default_factory=dict)
    last_used: float = field(default_factory=time.time)
    in_use: bool = False


@dataclass
class RateLimit:
    limit: int
    remaining: int
    reset: int

@dataclass
class TweetMetrics:
    retweet_count: int = 0
    favorite_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    bookmark_count: int = 0
    view_count: Optional[int] = None

@dataclass
class TweetUser:
    id: str
    username: str
    name: str

@dataclass
class Tweet:
    id: str
    text: str
    user_id: str
    created_at: str
    user: Optional[TweetUser] = None
    metrics: Optional[TweetMetrics] = None
    is_retweet: bool = False
    is_quote_status: bool = False
    quoted_tweet_id: Optional[str] = None
    language: Optional[str] = None
    source: Optional[str] = None

@dataclass
class UserSummary:
    id: str
    username: str
    name: str
    description: Optional[str] = None
    is_blue_verified: bool = False
    followers_count: int = 0
    following_count: int = 0
    profile_image_url: Optional[str] = None

@dataclass
class UserProfile:
    id: str
    username: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    is_blue_verified: bool = False
    followers_count: int = 0
    following_count: int = 0
    tweet_count: int = 0
    listed_count: int = 0
    profile_image_url: Optional[str] = None
    profile_banner_url: Optional[str] = None

@dataclass
class TweetPage:
    tweets: List[Tweet]
    count: int
    next_cursor: Optional[str] = None

@dataclass
class SearchPage:
    tweets: List[Tweet] = field(default_factory=list)
    users: List[UserSummary] = field(default_factory=list)
    count: int = 0
    category: str = ""
    next_cursor: Optional[str] = None

@dataclass
class UserPage:
    users: List[UserSummary]
    count: int
    next_cursor: Optional[str] = None

# Backward compatibility aliases for base.py and others
SearchResult = SearchPage
User = UserProfile
