"""
Real-Time Chat System for Looksy
WebSocket-based messaging with conversations and messages support
"""

import os
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, List, Set
from dataclasses import dataclass, field
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

# ==================== MODELS ====================

@dataclass
class ConnectedUser:
    user_id: str
    websocket: any
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ChatManager:
    """Manages WebSocket connections and real-time messaging"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        # In-memory connection tracking: user_id -> set of websockets
        self.connections: Dict[str, Set] = {}
        # Typing indicators: conversation_id -> {user_id: timestamp}
        self.typing_users: Dict[str, Dict[str, datetime]] = {}
    
    async def initialize(self):
        """Initialize chat collections and indexes"""
        try:
            # Create indexes for conversations
            await self.db.conversations.create_index("conversation_id", unique=True)
            await self.db.conversations.create_index("participants.user_id")
            await self.db.conversations.create_index([("participants.user_id", 1), ("updated_at", -1)])
            
            # Create indexes for messages
            await self.db.chat_messages.create_index("message_id", unique=True)
            await self.db.chat_messages.create_index([("conversation_id", 1), ("created_at", -1)])
            await self.db.chat_messages.create_index("sender_id")
            
            logger.info("Chat indexes created successfully")
        except Exception as e:
            logger.warning(f"Chat index creation: {e}")
    
    # ==================== CONNECTION MANAGEMENT ====================
    
    def register_connection(self, user_id: str, websocket):
        """Register a new WebSocket connection for a user"""
        if user_id not in self.connections:
            self.connections[user_id] = set()
        self.connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected. Total connections: {len(self.connections[user_id])}")
    
    def unregister_connection(self, user_id: str, websocket):
        """Remove a WebSocket connection"""
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)
            if not self.connections[user_id]:
                del self.connections[user_id]
            logger.info(f"User {user_id} disconnected")
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if a user has any active connections"""
        return user_id in self.connections and len(self.connections[user_id]) > 0
    
    def get_online_users(self, user_ids: List[str]) -> Dict[str, bool]:
        """Get online status for multiple users"""
        return {uid: self.is_user_online(uid) for uid in user_ids}
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections of a user"""
        if user_id in self.connections:
            disconnected = set()
            for ws in self.connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected.add(ws)
            
            # Clean up disconnected websockets
            for ws in disconnected:
                self.connections[user_id].discard(ws)
    
    async def broadcast_to_conversation(self, conversation_id: str, message: dict, exclude_user: str = None):
        """Broadcast message to all participants of a conversation"""
        conversation = await self.db.conversations.find_one(
            {"conversation_id": conversation_id},
            {"participants": 1, "_id": 0}
        )
        
        if conversation:
            for participant in conversation.get("participants", []):
                user_id = participant["user_id"]
                if user_id != exclude_user:
                    await self.send_to_user(user_id, message)
    
    # ==================== CONVERSATIONS ====================
    
    async def get_or_create_direct_conversation(self, user1_id: str, user2_id: str) -> dict:
        """Get existing direct conversation or create a new one"""
        
        # Check if conversation exists
        existing = await self.db.conversations.find_one({
            "type": "direct",
            "participants.user_id": {"$all": [user1_id, user2_id]},
            "$expr": {"$eq": [{"$size": "$participants"}, 2]}
        }, {"_id": 0})
        
        if existing:
            return existing
        
        # Create new conversation
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        conversation = {
            "conversation_id": conversation_id,
            "type": "direct",
            "participants": [
                {"user_id": user1_id, "joined_at": now, "last_read_at": now},
                {"user_id": user2_id, "joined_at": now, "last_read_at": None}
            ],
            "created_by": user1_id,
            "created_at": now,
            "updated_at": now,
            "last_message": None,
            "is_archived": False
        }
        
        await self.db.conversations.insert_one(conversation)
        
        # Return without _id
        return {k: v for k, v in conversation.items() if k != "_id"}
    
    async def get_user_conversations(
        self,
        user_id: str,
        limit: int = 20,
        cursor: Optional[str] = None
    ) -> dict:
        """Get user's conversations with pagination"""
        
        query = {"participants.user_id": user_id, "is_archived": {"$ne": True}}
        
        if cursor:
            query["updated_at"] = {"$lt": cursor}
        
        conversations = await self.db.conversations.find(
            query,
            {"_id": 0}
        ).sort("updated_at", -1).limit(limit + 1).to_list(limit + 1)
        
        has_more = len(conversations) > limit
        if has_more:
            conversations = conversations[:limit]
        
        # Enrich with other participant info
        for conv in conversations:
            other_participants = [p for p in conv["participants"] if p["user_id"] != user_id]
            if other_participants and conv["type"] == "direct":
                other_user = await self.db.users.find_one(
                    {"user_id": other_participants[0]["user_id"]},
                    {"_id": 0, "user_id": 1, "name": 1, "picture": 1}
                )
                conv["other_user"] = other_user
            
            # Calculate unread count
            my_participant = next((p for p in conv["participants"] if p["user_id"] == user_id), None)
            if my_participant and my_participant.get("last_read_at"):
                unread_count = await self.db.chat_messages.count_documents({
                    "conversation_id": conv["conversation_id"],
                    "created_at": {"$gt": my_participant["last_read_at"]},
                    "sender_id": {"$ne": user_id}
                })
            else:
                unread_count = await self.db.chat_messages.count_documents({
                    "conversation_id": conv["conversation_id"],
                    "sender_id": {"$ne": user_id}
                })
            conv["unread_count"] = unread_count
        
        next_cursor = conversations[-1]["updated_at"] if conversations else None
        
        return {
            "conversations": conversations,
            "next_cursor": next_cursor if has_more else None,
            "has_more": has_more
        }
    
    async def get_conversation(self, conversation_id: str, user_id: str) -> Optional[dict]:
        """Get a conversation if user is a participant"""
        conversation = await self.db.conversations.find_one({
            "conversation_id": conversation_id,
            "participants.user_id": user_id
        }, {"_id": 0})
        
        if conversation and conversation["type"] == "direct":
            other_participants = [p for p in conversation["participants"] if p["user_id"] != user_id]
            if other_participants:
                other_user = await self.db.users.find_one(
                    {"user_id": other_participants[0]["user_id"]},
                    {"_id": 0, "user_id": 1, "name": 1, "picture": 1}
                )
                conversation["other_user"] = other_user
        
        return conversation
    
    # ==================== MESSAGES ====================
    
    async def send_message(
        self,
        conversation_id: str,
        sender_id: str,
        content: str,
        message_type: str = "text"
    ) -> dict:
        """Send a message to a conversation"""
        
        # Verify sender is participant
        conversation = await self.db.conversations.find_one({
            "conversation_id": conversation_id,
            "participants.user_id": sender_id
        })
        
        if not conversation:
            raise ValueError("Conversation not found or access denied")
        
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Get sender info
        sender = await self.db.users.find_one(
            {"user_id": sender_id},
            {"_id": 0, "name": 1, "picture": 1}
        )
        
        message = {
            "message_id": message_id,
            "conversation_id": conversation_id,
            "sender_id": sender_id,
            "sender_name": sender.get("name", "Unknown") if sender else "Unknown",
            "sender_picture": sender.get("picture") if sender else None,
            "type": message_type,
            "content": content,
            "created_at": now,
            "edited_at": None,
            "is_deleted": False,
            "read_by": [sender_id]
        }
        
        await self.db.chat_messages.insert_one(message)
        
        # Update conversation's last_message
        await self.db.conversations.update_one(
            {"conversation_id": conversation_id},
            {
                "$set": {
                    "last_message": {
                        "message_id": message_id,
                        "content": content[:100] if len(content) > 100 else content,
                        "sender_id": sender_id,
                        "sent_at": now,
                        "type": message_type
                    },
                    "updated_at": now
                }
            }
        )
        
        # Return without _id
        return {k: v for k, v in message.items() if k != "_id"}
    
    async def get_messages(
        self,
        conversation_id: str,
        user_id: str,
        limit: int = 30,
        before: Optional[str] = None
    ) -> dict:
        """Get messages in a conversation with pagination"""
        
        # Verify user is participant
        conversation = await self.db.conversations.find_one({
            "conversation_id": conversation_id,
            "participants.user_id": user_id
        })
        
        if not conversation:
            raise ValueError("Conversation not found or access denied")
        
        query = {"conversation_id": conversation_id, "is_deleted": {"$ne": True}}
        
        if before:
            query["created_at"] = {"$lt": before}
        
        messages = await self.db.chat_messages.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit + 1).to_list(limit + 1)
        
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        # Reverse to show oldest first
        messages.reverse()
        
        return {
            "messages": messages,
            "has_more": has_more,
            "oldest_timestamp": messages[0]["created_at"] if messages else None
        }
    
    async def mark_messages_read(self, conversation_id: str, user_id: str, up_to_message_id: Optional[str] = None):
        """Mark messages as read up to a certain message"""
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Update participant's last_read_at
        await self.db.conversations.update_one(
            {
                "conversation_id": conversation_id,
                "participants.user_id": user_id
            },
            {"$set": {"participants.$.last_read_at": now}}
        )
        
        # Update read_by for messages
        query = {
            "conversation_id": conversation_id,
            "sender_id": {"$ne": user_id},
            "read_by": {"$ne": user_id}
        }
        
        if up_to_message_id:
            target_msg = await self.db.chat_messages.find_one({"message_id": up_to_message_id})
            if target_msg:
                query["created_at"] = {"$lte": target_msg["created_at"]}
        
        await self.db.chat_messages.update_many(
            query,
            {"$addToSet": {"read_by": user_id}}
        )
        
        return {"marked_read": True}
    
    async def delete_message(self, message_id: str, user_id: str) -> bool:
        """Soft delete a message (only sender can delete)"""
        result = await self.db.chat_messages.update_one(
            {"message_id": message_id, "sender_id": user_id},
            {"$set": {"is_deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat()}}
        )
        return result.modified_count > 0
    
    # ==================== TYPING INDICATORS ====================
    
    def set_typing(self, conversation_id: str, user_id: str, is_typing: bool):
        """Update typing status for a user"""
        if conversation_id not in self.typing_users:
            self.typing_users[conversation_id] = {}
        
        if is_typing:
            self.typing_users[conversation_id][user_id] = datetime.now(timezone.utc)
        else:
            self.typing_users[conversation_id].pop(user_id, None)
    
    def get_typing_users(self, conversation_id: str, exclude_user: str = None) -> List[str]:
        """Get list of users currently typing in a conversation"""
        if conversation_id not in self.typing_users:
            return []
        
        now = datetime.now(timezone.utc)
        typing = []
        expired = []
        
        for user_id, timestamp in self.typing_users[conversation_id].items():
            # Typing indicator expires after 5 seconds
            if (now - timestamp).total_seconds() < 5:
                if user_id != exclude_user:
                    typing.append(user_id)
            else:
                expired.append(user_id)
        
        # Clean up expired
        for user_id in expired:
            self.typing_users[conversation_id].pop(user_id, None)
        
        return typing
    
    # ==================== UNREAD COUNT ====================
    
    async def get_total_unread_count(self, user_id: str) -> int:
        """Get total unread message count across all conversations"""
        # Get all user's conversations
        conversations = await self.db.conversations.find(
            {"participants.user_id": user_id},
            {"conversation_id": 1, "participants": 1, "_id": 0}
        ).to_list(100)
        
        total_unread = 0
        
        for conv in conversations:
            my_participant = next((p for p in conv["participants"] if p["user_id"] == user_id), None)
            if my_participant and my_participant.get("last_read_at"):
                count = await self.db.chat_messages.count_documents({
                    "conversation_id": conv["conversation_id"],
                    "created_at": {"$gt": my_participant["last_read_at"]},
                    "sender_id": {"$ne": user_id}
                })
            else:
                count = await self.db.chat_messages.count_documents({
                    "conversation_id": conv["conversation_id"],
                    "sender_id": {"$ne": user_id}
                })
            total_unread += count
        
        return total_unread
