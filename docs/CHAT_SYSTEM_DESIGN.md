# Looksy Real-Time Chat System - Technical Design Document

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Web App   │  │  iOS App    │  │ Android App │  │  Desktop    │        │
│  │   (React)   │  │  (Swift)    │  │  (Kotlin)   │  │  (Electron) │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                │                │                │                │
│         └────────────────┴────────────────┴────────────────┘                │
│                                   │                                          │
│                    ┌──────────────┴──────────────┐                          │
│                    │      WebSocket Client       │                          │
│                    │   (Socket.IO / Native WS)   │                          │
│                    └──────────────┬──────────────┘                          │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│      LOAD BALANCER          │   │      API GATEWAY            │
│   (Nginx / AWS ALB)         │   │   (Kong / AWS API GW)       │
│   - SSL Termination         │   │   - Rate Limiting           │
│   - Sticky Sessions (WS)    │   │   - Authentication          │
│   - Health Checks           │   │   - Request Routing         │
└──────────────┬──────────────┘   └──────────────┬──────────────┘
               │                                  │
               ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
│                                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │  WebSocket Server   │  │    REST API Server  │  │  Background Workers │ │
│  │  (Socket.IO/FastAPI)│  │      (FastAPI)      │  │     (Celery)        │ │
│  │                     │  │                     │  │                     │ │
│  │  - Connection Mgmt  │  │  - CRUD Operations  │  │  - Push Notifs      │ │
│  │  - Real-time Events │  │  - File Uploads     │  │  - Media Processing │ │
│  │  - Presence System  │  │  - Search           │  │  - Cleanup Jobs     │ │
│  │  - Typing Indicators│  │  - Pagination       │  │  - Analytics        │ │
│  └──────────┬──────────┘  └──────────┬──────────┘  └──────────┬──────────┘ │
│             │                        │                        │             │
└─────────────┼────────────────────────┼────────────────────────┼─────────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
┌─────────────────────────────┐   ┌─────────────────────────────┐
│      MESSAGE BROKER         │   │      CACHING LAYER          │
│      (Redis Pub/Sub)        │   │      (Redis Cluster)        │
│                             │   │                             │
│  - Cross-server messaging   │   │  - Session storage          │
│  - Event broadcasting       │   │  - Online status cache      │
│  - Queue management         │   │  - Recent messages cache    │
└──────────────┬──────────────┘   └──────────────┬──────────────┘
               │                                  │
               └──────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│                                                                              │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │     MongoDB         │  │    PostgreSQL       │  │    S3 / GridFS      │ │
│  │  (Messages Store)   │  │  (User Relations)   │  │   (Media Storage)   │ │
│  │                     │  │                     │  │                     │ │
│  │  - Messages         │  │  - Users            │  │  - Images           │ │
│  │  - Conversations    │  │  - Blocked Users    │  │  - Videos           │ │
│  │  - Read Receipts    │  │  - Message Requests │  │  - Voice Messages   │ │
│  │  - Reactions        │  │  - Settings         │  │  - Attachments      │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema Design

### 2.1 MongoDB Collections (Messages & Conversations)

