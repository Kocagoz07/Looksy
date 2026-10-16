"""Smart Affiliate Engine routes."""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

import deps

router = APIRouter()


class AffiliateSuggestRequest(BaseModel):
    items: List[Dict]
    budget: Optional[str] = None
    outfit_id: Optional[str] = None
    post_id: Optional[str] = None
    persist: bool = True


@router.post("/affiliate/suggest")
async def affiliate_suggest(payload: AffiliateSuggestRequest, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not deps.affiliate_engine:
        raise HTTPException(status_code=503, detail="Affiliate engine not ready")

    suggestions = await deps.affiliate_engine.suggest_for_items(
        items=payload.items, user_id=user.user_id, budget=payload.budget
    )
    links: List[Dict] = []
    if payload.persist:
        links = await deps.affiliate_engine.create_links(
            user_id=user.user_id,
            suggestions=suggestions,
            outfit_id=payload.outfit_id,
            post_id=payload.post_id,
        )
    return {"suggestions": suggestions, "links": links}


@router.get("/affiliate/track/{link_id}")
async def affiliate_track(link_id: str, request: Request):
    """Track a click (platform CPC ledger) and redirect to the retailer. Public endpoint."""
    link = await deps.db.affiliate_links.find_one({"link_id": link_id}, {"_id": 0})
    if not link:
        raise HTTPException(status_code=404, detail="Affiliate link not found")
    user = await deps.get_current_user(request)
    result = await deps.click_revenue.record(
        request=request, user=user,
        source="story_product" if link.get("story_id") else "affiliate",
        link_ref=link_id, owner_id=link.get("user_id"), target_url=link["target_url"],
        extra={"story_id": link.get("story_id"), "outfit_id": link.get("outfit_id"), "post_id": link.get("post_id")},
    )
    if not {"bot", "ip_rate_limit", "self_click"} & set(result["reasons"]):
        await deps.db.affiliate_links.update_one({"link_id": link_id}, {"$inc": {"clicks": 1}})
    return RedirectResponse(url=result["redirect_url"], status_code=302)


@router.get("/affiliate/my-links")
async def my_affiliate_links(request: Request, limit: int = 50):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    links = await deps.affiliate_engine.get_links_for_user(user.user_id, limit)
    return {"links": links, "count": len(links)}


@router.get("/affiliate/my-stats")
async def my_affiliate_stats(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await deps.affiliate_engine.get_user_stats(user.user_id)


@router.get("/affiliate/outfit/{outfit_id}")
async def affiliate_for_outfit(outfit_id: str, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    links = await deps.affiliate_engine.get_links_for_outfit(outfit_id)
    return {"links": [link for link in links if link.get("user_id") == user.user_id]}


@router.get("/affiliate/post/{post_id}")
async def affiliate_for_post(post_id: str, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    links = await deps.affiliate_engine.get_links_for_post(post_id)
    return {"links": [link for link in links if link.get("user_id") == user.user_id]}
