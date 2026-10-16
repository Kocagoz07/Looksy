"""
Smart Affiliate Engine for Looksy
Generates AI-recommended affiliate links for outfit items and post tags,
tracks clicks, and computes potential earnings.
"""

import os
import json
import uuid
import logging
from urllib.parse import quote_plus
from datetime import datetime, timezone
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


# Default retailer fallbacks (used when AI cannot generate suggestions)
DEFAULT_RETAILERS = [
    {"name": "Amazon",     "base_url": "https://www.amazon.com/s?k=",        "commission_rate": 0.04},
    {"name": "ASOS",       "base_url": "https://www.asos.com/search/?q=",    "commission_rate": 0.07},
    {"name": "Zalando",    "base_url": "https://www.zalando.com/catalog/?q=", "commission_rate": 0.08},
    {"name": "Farfetch",   "base_url": "https://www.farfetch.com/shopping/search/items.aspx?q=", "commission_rate": 0.10},
    {"name": "Nordstrom",  "base_url": "https://www.nordstrom.com/sr?keyword=", "commission_rate": 0.05},
]


class AffiliateEngine:
    """AI-powered affiliate link generation and tracking."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.api_key = os.environ.get("EMERGENT_LLM_KEY")

    async def initialize(self):
        try:
            await self.db.affiliate_links.create_index("link_id", unique=True)
            await self.db.affiliate_links.create_index("user_id")
            await self.db.affiliate_links.create_index("post_id")
            await self.db.affiliate_links.create_index("outfit_id")
            await self.db.affiliate_clicks.create_index("link_id")
            await self.db.affiliate_clicks.create_index("clicked_at")
            logger.info("Affiliate engine indexes created")
        except Exception as e:
            logger.warning(f"Affiliate index creation: {e}")

    # ---------- AI suggestion ----------

    async def suggest_for_items(
        self,
        items: List[Dict],
        user_id: Optional[str] = None,
        budget: Optional[str] = None,
    ) -> List[Dict]:
        """For a list of outfit items, ask AI to suggest the best retailers and search keywords."""
        if not items:
            return []

        if not self.api_key:
            return [self._fallback_suggestion(item) for item in items]

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"affiliate_{user_id or 'anon'}_{uuid.uuid4().hex[:6]}",
                system_message=(
                    "You are an expert fashion affiliate matcher. For each clothing item, "
                    "return the 2 best retailers (from common fashion e-commerce sites like "
                    "Amazon, ASOS, Zalando, Farfetch, Nordstrom, Net-a-Porter, Mango, H&M, Zara) "
                    "and a precise search query that will surface a great matching product. "
                    "Respond ONLY in valid JSON with this shape: "
                    '{"suggestions":[{"item":"...","retailers":[{"name":"...","search_query":"..."}]}]}'
                ),
            ).with_model("openai", "gpt-4o-mini")

            item_lines = "\n".join(
                f"- {i.get('category','item')}: {i.get('color','')} {i.get('item','')}".strip()
                for i in items
            )
            prompt = (
                f"Items:\n{item_lines}\n\n"
                f"Budget hint: {budget or 'any'}.\n"
                "For each item, give 2 retailers and a strong search query."
            )

            response = await chat.send_message(UserMessage(text=prompt))
            parsed = self._parse_json(response)
            suggestions = parsed.get("suggestions", []) if isinstance(parsed, dict) else []

            results: List[Dict] = []
            for raw_item, ai_item in zip(items, suggestions):
                retailers_out: List[Dict] = []
                for retailer in (ai_item.get("retailers") or [])[:3]:
                    name = retailer.get("name") or "Amazon"
                    query = retailer.get("search_query") or raw_item.get("item") or "fashion"
                    retailers_out.append(self._build_retailer_link(name, query))
                if not retailers_out:
                    retailers_out = self._fallback_suggestion(raw_item)["retailers"]
                results.append({
                    "item": raw_item.get("item"),
                    "category": raw_item.get("category"),
                    "color": raw_item.get("color"),
                    "retailers": retailers_out,
                })
            # if AI returned fewer items than requested, fill the rest with fallbacks
            for raw_item in items[len(results):]:
                results.append(self._fallback_suggestion(raw_item))
            return results
        except Exception as e:
            logger.error(f"AI affiliate suggestion failed: {e}")
            return [self._fallback_suggestion(item) for item in items]

    def _fallback_suggestion(self, item: Dict) -> Dict:
        query = " ".join(filter(None, [item.get("color"), item.get("item"), item.get("category")]))
        return {
            "item": item.get("item"),
            "category": item.get("category"),
            "color": item.get("color"),
            "retailers": [
                self._build_retailer_link(r["name"], query) for r in DEFAULT_RETAILERS[:2]
            ],
        }

    def _build_retailer_link(self, retailer_name: str, search_query: str) -> Dict:
        retailer = next(
            (r for r in DEFAULT_RETAILERS if r["name"].lower() == (retailer_name or "").lower()),
            DEFAULT_RETAILERS[0],
        )
        url = retailer["base_url"] + quote_plus(search_query)
        return {
            "retailer": retailer["name"],
            "search_query": search_query,
            "url": url,
            "commission_rate": retailer["commission_rate"],
        }

    def _parse_json(self, text: str) -> Dict:
        try:
            text = text.strip()
            if text.startswith("```"):
                # strip fenced block
                stripped = []
                in_block = False
                for line in text.split("\n"):
                    if line.startswith("```"):
                        in_block = not in_block
                        continue
                    if in_block:
                        stripped.append(line)
                text = "\n".join(stripped)
            return json.loads(text)
        except Exception:
            return {}

    # ---------- Persistence: links, clicks ----------

    async def create_links(
        self,
        user_id: str,
        suggestions: List[Dict],
        outfit_id: Optional[str] = None,
        post_id: Optional[str] = None,
    ) -> List[Dict]:
        """Persist suggestions as trackable affiliate links and return them with IDs."""
        now = datetime.now(timezone.utc).isoformat()
        created: List[Dict] = []
        for s in suggestions:
            for retailer in s.get("retailers", []):
                link_id = f"aff_{uuid.uuid4().hex[:12]}"
                record = {
                    "link_id": link_id,
                    "user_id": user_id,
                    "outfit_id": outfit_id,
                    "post_id": post_id,
                    "item": s.get("item"),
                    "category": s.get("category"),
                    "color": s.get("color"),
                    "retailer": retailer["retailer"],
                    "search_query": retailer["search_query"],
                    "target_url": retailer["url"],
                    "commission_rate": retailer["commission_rate"],
                    "clicks": 0,
                    "conversions": 0,
                    "estimated_earnings_eur": 0.0,
                    "created_at": now,
                }
                await self.db.affiliate_links.insert_one(record)
                # strip Mongo _id before returning
                record.pop("_id", None)
                created.append(record)
        return created

    async def track_click(
        self,
        link_id: str,
        clicker_user_id: Optional[str],
        ip_address: Optional[str],
        device_fingerprint: Optional[str],
        fraud_service=None,
    ) -> Dict:
        link = await self.db.affiliate_links.find_one({"link_id": link_id}, {"_id": 0})
        if not link:
            raise ValueError("Affiliate link not found")

        # Fraud check (reuse fraud_service if available)
        is_suspicious = False
        if fraud_service and clicker_user_id:
            try:
                check = await fraud_service.check_like_abuse(
                    user_id=clicker_user_id,
                    target_id=link_id,
                    ip_address=ip_address or "0.0.0.0",
                    device_fingerprint=device_fingerprint,
                )
                is_suspicious = not check.get("allowed", True)
            except Exception as e:
                logger.warning(f"Affiliate fraud check failed: {e}")

        await self.db.affiliate_clicks.insert_one({
            "click_id": f"clk_{uuid.uuid4().hex[:12]}",
            "link_id": link_id,
            "user_id": clicker_user_id,
            "ip_address": ip_address,
            "device_fingerprint": device_fingerprint,
            "suspicious": is_suspicious,
            "clicked_at": datetime.now(timezone.utc).isoformat(),
        })

        if not is_suspicious:
            await self.db.affiliate_links.update_one(
                {"link_id": link_id},
                {"$inc": {"clicks": 1}},
            )

        return {
            "link_id": link_id,
            "target_url": link["target_url"],
            "suspicious": is_suspicious,
        }

    async def get_links_for_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        return await self.db.affiliate_links.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)

    async def get_links_for_outfit(self, outfit_id: str) -> List[Dict]:
        return await self.db.affiliate_links.find(
            {"outfit_id": outfit_id}, {"_id": 0}
        ).to_list(100)

    async def get_links_for_post(self, post_id: str) -> List[Dict]:
        return await self.db.affiliate_links.find(
            {"post_id": post_id}, {"_id": 0}
        ).to_list(100)

    async def get_user_stats(self, user_id: str) -> Dict:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_links": {"$sum": 1},
                "total_clicks": {"$sum": "$clicks"},
                "total_conversions": {"$sum": "$conversions"},
                "total_earnings_eur": {"$sum": "$estimated_earnings_eur"},
            }},
        ]
        agg = await self.db.affiliate_links.aggregate(pipeline).to_list(1)
        if not agg:
            return {
                "total_links": 0, "total_clicks": 0,
                "total_conversions": 0, "total_earnings_eur": 0.0,
            }
        row = agg[0]
        row.pop("_id", None)
        return row