```javascript
// conversations collection
{
  "_id": ObjectId,
  "conversation_id": "conv_abc123",
  "type": "direct" | "group",
  "participants": [
    {
      "user_id": "user_123",
      "joined_at": ISODate,
      "role": "member" | "admin",
      "nickname": null,
      "muted_until": null,
      "last_read_message_id": "msg_xyz789",
      "last_read_at": ISODate
    }
  ],
  "created_by": "user_123",
  "created_at": ISODate,
  "updated_at": ISODate,
  "last_message": {
    "message_id": "msg_xyz789",
    "text": "Hey, nice outfit!",
    "sender_id": "user_456",
    "sent_at": ISODate,
    "type": "text"
  },
  "metadata": {
    "group_name": null,        // For group chats
    "group_avatar": null,
    "theme": "default",
    "emoji": "👋"
  },
  "is_archived": false,
  "is_deleted": false
}

// messages collection (partitioned by date for scalability)
{
  "_id": ObjectId,
  "message_id": "msg_xyz789",
  "conversation_id": "conv_abc123",
  "sender_id": "user_456",
  "type": "text" | "image" | "video" | "voice" | "sticker" | "post_share" | "story_reply" | "system",
  "content": {
    "text": "Hey, nice outfit!",
    "media_url": null,
    "media_type": null,
    "thumbnail_url": null,
    "duration": null,          // For voice/video
    "dimensions": null,        // {width, height}
    "shared_post_id": null,    // For post shares
    "shared_story_id": null,   // For story replies
    "sticker_id": null
  },
  "reply_to": {
    "message_id": "msg_abc456",
    "sender_id": "user_123",
    "preview_text": "Original message..."
  },
  "reactions": [
    {
      "user_id": "user_123",
      "emoji": "❤️",
      "reacted_at": ISODate
    }
  ],
  "read_by": [
    {
      "user_id": "user_123",
      "read_at": ISODate
    }
  ],
  "delivered_to": [
    {
      "user_id": "user_123",
      "delivered_at": ISODate
    }
  ],
  "edited_at": null,
  "is_deleted": false,
  "deleted_for": [],           // User IDs who deleted this message locally
  "expires_at": null,          // For disappearing messages
  "created_at": ISODate,
  "client_message_id": "client_temp_123"  // For deduplication
}

// message_requests collection (for non-followers)
{
  "_id": ObjectId,
  "request_id": "req_abc123",
  "from_user_id": "user_456",
  "to_user_id": "user_123",
  "conversation_id": "conv_abc123",
  "status": "pending" | "accepted" | "declined" | "blocked",
  "preview_message": "Hi! I love your style...",
  "created_at": ISODate,
  "responded_at": null
}

// typing_indicators collection (TTL indexed - auto-expire)
{
  "_id": ObjectId,
  "conversation_id": "conv_abc123",
  "user_id": "user_456",
  "started_at": ISODate,
  "expires_at": ISODate  // TTL index, auto-delete after 5 seconds
}
```

### 2.2 MongoDB Indexes

```javascript
// conversations collection indexes
db.conversations.createIndex({ "conversation_id": 1 }, { unique: true })
db.conversations.createIndex({ "participants.user_id": 1 })
db.conversations.createIndex({ "participants.user_id": 1, "updated_at": -1 })
db.conversations.createIndex({ "last_message.sent_at": -1 })

// messages collection indexes
db.messages.createIndex({ "message_id": 1 }, { unique: true })
db.messages.createIndex({ "conversation_id": 1, "created_at": -1 })
db.messages.createIndex({ "conversation_id": 1, "message_id": 1 })
db.messages.createIndex({ "sender_id": 1, "created_at": -1 })
db.messages.createIndex({ "client_message_id": 1, "sender_id": 1 })  // Deduplication
db.messages.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })  // TTL for disappearing

// message_requests collection indexes
db.message_requests.createIndex({ "to_user_id": 1, "status": 1 })
db.message_requests.createIndex({ "from_user_id": 1 })

// typing_indicators TTL index
db.typing_indicators.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })
```

---

## 3. REST API Design

### 3.1 Conversations API

