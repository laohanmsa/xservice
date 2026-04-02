from pydantic import BaseModel, Field
from typing import List, Optional, Any

# Re-creating response models based on provider contract and legacy behavior.
# The provider models are dataclasses, but for FastAPI, Pydantic models are better.

class Tweet(BaseModel):
    id: str
    text: str
    user_id: str
    created_at: str
    # Common tweet fields, default to None if not available
    lang: Optional[str] = None
    quote_count: Optional[int] = None
    reply_count: Optional[int] = None
    retweet_count: Optional[int] = None
    favorite_count: Optional[int] = None
    # Assuming the provider model might return these, based on common twitter data
    entities: dict = Field(default_factory=dict)
    user: Optional[Any] = None # Can be a user object, but to avoid circular deps for now

class User(BaseModel):
    id: str
    username: str
    name: str
    profile_image_url: Optional[str] = None
    # Common user fields
    description: Optional[str] = None
    followers_count: Optional[int] = None
    following_count: Optional[int] = None
    statuses_count: Optional[int] = None
    verified: Optional[bool] = None

# UserProfile is often the same as User, but can be extended if needed
UserProfile = User

class TweetPage(BaseModel):
    tweets: List[Tweet]
    count: int
    next_cursor: Optional[str] = None

class UserPage(BaseModel):
    users: List[User]
    count: int
    next_cursor: Optional[str] = None

class SearchPage(BaseModel):
    tweets: List[Tweet]
    users: List[User]
    count: int
    category: str
    next_cursor: Optional[str] = None
