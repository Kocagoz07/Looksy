"""AI Outfit Generator routes."""

from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
import logging

import deps

logger = logging.getLogger(__name__)

router = APIRouter()


class OutfitGenerateRequest(BaseModel):
    occasion: str = "everyday"
    style: str = "casual"
    season: str = "all-season"
    budget: Optional[str] = None
    color_preference: Optional[str] = None
    additional_notes: Optional[str] = None
    include_affiliate_links: bool = True


class StyleProfileRequest(BaseModel):
    favorite_styles: List[str] = []
    favorite_colors: List[str] = []
    body_type: Optional[str] = None
    sizes: Dict[str, str] = {}
    avoid: List[str] = []
    budget_preference: Optional[str] = None


@router.post("/outfits/generate")
async def generate_outfit(payload: OutfitGenerateRequest, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not deps.outfit_generator:
        raise HTTPException(status_code=503, detail="Outfit generator not ready")

    try:
        result = await deps.outfit_generator.generate_outfit(
            user_id=user.user_id,
            occasion=payload.occasion,
            style=payload.style,
            season=payload.season,
            budget=payload.budget,
            color_preference=payload.color_preference,
            additional_notes=payload.additional_notes,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))

    if payload.include_affiliate_links and deps.affiliate_engine:
        items = result.get("outfit", {}).get("items", []) or []
        try:
            suggestions = await deps.affiliate_engine.suggest_for_items(
                items=items, user_id=user.user_id, budget=payload.budget
            )
            links = await deps.affiliate_engine.create_links(
                user_id=user.user_id,
                suggestions=suggestions,
                outfit_id=result["outfit_id"],
            )
            result["affiliate_links"] = links
        except Exception as e:
            logger.warning(f"Affiliate link generation failed: {e}")
            result["affiliate_links"] = []

    return result


@router.get("/outfits/mine")
async def my_outfits(request: Request, limit: int = 20):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    outfits = await deps.outfit_generator.get_user_outfits(user.user_id, limit)
    return {"outfits": outfits, "count": len(outfits)}


@router.post("/outfits/{outfit_id}/save")
async def save_outfit(outfit_id: str, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    success = await deps.outfit_generator.save_outfit(user.user_id, outfit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return {"saved": True, "outfit_id": outfit_id}


@router.get("/outfits/style-profile")
async def get_style_profile(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    profile = await deps.outfit_generator.get_user_style_profile(user.user_id)
    return profile or {"user_id": user.user_id}


@router.put("/outfits/style-profile")
async def update_style_profile(payload: StyleProfileRequest, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    updated = await deps.outfit_generator.update_user_style_profile(
        user.user_id, payload.model_dump()
    )
    return updated


@router.get("/outfits/trending")
async def trending_styles(limit: int = 10):
    return {"trending": await deps.outfit_generator.get_trending_styles(limit)}


@router.get("/outfits/options")
async def outfit_options():
    """Static options for the UI (style, occasion, season categories)."""
    from outfit_generator import OutfitGenerator as OG
    return {
        "styles": OG.STYLE_CATEGORIES,
        "occasions": OG.OCCASIONS,
        "seasons": OG.SEASONS,
    }


@router.get("/outfits/{outfit_id}")
async def get_outfit(outfit_id: str, request: Request):
    """Return a previously-generated outfit + its persisted affiliate links."""
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    outfit_doc = await deps.db.generated_outfits.find_one(
        {"outfit_id": outfit_id, "user_id": user.user_id},
        {"_id": 0},
    )
    if not outfit_doc:
        raise HTTPException(status_code=404, detail="Outfit not found")
    links = await deps.affiliate_engine.get_links_for_outfit(outfit_id)
    return {
        "outfit_id": outfit_id,
        "outfit": outfit_doc.get("generated_outfit", {}),
        "request": outfit_doc.get("request", {}),
        "created_at": outfit_doc.get("created_at"),
        "saved": outfit_doc.get("saved", False),
        "affiliate_links": [link for link in links if link.get("user_id") == user.user_id],
    }