```yaml
# Get user's conversations (inbox)
GET /api/messages/conversations
Query Parameters:
  - limit: int (default: 20, max: 50)
  - cursor: string (pagination cursor)
  - filter: "all" | "unread" | "requests"
Response:
  {
    "conversations": [...],
    "next_cursor": "...",
    "unread_count": 5,
    "request_count": 2
  }

# Get or create direct conversation
POST /api/messages/conversations/direct
Body: { "user_id": "user_456" }
Response: { "conversation": {...}, "created": true }

# Create group conversation
POST /api/messages/conversations/group
Body: {
  "participant_ids": ["user_456", "user_789"],
  "group_name": "Fashion Squad",
  "group_avatar": "..."
}

# Get conversation details
GET /api/messages/conversations/{conversation_id}

# Update conversation settings
PATCH /api/messages/conversations/{conversation_id}
Body: {
  "muted_until": "2024-12-31T00:00:00Z",
  "nickname": "Bestie",
  "theme": "love"
}

# Archive/Unarchive conversation
POST /api/messages/conversations/{conversation_id}/archive
POST /api/messages/conversations/{conversation_id}/unarchive

# Delete conversation (for current user only)
DELETE /api/messages/conversations/{conversation_id}

# Leave group conversation
POST /api/messages/conversations/{conversation_id}/leave

# Add participants to group
POST /api/messages/conversations/{conversation_id}/participants
Body: { "user_ids": ["user_999"] }

# Remove participant from group (admin only)
DELETE /api/messages/conversations/{conversation_id}/participants/{user_id}
```

### 3.2 Messages API

```yaml
# Get messages in conversation
GET /api/messages/conversations/{conversation_id}/messages
Query Parameters:
  - limit: int (default: 30, max: 100)
  - before: string (message_id for pagination)
  - after: string (message_id for new messages)
Response:
  {
    "messages": [...],
    "has_more": true,
    "oldest_message_id": "msg_abc"
  }

# Send message
POST /api/messages/conversations/{conversation_id}/messages
Body: {
  "type": "text",
  "content": {
    "text": "Hey! Love your style 🔥"
  },
  "reply_to_message_id": null,
  "client_message_id": "client_temp_123"
}

# Send media message (multipart)
POST /api/messages/conversations/{conversation_id}/messages/media
Form Data:
  - type: "image" | "video" | "voice"
  - file: binary
  - caption: string (optional)
  - client_message_id: string

# Share post to conversation
POST /api/messages/conversations/{conversation_id}/messages/share-post
Body: {
  "post_id": "post_abc123",
  "message": "Check this out!"
}

# Edit message (within 15 minutes)
PATCH /api/messages/{message_id}
Body: { "text": "Updated message" }

# Delete message
DELETE /api/messages/{message_id}
Query: ?for_everyone=true  (sender only, within 1 hour)

# React to message
POST /api/messages/{message_id}/reactions
Body: { "emoji": "❤️" }

# Remove reaction
DELETE /api/messages/{message_id}/reactions

# Mark messages as read
POST /api/messages/conversations/{conversation_id}/read
Body: { "up_to_message_id": "msg_xyz789" }
```

### 3.3 Message Requests API

```yaml
# Get message requests
GET /api/messages/requests
Query: ?status=pending

# Accept message request
POST /api/messages/requests/{request_id}/accept

# Decline message request
POST /api/messages/requests/{request_id}/decline

# Block user from request
POST /api/messages/requests/{request_id}/block
```

### 3.4 Presence & Typing API

```yaml
# Get online status of users
POST /api/messages/presence
Body: { "user_ids": ["user_456", "user_789"] }
Response: {
  "user_456": { "online": true, "last_active": null },
  "user_789": { "online": false, "last_active": "2024-01-15T10:30:00Z" }
}

# Send typing indicator (also via WebSocket)
POST /api/messages/conversations/{conversation_id}/typing
Body: { "is_typing": true }
```

---

## 4. WebSocket Architecture

### 4.1 Connection Flow

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│    Client    │                    │   WS Server  │                    │    Redis     │
└──────┬───────┘                    └──────┬───────┘                    └──────┬───────┘
       │                                   │                                   │
       │  1. Connect with JWT              │                                   │
       │ ─────────────────────────────────>│                                   │
       │                                   │                                   │
       │                                   │  2. Validate JWT                  │
       │                                   │──────────────────────────────────>│
       │                                   │                                   │
       │                                   │  3. Store connection mapping      │
       │                                   │  user_id -> server_id, socket_id  │
       │                                   │──────────────────────────────────>│
       │                                   │                                   │
       │  4. Connection ACK                │                                   │
       │ <─────────────────────────────────│                                   │
       │                                   │                                   │
       │  5. Subscribe to user channels    │                                   │
       │                                   │  6. SUBSCRIBE user:{user_id}      │
       │                                   │──────────────────────────────────>│
       │                                   │                                   │
