"""Tracked redirects for post product links + owner-only click stats."""

from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

import deps

router = APIRouter()


async def _get_post(post_id: str) -> dict:
    post = await deps.db.posts.find_one(
        {"post_id": post_id, "is_deleted": {"$ne": True}}, {"_id": 0, "user_id": 1, "products": 1}
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def _safe_url(raw: str) -> str:
    raw = (raw or "").strip()
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    if parsed.scheme not in ("http", "https") or "." not in parsed.netloc:
        raise HTTPException(status_code=400, detail="Invalid product link")
    return parsed.geturl()


@router.get("/posts/{post_id}/products/{index}/go")
async def go_to_product(post_id: str, index: int, request: Request):
    post = await _get_post(post_id)
    products = post.get("products") or []
    if not 0 <= index < len(products):
        raise HTTPException(status_code=404, detail="Product not found")
    target = _safe_url(products[index].get("url"))

    user = await deps.get_current_user(request)
    if not user or user.user_id != post["user_id"]:
        await deps.db.post_product_clicks.insert_one({
            "post_id": post_id,
            "index": index,
            "user_id": user.user_id if user else None,
            "ip_address": request.client.host if request.client else None,
            "clicked_at": datetime.now(timezone.utc).isoformat(),
        })
    return RedirectResponse(url=target, status_code=302)


@router.get("/posts/{post_id}/product-clicks")
async def product_clicks(post_id: str, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    post = await _get_post(post_id)
    if post["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Only the post owner can see product clicks")

    rows = await deps.db.post_product_clicks.aggregate([
        {"$match": {"post_id": post_id}},
        {"$group": {"_id": "$index", "clicks": {"$sum": 1}}},
    ]).to_list(100)
    counts = {r["_id"]: r["clicks"] for r in rows}
    items = [{"index": i, "name": p.get("name"), "clicks": counts.get(i, 0)} for i, p in enumerate(post.get("products") or [])]
    return {"products": items, "total_clicks": sum(it["clicks"] for it in items)}
