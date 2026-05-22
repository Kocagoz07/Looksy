"""
Device Fingerprint and Affiliate Abuse Detection System for Looksy
Detects fraudulent activity like fake accounts, self-liking, and abuse patterns
"""

import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Set
from collections import defaultdict
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class FraudDetectionService:
    """Detects and prevents affiliate abuse and fraudulent activity"""
    
    # Thresholds for suspicious activity
    THRESHOLDS = {
        "max_accounts_per_device": 2,
        "max_accounts_per_ip_per_day": 3,
        "max_likes_per_minute": 20,
        "max_stars_per_hour": 500,
        "suspicious_like_ratio": 0.8,  # 80% likes from same users = suspicious
        "min_time_between_accounts": 300,  # 5 minutes
    }
    
    # Risk score weights
    RISK_WEIGHTS = {
        "multiple_accounts_same_device": 30,
        "multiple_accounts_same_ip": 20,
        "self_like_pattern": 50,
        "rapid_star_accumulation": 25,
        "new_account_high_activity": 15,
        "suspicious_like_network": 40,
        "known_fraudulent_device": 60,
        "vpn_detected": 10,
    }
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        # In-memory caches for real-time detection
        self.recent_likes: Dict[str, List[datetime]] = defaultdict(list)
        self.device_accounts: Dict[str, Set[str]] = defaultdict(set)
        self.ip_registrations: Dict[str, List[datetime]] = defaultdict(list)
    
    async def initialize(self):
        """Initialize indexes for fraud detection collections"""
        try:
            # Device fingerprints collection
            await self.db.device_fingerprints.create_index("fingerprint_hash", unique=True)
            await self.db.device_fingerprints.create_index("user_ids")
            await self.db.device_fingerprints.create_index("is_flagged")
            
            # Fraud events collection
            await self.db.fraud_events.create_index("user_id")
            await self.db.fraud_events.create_index("event_type")
            await self.db.fraud_events.create_index("created_at")
            
            # User risk scores collection
            await self.db.user_risk_scores.create_index("user_id", unique=True)
            await self.db.user_risk_scores.create_index("risk_score")
            
            logger.info("Fraud detection indexes created successfully")
        except Exception as e:
            logger.warning(f"Fraud detection index creation: {e}")
    
    # ==================== DEVICE FINGERPRINTING ====================
    
    def generate_fingerprint_hash(self, fingerprint_data: dict) -> str:
        """Generate a unique hash from device fingerprint data"""
        # Combine key fingerprint components
        components = [
            str(fingerprint_data.get("user_agent", "")),
            str(fingerprint_data.get("screen_resolution", "")),
            str(fingerprint_data.get("timezone", "")),
            str(fingerprint_data.get("language", "")),
            str(fingerprint_data.get("platform", "")),
            str(fingerprint_data.get("canvas_hash", "")),
            str(fingerprint_data.get("webgl_hash", "")),
            str(fingerprint_data.get("audio_hash", "")),
            str(fingerprint_data.get("fonts", "")),
        ]
        
        fingerprint_string = "|".join(components)
        return hashlib.sha256(fingerprint_string.encode()).hexdigest()
    
    async def record_device_fingerprint(
        self,
        user_id: str,
        fingerprint_data: dict,
        ip_address: str
    ) -> dict:
        """Record device fingerprint and check for suspicious patterns"""
        
        fingerprint_hash = self.generate_fingerprint_hash(fingerprint_data)
        now = datetime.now(timezone.utc)
        
        # Check if fingerprint exists
        existing = await self.db.device_fingerprints.find_one(
            {"fingerprint_hash": fingerprint_hash},
            {"_id": 0}
        )
        
        flags = []
        risk_score = 0
        
        if existing:
            existing_users = set(existing.get("user_ids", []))
            
            # Check if this device is used by multiple accounts
            if user_id not in existing_users:
                existing_users.add(user_id)
                
                if len(existing_users) > self.THRESHOLDS["max_accounts_per_device"]:
                    flags.append("multiple_accounts_same_device")
                    risk_score += self.RISK_WEIGHTS["multiple_accounts_same_device"]
                    
                    # Log fraud event
                    await self.log_fraud_event(
                        user_id=user_id,
                        event_type="multiple_accounts_same_device",
                        details={
                            "fingerprint_hash": fingerprint_hash[:16] + "...",
                            "total_accounts": len(existing_users),
                            "other_user_ids": list(existing_users - {user_id})[:5]
                        }
                    )
            
            # Check if device is already flagged
            if existing.get("is_flagged"):
                flags.append("known_fraudulent_device")
                risk_score += self.RISK_WEIGHTS["known_fraudulent_device"]
            
            # Update fingerprint record
            await self.db.device_fingerprints.update_one(
                {"fingerprint_hash": fingerprint_hash},
                {
                    "$addToSet": {"user_ids": user_id, "ip_addresses": ip_address},
                    "$set": {"last_seen": now.isoformat()},
                    "$inc": {"access_count": 1}
                }
            )
        else:
            # Create new fingerprint record
            await self.db.device_fingerprints.insert_one({
                "fingerprint_hash": fingerprint_hash,
                "user_ids": [user_id],
                "ip_addresses": [ip_address],
                "fingerprint_data": {
                    "user_agent": fingerprint_data.get("user_agent"),
                    "screen_resolution": fingerprint_data.get("screen_resolution"),
                    "timezone": fingerprint_data.get("timezone"),
                    "platform": fingerprint_data.get("platform"),
                },
                "first_seen": now.isoformat(),
                "last_seen": now.isoformat(),
                "access_count": 1,
                "is_flagged": False
            })
        
        # Update user's risk score
        if risk_score > 0:
            await self.update_user_risk_score(user_id, risk_score, flags)
        
        return {
            "fingerprint_hash": fingerprint_hash[:16] + "...",
            "flags": flags,
            "risk_score_added": risk_score
        }
    
    # ==================== IP-BASED DETECTION ====================
    
    async def check_ip_abuse(self, ip_address: str, user_id: str) -> dict:
        """Check for IP-based abuse patterns"""
        
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(days=1)
        
        flags = []
        risk_score = 0
        
        # Count recent registrations from this IP
        recent_registrations = await self.db.users.count_documents({
            "registration_ip": ip_address,
            "created_at": {"$gte": day_ago.isoformat()}
        })
        
        if recent_registrations > self.THRESHOLDS["max_accounts_per_ip_per_day"]:
            flags.append("multiple_accounts_same_ip")
            risk_score += self.RISK_WEIGHTS["multiple_accounts_same_ip"]
            
            await self.log_fraud_event(
                user_id=user_id,
                event_type="multiple_accounts_same_ip",
                details={
                    "ip_address": ip_address,
                    "registrations_24h": recent_registrations
                }
            )
        
        # Check for VPN/proxy (simplified check - in production use a service)
        if await self.is_suspicious_ip(ip_address):
            flags.append("vpn_detected")
            risk_score += self.RISK_WEIGHTS["vpn_detected"]
        
        return {"flags": flags, "risk_score": risk_score}
    
    async def is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP is known VPN/proxy (simplified)"""
        # In production, use services like MaxMind, IPQualityScore, etc.
        # For now, check against our internal flagged IPs
        flagged = await self.db.flagged_ips.find_one({"ip": ip_address})
        return flagged is not None
    
    # ==================== LIKE PATTERN DETECTION ====================
    
    async def check_like_abuse(self, liker_id: str, post_owner_id: str, post_id: str) -> dict:
        """Check for like-based abuse patterns"""
        
        now = datetime.now(timezone.utc)
        flags = []
        risk_score = 0
        
        # Self-liking check (same device/IP for both accounts)
        if await self.are_accounts_related(liker_id, post_owner_id):
            flags.append("self_like_pattern")
            risk_score += self.RISK_WEIGHTS["self_like_pattern"]
            
            await self.log_fraud_event(
                user_id=liker_id,
                event_type="self_like_pattern",
                details={
                    "post_id": post_id,
                    "post_owner_id": post_owner_id,
                    "relationship": "same_device_or_ip"
                }
            )
        
        # Rate limiting check
        self.recent_likes[liker_id].append(now)
        # Clean old entries
        minute_ago = now - timedelta(minutes=1)
        self.recent_likes[liker_id] = [
            t for t in self.recent_likes[liker_id] if t > minute_ago
        ]
        
        if len(self.recent_likes[liker_id]) > self.THRESHOLDS["max_likes_per_minute"]:
            flags.append("rapid_like_activity")
            risk_score += 15
            
            await self.log_fraud_event(
                user_id=liker_id,
                event_type="rapid_like_activity",
                details={"likes_per_minute": len(self.recent_likes[liker_id])}
            )
        
        # Check for like network (group of accounts liking each other)
        network_score = await self.check_like_network(liker_id, post_owner_id)
        if network_score > 0:
            flags.append("suspicious_like_network")
            risk_score += network_score
        
        # Update risk scores if needed
        if risk_score > 0:
            await self.update_user_risk_score(liker_id, risk_score, flags)
        
        return {
            "allowed": risk_score < 50,  # Block if risk too high
            "flags": flags,
            "risk_score": risk_score
        }
    
    async def are_accounts_related(self, user1_id: str, user2_id: str) -> bool:
        """Check if two accounts are likely the same person"""
        
        # Check if same device fingerprint
        fp1 = await self.db.device_fingerprints.find_one(
            {"user_ids": user1_id},
            {"fingerprint_hash": 1, "_id": 0}
        )
        fp2 = await self.db.device_fingerprints.find_one(
            {"user_ids": user2_id},
            {"fingerprint_hash": 1, "_id": 0}
        )
        
        if fp1 and fp2 and fp1.get("fingerprint_hash") == fp2.get("fingerprint_hash"):
            return True
        
        # Check if same IP at registration
        user1 = await self.db.users.find_one({"user_id": user1_id}, {"registration_ip": 1, "_id": 0})
        user2 = await self.db.users.find_one({"user_id": user2_id}, {"registration_ip": 1, "_id": 0})
        
        if user1 and user2:
            ip1 = user1.get("registration_ip")
            ip2 = user2.get("registration_ip")
            if ip1 and ip2 and ip1 == ip2:
                return True
        
        return False
    
    async def check_like_network(self, liker_id: str, post_owner_id: str) -> int:
        """Detect suspicious like networks (circular liking patterns)"""
        
        # Get recent likes between these users
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Count how many times the post owner liked the liker's posts
        reverse_likes = await self.db.posts.count_documents({
            "user_id": liker_id,
            "likes": post_owner_id,
            "created_at": {"$gte": hour_ago.isoformat()}
        })
        
        # Also check if liker has liked many of this owner's posts
        owner_posts_liked = await self.db.posts.count_documents({
            "user_id": post_owner_id,
            "likes": liker_id
        })
        
        owner_total_posts = await self.db.posts.count_documents({"user_id": post_owner_id})
        
        # If they've liked almost all of each other's posts, suspicious
        if owner_total_posts > 0:
            like_ratio = owner_posts_liked / owner_total_posts
            if like_ratio > self.THRESHOLDS["suspicious_like_ratio"] and reverse_likes > 3:
                return self.RISK_WEIGHTS["suspicious_like_network"]
        
        return 0
    
    # ==================== STAR ACCUMULATION DETECTION ====================
    
    async def check_star_abuse(self, user_id: str, stars_gained: int) -> dict:
        """Check for suspicious star accumulation"""
        
        flags = []
        risk_score = 0
        
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        
        # Count stars gained in last hour
        recent_events = await self.db.star_events.find({
            "user_id": user_id,
            "created_at": {"$gte": hour_ago.isoformat()}
        }).to_list(1000)
        
        total_recent_stars = sum(e.get("stars", 0) for e in recent_events)
        
        if total_recent_stars > self.THRESHOLDS["max_stars_per_hour"]:
            flags.append("rapid_star_accumulation")
            risk_score += self.RISK_WEIGHTS["rapid_star_accumulation"]
            
            await self.log_fraud_event(
                user_id=user_id,
                event_type="rapid_star_accumulation",
                details={
                    "stars_per_hour": total_recent_stars,
                    "threshold": self.THRESHOLDS["max_stars_per_hour"]
                }
            )
        
        # Check if new account with high activity
        user = await self.db.users.find_one({"user_id": user_id}, {"created_at": 1, "_id": 0})
        if user:
            created_at = user.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                account_age_hours = (now - created_at).total_seconds() / 3600
                if account_age_hours < 24 and total_recent_stars > 100:
                    flags.append("new_account_high_activity")
                    risk_score += self.RISK_WEIGHTS["new_account_high_activity"]
        
        if risk_score > 0:
            await self.update_user_risk_score(user_id, risk_score, flags)
        
        return {"flags": flags, "risk_score": risk_score}
    
    # ==================== RISK SCORING ====================
    
    async def update_user_risk_score(self, user_id: str, score_delta: int, flags: List[str]):
        """Update user's cumulative risk score"""
        
        now = datetime.now(timezone.utc).isoformat()
        
        await self.db.user_risk_scores.update_one(
            {"user_id": user_id},
            {
                "$inc": {"risk_score": score_delta},
                "$addToSet": {"flags": {"$each": flags}},
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )
        
        # Check if user should be flagged/blocked
        user_risk = await self.db.user_risk_scores.find_one(
            {"user_id": user_id},
            {"risk_score": 1, "_id": 0}
        )
        
        if user_risk and user_risk.get("risk_score", 0) >= 100:
            # Auto-flag user for review
            await self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"is_flagged": True, "flagged_at": now, "flag_reason": "High fraud risk score"}}
            )
            
            logger.warning(f"User {user_id} auto-flagged for high risk score: {user_risk['risk_score']}")
    
    async def get_user_risk_score(self, user_id: str) -> dict:
        """Get user's current risk score and flags"""
        
        risk_data = await self.db.user_risk_scores.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if not risk_data:
            return {"user_id": user_id, "risk_score": 0, "flags": [], "status": "clean"}
        
        score = risk_data.get("risk_score", 0)
        status = "clean"
        if score >= 100:
            status = "blocked"
        elif score >= 50:
            status = "flagged"
        elif score >= 25:
            status = "suspicious"
        
        risk_data["status"] = status
        return risk_data
    
    # ==================== EVENT LOGGING ====================
    
    async def log_fraud_event(self, user_id: str, event_type: str, details: dict):
        """Log a fraud event for audit purposes"""
        
        await self.db.fraud_events.insert_one({
            "user_id": user_id,
            "event_type": event_type,
            "details": details,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    async def get_fraud_events(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Get fraud events with optional filters"""
        
        query = {}
        if user_id:
            query["user_id"] = user_id
        if event_type:
            query["event_type"] = event_type
        
        events = await self.db.fraud_events.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return events
    
    # ==================== ADMIN FUNCTIONS ====================
    
    async def get_flagged_users(self, limit: int = 50) -> List[dict]:
        """Get list of flagged users for admin review"""
        
        users = await self.db.user_risk_scores.find(
            {"risk_score": {"$gte": 50}},
            {"_id": 0}
        ).sort("risk_score", -1).limit(limit).to_list(limit)
        
        # Enrich with user info
        for user in users:
            user_info = await self.db.users.find_one(
                {"user_id": user["user_id"]},
                {"_id": 0, "name": 1, "email": 1, "created_at": 1}
            )
            if user_info:
                user["name"] = user_info.get("name")
                user["email"] = user_info.get("email")
                user["created_at"] = user_info.get("created_at")
        
        return users
    
    async def clear_user_flags(self, user_id: str) -> bool:
        """Clear user's fraud flags (admin action)"""
        
        await self.db.user_risk_scores.update_one(
            {"user_id": user_id},
            {"$set": {"risk_score": 0, "flags": [], "cleared_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$unset": {"is_flagged": 1, "flagged_at": 1, "flag_reason": 1}}
        )
        
        return True
    
    async def flag_device(self, fingerprint_hash: str, reason: str) -> bool:
        """Flag a device fingerprint as fraudulent"""
        
        result = await self.db.device_fingerprints.update_one(
            {"fingerprint_hash": fingerprint_hash},
            {
                "$set": {
                    "is_flagged": True,
                    "flagged_at": datetime.now(timezone.utc).isoformat(),
                    "flag_reason": reason
                }
            }
        )
        
        return result.modified_count > 0