```

### 4.2 WebSocket Events

```typescript
// CLIENT -> SERVER Events
interface ClientEvents {
  // Authentication
  "auth": { token: string };
  
  // Messaging
  "message:send": {
    conversation_id: string;
    type: "text" | "image" | "video" | "voice";
    content: MessageContent;
    client_message_id: string;
    reply_to_message_id?: string;
  };
  
  // Typing
  "typing:start": { conversation_id: string };
  "typing:stop": { conversation_id: string };
  
  // Read receipts
  "message:read": {
    conversation_id: string;
    message_id: string;
  };
  
  // Presence
  "presence:subscribe": { user_ids: string[] };
  "presence:unsubscribe": { user_ids: string[] };
  
  // Reactions
  "message:react": {
    message_id: string;
    emoji: string;
  };
  
  // Connection
  "ping": {};
}

// SERVER -> CLIENT Events
interface ServerEvents {
  // Connection
  "connected": { user_id: string; session_id: string };
  "pong": {};
  "error": { code: string; message: string };
  
  // Messages
  "message:new": {
    conversation_id: string;
    message: Message;
  };
  "message:updated": {
    conversation_id: string;
    message_id: string;
    updates: Partial<Message>;
  };
  "message:deleted": {
    conversation_id: string;
    message_id: string;
    deleted_for_everyone: boolean;
  };
  "message:sent": {
    client_message_id: string;
    message_id: string;
    sent_at: string;
  };
  
  // Typing
  "typing:update": {
    conversation_id: string;
    user_id: string;
    is_typing: boolean;
  };
  
  // Read receipts
  "message:read_receipt": {
    conversation_id: string;
    message_id: string;
    user_id: string;
    read_at: string;
  };
  
  // Delivery receipts
  "message:delivered": {
    conversation_id: string;
    message_id: string;
    user_id: string;
    delivered_at: string;
  };
  
  // Presence
  "presence:update": {
    user_id: string;
    online: boolean;
    last_active?: string;
  };
  
  // Reactions
  "message:reaction": {
    conversation_id: string;
    message_id: string;
    user_id: string;
    emoji: string | null;  // null = removed
  };
  
  // Conversation updates
  "conversation:updated": {
    conversation_id: string;
    updates: Partial<Conversation>;
  };
}
```

### 4.3 Multi-Server Message Routing

```python
# Redis Pub/Sub for cross-server communication

# When user sends a message:
async def handle_send_message(sender_id: str, conversation_id: str, message: dict):
    # 1. Save message to database
    saved_message = await db.messages.insert_one(message)
    
    # 2. Get all participants
    conversation = await db.conversations.find_one({"conversation_id": conversation_id})
    participant_ids = [p["user_id"] for p in conversation["participants"]]
    
    # 3. Publish to Redis for each participant
    for user_id in participant_ids:
        await redis.publish(
            f"user:{user_id}",
            json.dumps({
                "event": "message:new",
                "data": {
                    "conversation_id": conversation_id,
                    "message": serialize_message(saved_message)
                }
            })
        )
    
    # 4. Update conversation's last_message
    await db.conversations.update_one(
        {"conversation_id": conversation_id},
        {"$set": {
            "last_message": {
                "message_id": message["message_id"],
                "text": message["content"].get("text", ""),
                "sender_id": sender_id,
                "sent_at": message["created_at"],
                "type": message["type"]
            },
            "updated_at": datetime.utcnow()
        }}
    )

