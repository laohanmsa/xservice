from fastapi import APIRouter, Depends, HTTPException, Query

from xservice.api.dependencies import get_provider
from xservice.api.response_models import Tweet, User, UserPage
from xservice.auth import get_api_key
from xservice.models import ApiKey
from xservice.providers.base import Provider
from xservice.providers.exceptions import ProviderError, SessionAcquisitionError

router = APIRouter()


async def handle_provider_call(coroutine):
    try:
        return await coroutine
    except SessionAcquisitionError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{tweet_id}/", response_model=Tweet, tags=["tweets"])
async def get_tweet_detail(
    tweet_id: str,
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    tweet = await handle_provider_call(provider.tweet_detail(tweet_id=tweet_id))
    if not tweet:
        raise HTTPException(status_code=404, detail="Tweet not found")
    
    return Tweet(
        id=tweet.id,
        text=tweet.text,
        user_id=tweet.user_id,
        created_at=tweet.created_at,
        lang=tweet.language,
        quote_count=tweet.metrics.quote_count if tweet.metrics else 0,
        reply_count=tweet.metrics.reply_count if tweet.metrics else 0,
        retweet_count=tweet.metrics.retweet_count if tweet.metrics else 0,
        favorite_count=tweet.metrics.favorite_count if tweet.metrics else 0,
        user=tweet.user.__dict__ if tweet.user else None,
    )


@router.get("/{tweet_id}/retweeters/", response_model=UserPage, tags=["tweets"])
async def get_tweet_retweeters(
    tweet_id: str,
    limit: int = Query(100),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(
        provider.tweet_retweeters(tweet_id=tweet_id, limit=limit)
    )
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
    return UserPage(
        users=api_users,
        count=provider_page.count,
        next_cursor=provider_page.next_cursor,
    )


@router.get("/{tweet_id}/favoriters/", response_model=UserPage, tags=["tweets"])
async def get_tweet_favoriters(
    tweet_id: str,
    limit: int = Query(100),
    provider: Provider = Depends(get_provider),
    _: ApiKey = Depends(get_api_key),
):
    provider_page = await handle_provider_call(
        provider.tweet_favoriters(tweet_id=tweet_id, limit=limit)
    )
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
    return UserPage(
        users=api_users,
        count=provider_page.count,
        next_cursor=provider_page.next_cursor,
    )
