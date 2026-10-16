"""Live currency conversion routes (USD → EUR)."""

from fastapi import APIRouter, HTTPException, Request

import deps
from currency import get_converter

router = APIRouter()


@router.get("/currency/rate")
async def get_currency_rate():
    """Public: current USD→EUR rate + source/freshness."""
    return get_converter().info


@router.post("/currency/refresh")
async def refresh_currency_rate(request: Request):
    """Force a refresh of the USD→EUR rate (auth required)."""
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    rate = await get_converter().refresh()
    return {"rate": rate, "info": get_converter().info}
