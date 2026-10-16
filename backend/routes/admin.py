"""App-owner admin panel: click revenue, suspicious clicks, CPC setting, payout review."""

import os
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

import deps
from click_revenue import MAX_CPC_EUR, sovrn_key

router = APIRouter()


def admin_emails() -> set:
    return {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}


async def require_admin(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user.email.lower() not in admin_emails():
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class CpcSettings(BaseModel):
    cpc_eur: float = Field(ge=0, le=MAX_CPC_EUR)


@router.get("/admin/me")
async def admin_me(request: Request):
    user = await deps.get_current_user(request)
    return {"is_admin": bool(user and user.email.lower() in admin_emails())}


@router.get("/admin/settings")
async def get_settings(request: Request):
    await require_admin(request)
    return {"cpc_eur": await deps.click_revenue.get_cpc(), "sovrn_configured": bool(sovrn_key()),
            "revenue_share": {"platform": 1.0, "creator": 0.0}}


@router.put("/admin/settings")
async def update_settings(payload: CpcSettings, request: Request):
    admin = await require_admin(request)
    return {"cpc_eur": await deps.click_revenue.set_cpc(payload.cpc_eur, admin.user_id)}


def _sum_group(match: dict, group_id):
    return [
        {"$match": match},
        {"$group": {
            "_id": group_id,
            "clicks": {"$sum": 1},
            "billable": {"$sum": {"$cond": ["$billable", 1, 0]}},
            "suspicious": {"$sum": {"$cond": ["$suspicious", 1, 0]}},
            "revenue_eur": {"$sum": "$revenue_eur"},
        }},
    ]


@router.get("/admin/revenue/summary")
async def revenue_summary(request: Request, days: int = Query(30, ge=1, le=365)):
    await require_admin(request)
    db = deps.db
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    async def window(since):
        rows = await db.link_clicks.aggregate(_sum_group({"clicked_at": {"$gte": since}} if since else {}, None)).to_list(1)
        r = rows[0] if rows else {}
        return {k: round(r.get(k, 0), 4) if k == "revenue_eur" else r.get(k, 0) for k in ("clicks", "billable", "suspicious", "revenue_eur")}

    since = today - timedelta(days=days - 1)
    daily_rows = await db.link_clicks.aggregate(
        _sum_group({"clicked_at": {"$gte": since}}, {"$dateToString": {"format": "%Y-%m-%d", "date": "$clicked_at"}})
    ).to_list(400)
    by_day = {r["_id"]: r for r in daily_rows}
    daily = []
    for i in range(days):
        d = (since + timedelta(days=i)).strftime("%Y-%m-%d")
        r = by_day.get(d, {})
        daily.append({"date": d, "clicks": r.get("clicks", 0), "billable": r.get("billable", 0),
                      "revenue_eur": round(r.get("revenue_eur", 0.0), 4)})

    by_source = await db.link_clicks.aggregate(_sum_group({"clicked_at": {"$gte": since}}, "$source")).to_list(20)
    top_owners = await db.link_clicks.aggregate(
        _sum_group({"clicked_at": {"$gte": since}, "billable": True}, "$owner_id") + [{"$sort": {"revenue_eur": -1}}, {"$limit": 5}]
    ).to_list(5)
    names = {u["user_id"]: u.get("name") for u in await db.users.find(
        {"user_id": {"$in": [o["_id"] for o in top_owners if o["_id"]]}}, {"_id": 0, "user_id": 1, "name": 1}
    ).to_list(5)}

    return {
        "cpc_eur": await deps.click_revenue.get_cpc(),
        "sovrn_configured": bool(sovrn_key()),
        "today": await window(today),
        "last_7_days": await window(today - timedelta(days=6)),
        "last_30_days": await window(today - timedelta(days=29)),
        "all_time": await window(None),
        "daily": daily,
        "by_source": [{"source": s["_id"], "clicks": s["clicks"], "billable": s["billable"],
                       "revenue_eur": round(s["revenue_eur"], 4)} for s in by_source],
        "top_creators": [{"user_id": o["_id"], "name": names.get(o["_id"]), "billable": o["billable"],
                          "revenue_eur": round(o["revenue_eur"], 4)} for o in top_owners],
        "pending_payouts": await db.payouts.count_documents({"status": "pending"}),
    }


@router.get("/admin/clicks")
async def list_clicks(request: Request, filter: Literal["suspicious", "rejected", "all"] = "suspicious",
                      limit: int = Query(50, ge=1, le=200)):
    await require_admin(request)
    query = {"suspicious": True} if filter == "suspicious" else {"billable": False} if filter == "rejected" else {}
    clicks = await deps.db.link_clicks.find(query, {"_id": 0, "user_agent": 0}).sort("clicked_at", -1).limit(limit).to_list(limit)
    for c in clicks:
        c["clicked_at"] = c["clicked_at"].replace(tzinfo=timezone.utc).isoformat() if c["clicked_at"].tzinfo is None else c["clicked_at"].isoformat()
    return {"clicks": clicks}


@router.get("/admin/pending-payouts")
async def pending_payouts(request: Request):
    await require_admin(request)
    payouts = await deps.db.payouts.find({"status": "pending"}, {"_id": 0}).sort("created_at", 1).to_list(100)
    users = {u["user_id"]: u for u in await deps.db.users.find(
        {"user_id": {"$in": [p["user_id"] for p in payouts]}}, {"_id": 0, "user_id": 1, "name": 1, "email": 1}
    ).to_list(100)}
    for p in payouts:
        p["user_name"] = users.get(p["user_id"], {}).get("name")
        p["user_email"] = users.get(p["user_id"], {}).get("email")
    return {"pending_payouts": payouts, "count": len(payouts)}


ACTIONS = {
    "approve": ({"pending"}, "processing"),
    "complete": ({"pending", "processing"}, "completed"),
    "reject": ({"pending"}, "rejected"),
}


@router.post("/admin/process-payout/{payout_id}")
async def process_payout(payout_id: str, request: Request, action: str = "approve", notes: Optional[str] = None):
    admin = await require_admin(request)
    if action not in ACTIONS:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve', 'complete', or 'reject'")
    allowed, new_status = ACTIONS[action]
    now = datetime.now(timezone.utc).isoformat()
    update = {"status": new_status, "updated_at": now, "notes": notes, "processed_by": admin.user_id}
    if new_status == "completed":
        update["completed_at"] = now
    payout = await deps.db.payouts.find_one_and_update(
        {"payout_id": payout_id, "status": {"$in": list(allowed)}}, {"$set": update}
    )
    if not payout:
        existing = await deps.db.payouts.find_one({"payout_id": payout_id}, {"_id": 0, "status": 1})
        if not existing:
            raise HTTPException(status_code=404, detail="Payout not found")
        raise HTTPException(status_code=400, detail=f"Payout already {existing['status']}")
    if action == "reject":
        await deps.db.users.update_one({"user_id": payout["user_id"]}, {"$inc": {"payout_points": payout["amount_eur"]}})
        await deps.db.payouts.update_one({"payout_id": payout_id}, {"$set": {"refunded": True}})
        return {"message": "Payout rejected and amount refunded", "payout_id": payout_id}
    return {"message": f"Payout {new_status}", "payout_id": payout_id}
