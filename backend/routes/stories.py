"""24-hour stories: upload from gallery or re-share a post; followers see rings above the feed."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from urllib.parse import urlparse

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

import deps

router = APIRouter()
STORY_TTL = timedelta(hours=24)
MAX_ACTIVE_STORIES = 30
MAX_PRODUCTS = 5


class StoryProduct(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(max_length=2000)
    price: Optional[float] = Field(None, ge=0, le=100000)

    @field_validator("url")
    @classmethod
    def http_url(cls, v: str) -> str:
        v = v.strip()
        parsed = urlparse(v if "://" in v else f"https://{v}")
        if parsed.scheme not in ("http", "https") or "." not in parsed.netloc:
            raise ValueError("Product link must be a valid web address")
        return parsed.geturl()


class StoryCreate(BaseModel):
    image_id: str = Field(min_length=24, max_length=24)
    caption: Optional[str] = Field(None, max_length=200)
    products: List[StoryProduct] = Field(default_factory=list, max_length=MAX_PRODUCTS)


class StoryFromPost(BaseModel):
    caption: Optional[str] = Field(None, max_length=200)
    products: Optional[List[StoryProduct]] = Field(None, max_length=MAX_PRODUCTS)


def _retailer(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


async def _create_product_links(user_id: str, story_id: str, products: List[StoryProduct]) -> List[dict]:
    now = _now().isoformat()
    out = []
    for p in products:
        link_id = f"aff_{uuid.uuid4().hex[:12]}"
        retailer = _retailer(p.url)
        await deps.db.affiliate_links.insert_one({
            "link_id": link_id, "user_id": user_id, "story_id": story_id, "outfit_id": None, "post_id": None,
            "item": p.name, "category": "story_tag", "color": None, "retailer": retailer,
            "search_query": p.name, "target_url": p.url, "commission_rate": 0.0,
            "clicks": 0, "conversions": 0, "estimated_earnings_eur": 0.0, "created_at": now,
        })
        out.append({"link_id": link_id, "name": p.name, "price": p.price})
    return out


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


async def _insert_story(user_id: str, image_id: str, caption: Optional[str],
                        shared_post: Optional[dict] = None, products: Optional[List[StoryProduct]] = None):
    active = await deps.db.stories.count_documents({"user_id": user_id, "expires_at": {"$gt": _now()}})
    if active >= MAX_ACTIVE_STORIES:
        raise HTTPException(status_code=400, detail=f"You can have up to {MAX_ACTIVE_STORIES} active stories")
    now = _now()
    story_id = f"story_{uuid.uuid4().hex[:12]}"
    story = {
        "story_id": story_id,
        "user_id": user_id,
        "image_id": image_id,
        "caption": caption,
        "shared_post": shared_post,
        "products": await _create_product_links(user_id, story_id, products or []),
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
        "products": [{k: v for k, v in p.items() if k != "retailer"} for p in story.get("products", [])],
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
    return await _insert_story(user.user_id, payload.image_id, caption, products=payload.products)


@router.post("/stories/from-post/{post_id}")
async def story_from_post(post_id: str, request: Request, payload: Optional[StoryFromPost] = None):
    user = await _require_user(request)
    post = await deps.db.posts.find_one({"post_id": post_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    author = await deps.db.users.find_one({"user_id": post["user_id"]}, {"_id": 0, "name": 1})
    shared = {"post_id": post_id, "author_id": post["user_id"], "author_name": (author or {}).get("name")}
    payload = payload or StoryFromPost()
    if payload.products is None:
        products = []
        for p in (post.get("products") or [])[:MAX_PRODUCTS]:
            try:
                products.append(StoryProduct(name=p.get("name") or "Product", url=p.get("url") or ""))
            except ValueError:
                continue
    else:
        products = payload.products
    caption = (payload.caption or "").strip() or None
    return await _insert_story(user.user_id, post["image_id"], caption, shared, products)


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
    link_ids = [p["link_id"] for p in story.get("products", [])]
    links = await deps.db.affiliate_links.find(
        {"link_id": {"$in": link_ids}}, {"_id": 0, "link_id": 1, "clicks": 1}
    ).to_list(MAX_PRODUCTS)
    clicks = {lk["link_id"]: lk.get("clicks", 0) for lk in links}
    product_clicks = [
        {"link_id": p["link_id"], "name": p["name"], "clicks": clicks.get(p["link_id"], 0)}
        for p in story.get("products", [])
    ]
    return {"viewers": result, "count": len(result), "product_clicks": product_clicks,
            "total_clicks": sum(pc["clicks"] for pc in product_clicks)}


@router.delete("/stories/{story_id}")
async def delete_story(story_id: str, request: Request):
    user = await _require_user(request)
    result = await deps.db.stories.delete_one({"story_id": story_id, "user_id": user.user_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Story not found")
    return {"deleted": True}