# WebSocket server subscribes to user channels:
async def handle_user_connection(websocket, user_id: str):
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"user:{user_id}")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            await websocket.send_json(data)
```

---

## 5. Scalability Design

### 5.1 Horizontal Scaling Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    SCALING ARCHITECTURE                          │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   LOAD BALANCER                          │   │
│  │              (Sticky Sessions for WS)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│         ┌──────────────────┼──────────────────┐                │
│         ▼                  ▼                  ▼                │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐         │
│  │  WS Node 1  │   │  WS Node 2  │   │  WS Node 3  │         │
│  │  (1000 conn)│   │  (1000 conn)│   │  (1000 conn)│         │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘         │
│         │                 │                 │                  │
│         └─────────────────┼─────────────────┘                  │
│                           │                                    │
│                           ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              REDIS CLUSTER (Pub/Sub)                     │   │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐                │   │
│  │   │ Master  │  │ Replica │  │ Replica │                │   │
│  │   └─────────┘  └─────────┘  └─────────┘                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              MONGODB SHARDED CLUSTER                     │   │
│  │                                                          │   │
│  │   Shard Key: { conversation_id: "hashed" }              │   │
│  │                                                          │   │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐               │   │
│  │   │ Shard 1 │  │ Shard 2 │  │ Shard 3 │               │   │
│  │   └─────────┘  └─────────┘  └─────────┘               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Connection Management

```python
# Connection limits per server
MAX_CONNECTIONS_PER_SERVER = 10000
HEARTBEAT_INTERVAL = 30  # seconds
CONNECTION_TIMEOUT = 60  # seconds

# Redis connection registry
class ConnectionRegistry:
    """Track user connections across servers"""
    
    async def register_connection(self, user_id: str, server_id: str, socket_id: str):
        # Store with TTL for automatic cleanup
        await redis.hset(
            f"connections:{user_id}",
            socket_id,
            json.dumps({"server_id": server_id, "connected_at": time.time()})
        )
        await redis.expire(f"connections:{user_id}", 3600)
        
        # Track server load
        await redis.hincrby("server_connections", server_id, 1)
    
    async def unregister_connection(self, user_id: str, socket_id: str):
        connection = await redis.hget(f"connections:{user_id}", socket_id)
        if connection:
            data = json.loads(connection)
            await redis.hdel(f"connections:{user_id}", socket_id)
            await redis.hincrby("server_connections", data["server_id"], -1)
    
    async def get_user_connections(self, user_id: str) -> List[dict]:
        connections = await redis.hgetall(f"connections:{user_id}")
        return [json.loads(v) for v in connections.values()]
    
    async def is_user_online(self, user_id: str) -> bool:
        return await redis.exists(f"connections:{user_id}")
```

### 5.3 Message Partitioning Strategy

```python
# Time-based partitioning for messages
# Collection naming: messages_YYYY_MM

def get_messages_collection(date: datetime) -> str:
    return f"messages_{date.strftime('%Y_%m')}"

async def save_message(message: dict):
    collection_name = get_messages_collection(message["created_at"])
    collection = db[collection_name]
    await collection.insert_one(message)

async def get_messages(conversation_id: str, before: datetime, limit: int):
    # Query current and previous month partitions
    current_month = get_messages_collection(before)
    previous_month = get_messages_collection(before - timedelta(days=30))
    
    messages = []
    for collection_name in [current_month, previous_month]:
        if collection_name in await db.list_collection_names():
            batch = await db[collection_name].find({
                "conversation_id": conversation_id,
                "created_at": {"$lt": before}
            }).sort("created_at", -1).limit(limit - len(messages)).to_list(limit)
            messages.extend(batch)
            if len(messages) >= limit:
                break
    
    return messages[:limit]
```

---

## 6. Security Implementation

### 6.1 Authentication & Authorization

```python
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from jose import jwt, JWTError
import hashlib

