"""
Notifications service.

Persists per-user notifications, exposes helpers to emit them from anywhere
in the codebase (like/comment/follow/star/message/collab).
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


VALID_TYPES = {"like", "comment", "follow", "star", "message", "collab", "outfit"}
DEDUPE_TYPES = {"like", "star", "follow"}


class NotificationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def initialize(self):
        try:
            await self.db.notifications.create_index("notification_id", unique=True)
            await self.db.notifications.create_index([("user_id", 1), ("created_at", -1)])
            await self.db.notifications.create_index([("user_id", 1), ("read", 1)])
            logger.info("Notification indexes created")
        except Exception as e:
            logger.warning(f"Notification index creation: {e}")

    async def emit(
        self,
        user_id: str,
        actor_user_id: Optional[str],
        n_type: str,
        preview: str,
        post_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """Create a notification. Skips self-notifications and unknown types."""
        if n_type not in VALID_TYPES:
            logger.warning(f"Unknown notification type: {n_type}")
            return None
        if actor_user_id and actor_user_id == user_id:
            # Never notify a user about their own action
            return None

        if n_type in DEDUPE_TYPES and await self.db.notifications.find_one({
            "user_id": user_id, "actor_user_id": actor_user_id, "type": n_type,
            "post_id": post_id, "read": False,
        }):
            return None

        # Enrich preview with actor name if possible
        actor_name = None
        if actor_user_id:
            actor = await self.db.users.find_one(
                {"user_id": actor_user_id}, {"_id": 0, "name": 1}
            )
            actor_name = (actor or {}).get("name")

        record = {
            "notification_id": f"ntf_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "actor_user_id": actor_user_id,
            "actor_name": actor_name,
            "type": n_type,
            "preview": preview,
            "post_id": post_id,
            "conversation_id": conversation_id,
            "target_user_id": target_user_id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.notifications.insert_one(record)
        record.pop("_id", None)
        return record

    async def list_for_user(
        self, user_id: str, limit: int = 30, unread_only: bool = False
    ) -> List[Dict]:
        query: Dict = {"user_id": user_id}
        if unread_only:
            query["read"] = False
        return await self.db.notifications.find(
            query, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)

    async def unread_count(self, user_id: str) -> int:
        return await self.db.notifications.count_documents({"user_id": user_id, "read": False})

    async def mark_read(self, user_id: str, notification_ids: Optional[List[str]] = None) -> int:
        query: Dict = {"user_id": user_id, "read": False}
        if notification_ids:
            query["notification_id"] = {"$in": notification_ids}
        result = await self.db.notifications.update_many(query, {"$set": {"read": True}})
        return result.modified_count
