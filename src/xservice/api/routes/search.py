from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Literal
from xservice.api.dependencies import get_provider
from xservice.api.response_models import SearchPage, Tweet, User
from xservice.providers.base import Provider
from xservice.providers.exceptions import ProviderError, SessionAcquisitionError
from xservice.auth import get_api_key
from xservice.models import ApiKey

router = APIRouter()

SearchCategory = Literal["Top", "Latest", "People", "Photos", "Videos"]

@router.get(
    "/",
    response_model=SearchPage,
    summary="Search for tweets and users.",
    tags=["search"],
)
async def search(
    q: str = Query(..., description="The search query."),
    category: SearchCategory = Query("Latest", description="The search category."),
    limit: int = Query(20, description="The maximum number of results to return."),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    """
    Performs a search for tweets and users matching the query.
    """
    try:
        provider_page = await provider.search(query=q, category=category, limit=limit)
        
        # Explicitly map from provider models to response models
        api_tweets = [
            Tweet(
                id=t.id,
                text=t.text,
                user_id=t.user_id,
                created_at=t.created_at,
                lang=t.language,
                quote_count=t.metrics.quote_count if t.metrics else 0,
                reply_count=t.metrics.reply_count if t.metrics else 0,
                retweet_count=t.metrics.retweet_count if t.metrics else 0,
                favorite_count=t.metrics.favorite_count if t.metrics else 0,
                user=t.user.__dict__ if t.user else None,
            )
            for t in provider_page.tweets
        ]
        
        api_users = [
            User(
                id=u.id,
                username=u.username,
                name=u.name,
                profile_image_url=u.profile_image_url,
                description=u.description,
                followers_count=u.followers_count,
                following_count=u.following_count,
                verified=u.is_blue_verified,
            )
            for u in provider_page.users
        ]

        return SearchPage(
            tweets=api_tweets,
            users=api_users,
            count=provider_page.count,
            category=provider_page.category,
            next_cursor=provider_page.next_cursor,
        )
    except SessionAcquisitionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))