class ChatSecurityManager:
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    async def authenticate_websocket(self, websocket: WebSocket) -> str:
        """Authenticate WebSocket connection"""
        # Get token from query params or first message
        token = websocket.query_params.get("token")
        
        if not token:
            # Wait for auth message
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=10.0
                )
                if data.get("event") != "auth":
                    raise WebSocketDisconnect(code=4001, reason="Authentication required")
                token = data.get("token")
            except asyncio.TimeoutError:
                raise WebSocketDisconnect(code=4001, reason="Authentication timeout")
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload["user_id"]
        except JWTError:
            raise WebSocketDisconnect(code=4002, reason="Invalid token")
    
    async def authorize_conversation_access(
        self, 
        user_id: str, 
        conversation_id: str
    ) -> bool:
        """Check if user can access conversation"""
        conversation = await db.conversations.find_one({
            "conversation_id": conversation_id,
            "participants.user_id": user_id,
            "is_deleted": {"$ne": True}
        })
        return conversation is not None
    
    async def check_message_request_required(
        self,
        sender_id: str,
        recipient_id: str
    ) -> bool:
        """Check if message request is needed (non-followers)"""
        # Check if they follow each other
        sender = await db.users.find_one({"user_id": sender_id})
        recipient = await db.users.find_one({"user_id": recipient_id})
        
        sender_follows_recipient = recipient_id in (sender.get("following") or [])
        recipient_follows_sender = sender_id in (recipient.get("following") or [])
        
        # No request needed if mutual follow or recipient follows sender
        return not (sender_follows_recipient or recipient_follows_sender)
    
    async def is_user_blocked(
        self,
        user_id: str,
        target_user_id: str
    ) -> bool:
        """Check if either user has blocked the other"""
        block = await db.blocked_users.find_one({
            "$or": [
                {"blocker_id": user_id, "blocked_id": target_user_id},
                {"blocker_id": target_user_id, "blocked_id": user_id}
            ]
        })
        return block is not None
```

### 6.2 Message Encryption

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

class MessageEncryption:
    """End-to-end encryption for sensitive messages"""
    
    def __init__(self, master_key: str):
        self.master_key = master_key.encode()
    
    def derive_conversation_key(self, conversation_id: str) -> bytes:
        """Derive unique key for each conversation"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=conversation_id.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return key
    
    def encrypt_message(self, conversation_id: str, plaintext: str) -> str:
        """Encrypt message content"""
        key = self.derive_conversation_key(conversation_id)
        f = Fernet(key)
        encrypted = f.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_message(self, conversation_id: str, ciphertext: str) -> str:
        """Decrypt message content"""
        key = self.derive_conversation_key(conversation_id)
        f = Fernet(key)
        encrypted = base64.urlsafe_b64decode(ciphertext.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()
```

### 6.3 Rate Limiting

```python
from datetime import datetime, timedelta
from collections import defaultdict

class ChatRateLimiter:
    """Rate limiting for chat operations"""
    
    LIMITS = {
        "message_send": {"max": 60, "window": 60},      # 60 messages/minute
        "typing_indicator": {"max": 10, "window": 10},  # 10 typing events/10s
        "conversation_create": {"max": 10, "window": 3600},  # 10 new convos/hour
        "media_upload": {"max": 20, "window": 3600},    # 20 uploads/hour
    }
    
    async def check_rate_limit(
        self, 
        user_id: str, 
        action: str
    ) -> tuple[bool, int]:
        """Check if action is allowed, return (allowed, retry_after_seconds)"""
        limit = self.LIMITS.get(action)
        if not limit:
            return True, 0
        
        key = f"ratelimit:{action}:{user_id}"
        current_time = int(datetime.utcnow().timestamp())
        window_start = current_time - limit["window"]
        
        # Remove old entries
        await redis.zremrangebyscore(key, 0, window_start)
        
        # Count current window
        count = await redis.zcard(key)
        
        if count >= limit["max"]:
            # Get oldest entry to calculate retry time
            oldest = await redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1]) + limit["window"] - current_time
                return False, max(1, retry_after)
            return False, limit["window"]
        
        # Add current action
        await redis.zadd(key, {str(uuid.uuid4()): current_time})
        await redis.expire(key, limit["window"])
        
        return True, 0
```

