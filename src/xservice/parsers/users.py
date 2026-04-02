from typing import Any, List, Optional
from xservice.providers.models import UserProfile, UserSummary, UserPage
from .base import ParsingError, UserParser
from .tweets import get_cursor, _safe_int, find_key

def _extract_user_fields(user_result: dict) -> dict:
    core = user_result.get("core", {})
    legacy = user_result.get("legacy", {})
    username = core.get("screen_name") or legacy.get("screen_name", "unknown")
    name = core.get("name") or legacy.get("name", "Unknown")
    return {"username": username, "name": name}

class DefaultUserParser(UserParser):
    def parse(self, data: dict) -> UserProfile:
        try:
            legacy = data.get("legacy", {})
            user_fields = _extract_user_fields(data)
            return UserProfile(
                id=data.get("rest_id", ""),
                name=user_fields["name"],
                username=user_fields["username"],
                description=legacy.get("description"),
                location=legacy.get("location"),
                url=legacy.get("url"),
                created_at=legacy.get("created_at") or data.get("core", {}).get("created_at"),
                is_blue_verified=data.get("is_blue_verified", False),
                followers_count=_safe_int(legacy.get("followers_count")),
                following_count=_safe_int(legacy.get("friends_count")),
                tweet_count=_safe_int(legacy.get("statuses_count")),
                listed_count=_safe_int(legacy.get("listed_count")),
                profile_image_url=(
                    legacy.get("profile_image_url_https")
                    or data.get("avatar", {}).get("image_url")
                ),
                profile_banner_url=legacy.get("profile_banner_url"),
            )
        except Exception as e:
            raise ParsingError(f"Missing expected key in user data: {e}")

class DefaultUserPageParser:
    def parse(self, entries: List[Any], data: Any = None) -> UserPage:
        users: List[UserSummary] = []
        seen_ids = set()
        cursor = get_cursor(data) if data else None

        for entry in entries:
            entry_id = entry.get("entryId", "")
            if not entry_id.startswith("user-"):
                continue
            
            user_results = find_key(entry, "user_results")
            for ur in user_results:
                result = ur.get("result", {})
                if result.get("__typename") != "User":
                    continue
                rest_id = result.get("rest_id", "")
                if not rest_id:
                    continue
                
                legacy = result.get("legacy", {})
                user_fields = _extract_user_fields(result)
                summary = UserSummary(
                    id=rest_id,
                    username=user_fields["username"],
                    name=user_fields["name"],
                    description=legacy.get("description"),
                    is_blue_verified=result.get("is_blue_verified", False),
                    followers_count=_safe_int(legacy.get("followers_count")),
                    following_count=_safe_int(legacy.get("friends_count")),
                    profile_image_url=(
                        legacy.get("profile_image_url_https")
                        or result.get("avatar", {}).get("image_url")
                    )
                )
                
                if summary.id not in seen_ids:
                    seen_ids.add(summary.id)
                    users.append(summary)
                    
        return UserPage(users=users, count=len(users), next_cursor=cursor)
