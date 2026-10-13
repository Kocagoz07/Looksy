"""Share a post with other Looksy users via direct message."""

import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import deps

router = APIRouter()

SHARE_PLACEHOLDER = "Shared a post"
USER_FIELDS = {"_id": 0, "user_id": 1, "name": 1, "picture": 1, "category": 1, "brand_verified": 1}


class SharePostRequest(BaseModel):
    recipient_ids: List[str] = Field(min_length=1, max_length=10)
    note: Optional[str] = Field(None, max_length=500)


async def _require_user(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/share/recipients")
async def share_recipients(request: Request, q: Optional[str] = None):
    user = await _require_user(request)
    if q and len(q.strip()) >= 2:
        query = {"name": {"$regex": re.escape(q.strip()), "$options": "i"}}
    else:
        query = {"user_id": {"$in": list(set(user.following or []) | set(user.followers or []))}}
    query = {"$and": [query, {"user_id": {"$ne": user.user_id}}]}
    users = await deps.db.users.find(query, USER_FIELDS).limit(30).to_list(30)
    following = set(user.following or [])
    for u in users:
        u["is_following"] = u["user_id"] in following
    users.sort(key=lambda u: (not u["is_following"], (u.get("name") or "").lower()))
    return {"users": users}


@router.post("/posts/{post_id}/share")
async def share_post(post_id: str, payload: SharePostRequest, request: Request):
    user = await _require_user(request)
    post = await deps.db.posts.find_one({"post_id": post_id, "is_deleted": {"$ne": True}}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    recipient_ids = [r for r in dict.fromkeys(payload.recipient_ids) if r != user.user_id]
    recipients = await deps.db.users.find({"user_id": {"$in": recipient_ids}}, {"_id": 0, "user_id": 1}).to_list(10)
    if not recipients:
        raise HTTPException(status_code=400, detail="Choose at least one valid recipient")

    author = await deps.db.users.find_one({"user_id": post["user_id"]}, {"_id": 0, "name": 1, "picture": 1})
    note = (payload.note or "").strip()
    caption = post.get("caption") or ""
    shared_post = {
        "post_id": post_id,
        "image_id": post["image_id"],
        "caption": caption[:140],
        "author_id": post["user_id"],
        "author_name": (author or {}).get("name"),
        "author_picture": (author or {}).get("picture"),
        "has_note": bool(note),
    }

    sent = []
    for r in recipients:
        conversation = await deps.chat_manager.get_or_create_direct_conversation(user.user_id, r["user_id"])
        message = await deps.chat_manager.send_message(
            conversation_id=conversation["conversation_id"],
            sender_id=user.user_id,
            content=note or SHARE_PLACEHOLDER,
            message_type="post_share",
            extra={"shared_post": shared_post},
        )
        await deps.chat_manager.broadcast_to_conversation(
            conversation["conversation_id"], {"type": "message:new", "message": message}, exclude_user=user.user_id
        )
        sent.append({"recipient_id": r["user_id"], "conversation_id": conversation["conversation_id"]})

    return {"shared": len(sent), "results": sent}
