"""24-hour stories: upload from gallery or re-share a post; followers see rings above the feed."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import deps

router = APIRouter()
STORY_TTL = timedelta(hours=24)
MAX_ACTIVE_STORIES = 30


class StoryCreate(BaseModel):
    image_id: str = Field(min_length=24, max_length=24)
    caption: Optional[str] = Field(None, max_length=200)


async def _require_user(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).isoformat()


async def ensure_story_indexes(db):
    await db.stories.create_index("expires_at", expireAfterSeconds=0)
    await db.stories.create_index([("user_id", 1), ("created_at", -1)])
    await db.stories.create_index("story_id", unique=True)


async def _insert_story(user_id: str, image_id: str, caption: Optional[str], shared_post: Optional[dict] = None):
    active = await deps.db.stories.count_documents({"user_id": user_id, "expires_at": {"$gt": _now()}})
    if active >= MAX_ACTIVE_STORIES:
        raise HTTPException(status_code=400, detail=f"You can have up to {MAX_ACTIVE_STORIES} active stories")
    now = _now()
    story = {
        "story_id": f"story_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "image_id": image_id,
        "caption": caption,
        "shared_post": shared_post,
        "viewers": [],
        "created_at": now,
        "expires_at": now + STORY_TTL,
    }
    await deps.db.stories.insert_one(story)
    return _public(story, user_id)


def _public(story: dict, viewer_id: str) -> dict:
    is_owner = story["user_id"] == viewer_id
    out = {
        "story_id": story["story_id"],
        "user_id": story["user_id"],
        "image_id": story["image_id"],
        "caption": story.get("caption"),
        "shared_post": story.get("shared_post"),
        "created_at": _iso(story["created_at"]),
        "expires_at": _iso(story["expires_at"]),
        "seen": is_owner or any(v["user_id"] == viewer_id for v in story.get("viewers", [])),
    }
    if is_owner:
        out["view_count"] = len(story.get("viewers", []))
    return out


async def _get_active(story_id: str) -> dict:
    story = await deps.db.stories.find_one({"story_id": story_id, "expires_at": {"$gt": _now()}}, {"_id": 0})
    if not story:
        raise HTTPException(status_code=404, detail="Story not found or expired")
    return story


@router.post("/stories")
async def create_story(payload: StoryCreate, request: Request):
    user = await _require_user(request)
    try:
        exists = await deps.db["fs.files"].find_one({"_id": ObjectId(payload.image_id)}, {"_id": 1})
    except InvalidId:
        exists = None
    if not exists:
        raise HTTPException(status_code=400, detail="Image not found. Please upload it again.")
    caption = (payload.caption or "").strip() or None
    return await _insert_story(user.user_id, payload.image_id, caption)


@router.post("/stories/from-post/{post_id}")
async def story_from_post(post_id: str, request: Request):
    user = await _require_user(request)
    post = await deps.db.posts.find_one({"post_id": post_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    author = await deps.db.users.find_one({"user_id": post["user_id"]}, {"_id": 0, "name": 1})
    shared = {"post_id": post_id, "author_id": post["user_id"], "author_name": (author or {}).get("name")}
    return await _insert_story(user.user_id, post["image_id"], None, shared)


@router.get("/stories/feed")
async def stories_feed(request: Request):
    user = await _require_user(request)
    owner_ids = [user.user_id] + [u for u in (user.following or []) if u != user.user_id]
    stories = await deps.db.stories.find(
        {"user_id": {"$in": owner_ids}, "expires_at": {"$gt": _now()}}, {"_id": 0}
    ).sort("created_at", 1).to_list(1000)

    by_user = {}
    for s in stories:
        by_user.setdefault(s["user_id"], []).append(_public(s, user.user_id))
    users = await deps.db.users.find(
        {"user_id": {"$in": list(by_user)}}, {"_id": 0, "user_id": 1, "name": 1, "picture": 1}
    ).to_list(len(by_user) or 1)
    profiles = {u["user_id"]: u for u in users}

    groups = [
        {
            "user_id": uid,
            "name": profiles.get(uid, {}).get("name"),
            "picture": profiles.get(uid, {}).get("picture"),
            "is_me": uid == user.user_id,
            "has_unseen": any(not s["seen"] for s in items),
            "latest_at": items[-1]["created_at"],
            "stories": items,
        }
        for uid, items in by_user.items()
    ]
    groups.sort(key=lambda g: (not g["is_me"], not g["has_unseen"], _neg_ts(g["latest_at"])))
    return {"groups": groups}


def _neg_ts(iso: str) -> float:
    return -datetime.fromisoformat(iso).timestamp()


@router.post("/stories/{story_id}/view")
async def view_story(story_id: str, request: Request):
    user = await _require_user(request)
    story = await _get_active(story_id)
    if story["user_id"] != user.user_id:
        await deps.db.stories.update_one(
            {"story_id": story_id, "viewers.user_id": {"$ne": user.user_id}},
            {"$push": {"viewers": {"user_id": user.user_id, "viewed_at": _now().isoformat()}}},
        )
    return {"seen": True}


@router.get("/stories/{story_id}/viewers")
async def story_viewers(story_id: str, request: Request):
    user = await _require_user(request)
    story = await _get_active(story_id)
    if story["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Only the story owner can see viewers")
    viewers = story.get("viewers", [])
    profiles = await deps.db.users.find(
        {"user_id": {"$in": [v["user_id"] for v in viewers]}}, {"_id": 0, "user_id": 1, "name": 1, "picture": 1}
    ).to_list(len(viewers) or 1)
    by_id = {p["user_id"]: p for p in profiles}
    result = [{**by_id.get(v["user_id"], {"user_id": v["user_id"]}), "viewed_at": v["viewed_at"]} for v in viewers]
    result.sort(key=lambda v: v["viewed_at"], reverse=True)
    return {"viewers": result, "count": len(result)}


@router.delete("/stories/{story_id}")
async def delete_story(story_id: str, request: Request):
    user = await _require_user(request)
    result = await deps.db.stories.delete_one({"story_id": story_id, "user_id": user.user_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"deleted": True}
