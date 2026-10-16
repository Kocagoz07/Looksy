"""Home feeds: following feed and popular/discover feed."""

from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

import deps

router = APIRouter()
POPULAR_WINDOW = timedelta(days=14)


async def _require_user(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/feed/following")
async def following_feed(request: Request, limit: int = Query(50, ge=1, le=100)):
    user = await _require_user(request)
    author_ids = list(set(user.following or []) | {user.user_id})
    posts = await deps.db.posts.find(
        {"user_id": {"$in": author_ids}, "is_deleted": {"$ne": True}}, {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"posts": posts}


async def _popular(match: dict, limit: int):
    pipeline = [
        {"$match": match},
        {"$addFields": {"score": {"$add": [
            {"$ifNull": ["$likes_count", 0]},
            {"$multiply": [2, {"$size": {"$ifNull": ["$starred_by", []]}}]},
        ]}}},
        {"$sort": {"score": -1, "created_at": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0}},
    ]
    return await deps.db.posts.aggregate(pipeline).to_list(limit)


@router.get("/feed/popular")
async def popular_feed(
    request: Request,
    category: Optional[str] = Query(None, pattern="^(men|women)$"),
    exclude_following: bool = False,
    limit: int = Query(24, ge=1, le=60),
):
    user = await _require_user(request)
    category = category or user.category
    excluded = {user.user_id} | (set(user.following or []) if exclude_following else set())

    author_query = {"user_id": {"$nin": list(excluded)}}
    if category in ("men", "women"):
        authors = await deps.db.users.find({"category": category}, {"_id": 0, "user_id": 1}).to_list(5000)
        author_query = {"user_id": {"$in": [a["user_id"] for a in authors if a["user_id"] not in excluded]}}

    base = {"is_deleted": {"$ne": True}, **author_query}
    since = (datetime.now(timezone.utc) - POPULAR_WINDOW).isoformat()
    posts = await _popular({**base, "created_at": {"$gte": since}}, limit)
    for match in (base, {"is_deleted": {"$ne": True}, "user_id": {"$nin": list(excluded)}}):
        if len(posts) >= limit:
            break
        posts += await _popular({**match, "post_id": {"$nin": [p["post_id"] for p in posts]}}, limit - len(posts))
    return {"posts": posts, "category": category}
