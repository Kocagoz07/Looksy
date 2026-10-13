"""Notification routes."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import deps

router = APIRouter()


class MarkReadRequest(BaseModel):
    notification_ids: Optional[List[str]] = None  # None = mark ALL as read


@router.get("/notifications")
async def list_notifications(request: Request, limit: int = 30, unread_only: bool = False):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    items = await deps.notification_service.list_for_user(
        user.user_id, limit=limit, unread_only=unread_only
    )
    unread = await deps.notification_service.unread_count(user.user_id)
    return {"notifications": items, "unread_count": unread, "count": len(items)}


@router.get("/notifications/unread-count")
async def notifications_unread_count(request: Request):
    """Cheap poll endpoint used by the bell badge."""
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"unread_count": await deps.notification_service.unread_count(user.user_id)}


@router.post("/notifications/mark-read")
async def mark_notifications_read(payload: MarkReadRequest, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    updated = await deps.notification_service.mark_read(
        user.user_id, notification_ids=payload.notification_ids
    )
    unread = await deps.notification_service.unread_count(user.user_id)
    return {"marked_read": updated, "unread_count": unread}
