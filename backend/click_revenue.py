"""Platform click revenue: CPC ledger for every outbound product/affiliate click (100% to the app owner)."""

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import quote

from fastapi import Request

from security import get_client_ip

BOT_UA = re.compile(r"bot|crawl|spider|slurp|facebookexternalhit|embedly|preview|curl|wget|python-requests|httpx|headless|phantom", re.I)
DEDUPE_WINDOW = timedelta(hours=24)
IP_WINDOW = timedelta(hours=1)
IP_LIMIT = 30
SETTINGS_ID = "revenue"
MAX_CPC_EUR = 5.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sovrn_key() -> Optional[str]:
    return (os.environ.get("SOVRN_API_KEY") or "").strip() or None


def monetize_url(url: str, click_id: str) -> str:
    key = sovrn_key()
    if not key:
        return url
    return f"https://redirect.viglink.com?key={quote(key)}&u={quote(url, safe='')}&cuid={click_id}"


class ClickRevenue:
    def __init__(self, db):
        self.db = db

    async def ensure_indexes(self):
        await self.db.link_clicks.create_index([("link_ref", 1), ("visitor_key", 1), ("clicked_at", -1)])
        await self.db.link_clicks.create_index([("ip_address", 1), ("clicked_at", -1)])
        await self.db.link_clicks.create_index([("clicked_at", -1)])
        await self.db.link_clicks.create_index([("post_id", 1)])

    async def get_cpc(self) -> float:
        doc = await self.db.platform_settings.find_one({"_id": SETTINGS_ID})
        if doc and doc.get("cpc_eur") is not None:
            return float(doc["cpc_eur"])
        return float(os.environ["PLATFORM_CPC_EUR"])

    async def set_cpc(self, cpc_eur: float, admin_id: str) -> float:
        await self.db.platform_settings.update_one(
            {"_id": SETTINGS_ID},
            {"$set": {"cpc_eur": round(cpc_eur, 4), "updated_by": admin_id, "updated_at": _now().isoformat()}},
            upsert=True,
        )
        return await self.get_cpc()

    async def record(self, *, request: Request, user, source: str, link_ref: str,
                     owner_id: Optional[str], target_url: str, extra: Optional[dict] = None) -> dict:
        ip = get_client_ip(request)
        ua = request.headers.get("User-Agent", "")[:300]
        visitor_key = user.user_id if user else hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:20]
        now = _now()

        reasons = []
        if not ua or BOT_UA.search(ua):
            reasons.append("bot")
        if user and owner_id and user.user_id == owner_id:
            reasons.append("self_click")
        if await self.db.link_clicks.find_one({
            "link_ref": link_ref, "visitor_key": visitor_key, "billable": True,
            "clicked_at": {"$gte": now - DEDUPE_WINDOW},
        }, {"_id": 1}):
            reasons.append("duplicate")
        if ip and await self.db.link_clicks.count_documents(
            {"ip_address": ip, "clicked_at": {"$gte": now - IP_WINDOW}}
        ) >= IP_LIMIT:
            reasons.append("ip_rate_limit")

        billable = not reasons
        cpc = await self.get_cpc()
        click_id = f"lc_{uuid.uuid4().hex[:14]}"
        redirect_url = monetize_url(target_url, click_id)
        doc = {
            "click_id": click_id,
            "source": source,
            "link_ref": link_ref,
            "owner_id": owner_id,
            "user_id": user.user_id if user else None,
            "visitor_key": visitor_key,
            "ip_address": ip,
            "user_agent": ua,
            "target_url": target_url,
            "network": "sovrn" if redirect_url != target_url else "direct",
            "billable": billable,
            "suspicious": any(r in ("bot", "ip_rate_limit") for r in reasons),
            "reasons": reasons,
            "cpc_eur": cpc,
            "revenue_eur": cpc if billable else 0.0,
            "clicked_at": now,
            **(extra or {}),
        }
        await self.db.link_clicks.insert_one(doc)
        return {"click_id": click_id, "billable": billable, "reasons": reasons, "redirect_url": redirect_url}