### 6.4 Content Moderation

```python
import re
from typing import Optional

class ContentModerator:
    """Content moderation for messages"""
    
    # Banned patterns (expandable)
    BANNED_PATTERNS = [
        r'\b(spam|scam)\b',
        r'(https?://)?[\w.-]+\.(tk|ml|ga|cf|gq)/',  # Common spam TLDs
    ]
    
    # Link whitelist
    ALLOWED_DOMAINS = [
        'looksy.com',
        'instagram.com',
        'youtube.com',
        'spotify.com',
    ]
    
    async def moderate_message(
        self, 
        text: str, 
        sender_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Moderate message content
        Returns: (is_allowed, rejection_reason)
        """
        # Check for banned patterns
        text_lower = text.lower()
        for pattern in self.BANNED_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                await self.log_moderation_event(sender_id, text, "banned_pattern")
                return False, "Message contains prohibited content"
        
        # Check links
        urls = re.findall(r'https?://[^\s]+', text)
        for url in urls:
            domain = self.extract_domain(url)
            if domain and not self.is_domain_allowed(domain):
                # Allow but flag for review
                await self.flag_for_review(sender_id, text, "suspicious_link")
        
        # Check for excessive caps
        if len(text) > 10 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
            return True, None  # Allow but could add warning
        
        return True, None
    
    def extract_domain(self, url: str) -> Optional[str]:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return None
    
    def is_domain_allowed(self, domain: str) -> bool:
        return any(
            domain == allowed or domain.endswith(f".{allowed}")
            for allowed in self.ALLOWED_DOMAINS
        )
    
    async def log_moderation_event(self, user_id: str, content: str, reason: str):
        await db.moderation_logs.insert_one({
            "user_id": user_id,
            "content_preview": content[:100],
            "reason": reason,
            "action": "blocked",
            "created_at": datetime.utcnow()
        })
    
    async def flag_for_review(self, user_id: str, content: str, reason: str):
        await db.moderation_queue.insert_one({
            "user_id": user_id,
            "content": content,
            "reason": reason,
            "status": "pending",
            "created_at": datetime.utcnow()
        })
```

---

## 7. Implementation Phases

### Phase 1: Core Messaging (Week 1-2)
- [ ] Database schema setup
- [ ] REST API for conversations & messages
- [ ] Basic WebSocket connection
- [ ] Send/receive text messages
- [ ] Message persistence

### Phase 2: Real-time Features (Week 3-4)
- [ ] Typing indicators
- [ ] Read receipts
- [ ] Delivery receipts
- [ ] Online presence
- [ ] Redis Pub/Sub integration

### Phase 3: Rich Media (Week 5-6)
- [ ] Image messages
- [ ] Video messages
- [ ] Voice messages
- [ ] Post sharing
- [ ] Story replies

### Phase 4: Advanced Features (Week 7-8)
- [ ] Message reactions
- [ ] Message editing
- [ ] Message deletion
- [ ] Message requests (non-followers)
- [ ] Group conversations

### Phase 5: Security & Scale (Week 9-10)
- [ ] End-to-end encryption (optional)
- [ ] Rate limiting
- [ ] Content moderation
- [ ] Horizontal scaling
- [ ] Performance optimization

---

## 8. Estimated Resources

### Infrastructure (for 100K DAU)

| Component | Specification | Quantity |
|-----------|--------------|----------|
| WebSocket Servers | 4 vCPU, 8GB RAM | 3-5 |
| API Servers | 2 vCPU, 4GB RAM | 2-3 |
| MongoDB | 8 vCPU, 32GB RAM | 3 (replica set) |
| Redis | 4 vCPU, 16GB RAM | 3 (cluster) |
| Load Balancer | AWS ALB | 1 |
| CDN | CloudFront | 1 |

### Key Metrics to Monitor
- WebSocket connection count
- Message latency (p50, p95, p99)
- Messages per second
- Failed message delivery rate
- Redis memory usage
- MongoDB query performance
