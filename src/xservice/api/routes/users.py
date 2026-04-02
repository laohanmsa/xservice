from fastapi import APIRouter, Depends, HTTPException, Query

from xservice.api.dependencies import get_provider
from xservice.api.response_models import (
    Tweet as ApiTweet,
    User as ApiUser,
    UserProfile as ApiUserProfile,
    TweetPage as ApiTweetPage,
    UserPage as ApiUserPage,
)
from xservice.auth import get_api_key
from xservice.models import ApiKey
from xservice.providers.base import Provider
from xservice.providers.exceptions import ProviderError, SessionAcquisitionError
from xservice.providers.models import (
    TweetPage as ProviderTweetPage,
    UserPage as ProviderUserPage,
)

router = APIRouter()

async def handle_provider_call(coroutine):
    try:
        return await coroutine
    except SessionAcquisitionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))

@router.get("/{username}/", response_model=ApiUserProfile, tags=["users"])
async def get_user_by_username(
    username: str,
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    user = await handle_provider_call(provider.user_by_username(username=username))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return ApiUserProfile(
        id=user.id,
        username=user.username,
        name=user.name,
        profile_image_url=user.profile_image_url,
        description=user.description,
        followers_count=user.followers_count,
        following_count=user.following_count,
        statuses_count=user.tweet_count,
        verified=user.is_blue_verified,
    )

@router.get("/id/{user_id}/", response_model=ApiUserProfile, tags=["users"])
async def get_user_by_id(
    user_id: str,
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    user = await handle_provider_call(provider.user_by_id(user_id=user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return ApiUserProfile(
        id=user.id,
        username=user.username,
        name=user.name,
        profile_image_url=user.profile_image_url,
        description=user.description,
        followers_count=user.followers_count,
        following_count=user.following_count,
        statuses_count=user.tweet_count,
        verified=user.is_blue_verified,
    )

def _map_tweet_page(provider_page: ProviderTweetPage) -> ApiTweetPage:
    api_tweets = [
        ApiTweet(
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
    return ApiTweetPage(
        tweets=api_tweets,
        count=provider_page.count,
        next_cursor=provider_page.next_cursor,
    )

def _map_user_page(provider_page: ProviderUserPage) -> ApiUserPage:
    api_users = [
        ApiUser(
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
    return ApiUserPage(
        users=api_users,
        count=provider_page.count,
        next_cursor=provider_page.next_cursor,
    )

@router.get("/{username}/timeline/", response_model=ApiTweetPage, tags=["users"])
async def get_user_timeline(
    username: str,
    limit: int = Query(20),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(provider.user_timeline(username=username, limit=limit))
    return _map_tweet_page(provider_page)

@router.get("/{username}/tweets/", response_model=ApiTweetPage, tags=["users"])
async def get_user_tweets(
    username: str,
    limit: int = Query(20),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(provider.user_tweets(username=username, limit=limit))
    return _map_tweet_page(provider_page)

@router.get(
    "/{username}/following/",
    response_model=ApiUserPage,
    tags=["users"],
    summary="Get accounts this user follows",
    description=(
        "Returns X's current following timeline page. "
        "X does not currently expose a true asc/desc relationship-time ordering "
        "control for this endpoint, so xservice returns the upstream page order "
        "and cursor as-is."
    ),
)
async def get_user_following(
    username: str,
    limit: int = Query(100),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(provider.user_following(username=username, limit=limit))
    return _map_user_page(provider_page)

@router.get(
    "/{username}/followers/",
    response_model=ApiUserPage,
    tags=["users"],
    summary="Get this user's followers",
    description=(
        "Returns X's current followers timeline page. "
        "X does not currently expose a true asc/desc relationship-time ordering "
        "control for this endpoint, so xservice returns the upstream page order "
        "and cursor as-is."
    ),
)
async def get_user_followers(
    username: str,
    limit: int = Query(100),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(provider.user_followers(username=username, limit=limit))
    return _map_user_page(provider_page)

@router.get("/{username}/likes/", response_model=ApiTweetPage, tags=["users"])
async def get_user_likes(
    username: str,
    limit: int = Query(20),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(provider.user_likes(username=username, limit=limit))
    return _map_tweet_page(provider_page)

@router.get("/{username}/media/", response_model=ApiTweetPage, tags=["users"])
async def get_user_media(
    username: str,
    limit: int = Query(20),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(provider.user_media(username=username, limit=limit))
    return _map_tweet_page(provider_page)

@router.get("/{username}/tweets_and_replies/", response_model=ApiTweetPage, tags=["users"])
async def get_user_tweets_and_replies(
    username: str,
    limit: int = Query(20),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(
        provider.user_tweets_and_replies(username=username, limit=limit)
    )
    return _map_tweet_page(provider_page)
