"""
Security Module for Looksy Application
Implements:
- Rate limiting
- Login attempt tracking and account lockout
- IP-based blocking
- Security headers
- Input sanitization
- CAPTCHA verification
"""

import os
import re
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Set
from collections import defaultdict
import asyncio
from functools import wraps

# Configuration
MAX_LOGIN_ATTEMPTS = 5  # Max failed attempts before lockout
LOCKOUT_DURATION_MINUTES = 15  # Lockout duration
RATE_LIMIT_WINDOW_SECONDS = 60  # Time window for rate limiting
RATE_LIMIT_MAX_REQUESTS = 100  # Max requests per window for general endpoints
LOGIN_RATE_LIMIT_MAX = 10  # Max login attempts per window
SUSPICIOUS_ACTIVITY_THRESHOLD = 20  # Failed attempts before IP block
IP_BLOCK_DURATION_HOURS = 24  # IP block duration

# In-memory stores (in production, use Redis)
login_attempts: Dict[str, list] = defaultdict(list)  # email -> list of timestamps
failed_attempts_by_ip: Dict[str, list] = defaultdict(list)  # ip -> list of timestamps
blocked_ips: Dict[str, datetime] = {}  # ip -> unblock_time
request_counts: Dict[str, list] = defaultdict(list)  # ip -> list of timestamps
account_lockouts: Dict[str, datetime] = {}  # email -> lockout_end_time

# Suspicious patterns
SUSPICIOUS_USER_AGENTS = [
    'sqlmap', 'nikto', 'nmap', 'masscan', 'burp', 'zap',
    'acunetix', 'nessus', 'openvas', 'w3af', 'dirbuster'
]

SQL_INJECTION_PATTERNS = [
    r"(\%27)|(\')|(\-\-)|(\%23)|(#)",
    r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",
    r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",
    r"union.*select", r"select.*from", r"insert.*into",
    r"delete.*from", r"drop.*table", r"update.*set"
]

XSS_PATTERNS = [
    r"<script[^>]*>", r"javascript:", r"on\w+\s*=",
    r"<iframe[^>]*>", r"<object[^>]*>", r"<embed[^>]*>"
]


class SecurityManager:
    """Manages all security-related operations"""
    
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger("security")
    
    async def initialize(self):
        """Initialize security collections and indexes"""
        # Create indexes for security collections
        await self.db.security_events.create_index("timestamp", expireAfterSeconds=30*24*60*60)  # 30 days
        await self.db.blocked_ips.create_index("unblock_at", expireAfterSeconds=0)
        await self.db.login_attempts.create_index("timestamp", expireAfterSeconds=24*60*60)  # 24 hours
        await self.db.rate_limits.create_index("timestamp", expireAfterSeconds=300)  # 5 minutes
    
    # ==================== RATE LIMITING ====================
    
    def check_rate_limit(self, ip: str, endpoint: str = "general", 
                         max_requests: int = RATE_LIMIT_MAX_REQUESTS) -> bool:
        """Check if IP has exceeded rate limit"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
        
        key = f"{ip}:{endpoint}"
        
        # Clean old requests
        request_counts[key] = [
            ts for ts in request_counts[key] 
            if ts > window_start
        ]
        
        # Check limit
        if len(request_counts[key]) >= max_requests:
            return False
        
        # Add current request
        request_counts[key].append(now)
        return True
    
    async def check_rate_limit_db(self, ip: str, endpoint: str, 
                                   max_requests: int, window_seconds: int) -> bool:
        """Check rate limit using database (for distributed systems)"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)
        
        count = await self.db.rate_limits.count_documents({
            "ip": ip,
            "endpoint": endpoint,
            "timestamp": {"$gte": window_start.isoformat()}
        })
        
        if count >= max_requests:
            return False
        
        await self.db.rate_limits.insert_one({
            "ip": ip,
            "endpoint": endpoint,
            "timestamp": now.isoformat()
        })
        return True
    
    # ==================== LOGIN ATTEMPT TRACKING ====================
    
    async def record_login_attempt(self, email: str, ip: str, success: bool, 
                                    user_agent: str = None):
        """Record a login attempt"""
        now = datetime.now(timezone.utc)
        
        attempt = {
            "email": email,
            "ip": ip,
            "success": success,
            "user_agent": user_agent,
            "timestamp": now.isoformat()
        }
        
        await self.db.login_attempts.insert_one(attempt)
        
        if not success:
            # Track in memory for quick access
            login_attempts[email].append(now)
            failed_attempts_by_ip[ip].append(now)
            
            # Log security event
            await self.log_security_event(
                "failed_login",
                f"Failed login attempt for {email}",
                ip=ip,
                email=email
            )
    
    async def check_account_locked(self, email: str) -> tuple[bool, Optional[int]]:
        """Check if account is locked due to failed attempts"""
        now = datetime.now(timezone.utc)
        
        # Check in-memory lockout first
        if email in account_lockouts:
            if account_lockouts[email] > now:
                remaining = int((account_lockouts[email] - now).total_seconds() / 60)
                return True, remaining
            else:
                del account_lockouts[email]
        
        # Check recent failed attempts
        window_start = now - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        login_attempts[email] = [
            ts for ts in login_attempts[email] 
            if ts > window_start
        ]
        
        if len(login_attempts[email]) >= MAX_LOGIN_ATTEMPTS:
            lockout_end = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            account_lockouts[email] = lockout_end
            
            await self.log_security_event(
                "account_locked",
                f"Account {email} locked due to {MAX_LOGIN_ATTEMPTS} failed attempts",
                email=email
            )
            
            return True, LOCKOUT_DURATION_MINUTES
        
        return False, None
    
    async def clear_login_attempts(self, email: str):
        """Clear login attempts after successful login"""
        login_attempts[email] = []
        if email in account_lockouts:
            del account_lockouts[email]
    
    async def get_remaining_attempts(self, email: str) -> int:
        """Get remaining login attempts before lockout"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        
        recent_attempts = [
            ts for ts in login_attempts[email] 
            if ts > window_start
        ]
        
        return MAX_LOGIN_ATTEMPTS - len(recent_attempts)
    
    # ==================== IP BLOCKING ====================
    
    def is_ip_blocked(self, ip: str) -> tuple[bool, Optional[int]]:
        """Check if IP is blocked"""
        if ip in blocked_ips:
            now = datetime.now(timezone.utc)
            if blocked_ips[ip] > now:
                remaining = int((blocked_ips[ip] - now).total_seconds() / 3600)
                return True, remaining
            else:
                del blocked_ips[ip]
        return False, None
    
    async def check_suspicious_activity(self, ip: str) -> bool:
        """Check if IP has suspicious activity and should be blocked"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=1)
        
        # Clean old attempts
        failed_attempts_by_ip[ip] = [
            ts for ts in failed_attempts_by_ip[ip] 
            if ts > window_start
        ]
        
        if len(failed_attempts_by_ip[ip]) >= SUSPICIOUS_ACTIVITY_THRESHOLD:
            # Block the IP
            blocked_ips[ip] = now + timedelta(hours=IP_BLOCK_DURATION_HOURS)
            
            await self.log_security_event(
                "ip_blocked",
                f"IP {ip} blocked due to suspicious activity ({len(failed_attempts_by_ip[ip])} failed attempts)",
                ip=ip,
                severity="high"
            )
            
            # Also save to database for persistence
            await self.db.blocked_ips.update_one(
                {"ip": ip},
                {"$set": {
                    "ip": ip,
                    "blocked_at": now.isoformat(),
                    "unblock_at": (now + timedelta(hours=IP_BLOCK_DURATION_HOURS)).isoformat(),
                    "reason": "suspicious_activity"
                }},
                upsert=True
            )
            
            return True
        return False
    
    async def block_ip(self, ip: str, reason: str, duration_hours: int = IP_BLOCK_DURATION_HOURS):
        """Manually block an IP"""
        now = datetime.now(timezone.utc)
        blocked_ips[ip] = now + timedelta(hours=duration_hours)
        
        await self.db.blocked_ips.update_one(
            {"ip": ip},
            {"$set": {
                "ip": ip,
                "blocked_at": now.isoformat(),
                "unblock_at": (now + timedelta(hours=duration_hours)).isoformat(),
                "reason": reason
            }},
            upsert=True
        )
        
        await self.log_security_event("ip_blocked_manual", f"IP {ip} manually blocked: {reason}", ip=ip)
    
    async def unblock_ip(self, ip: str):
        """Unblock an IP"""
        if ip in blocked_ips:
            del blocked_ips[ip]
        await self.db.blocked_ips.delete_one({"ip": ip})
        failed_attempts_by_ip[ip] = []
    
    # ==================== INPUT VALIDATION ====================
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent XSS"""
        if not text:
            return text
        
        # HTML entity encoding for special characters
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        text = text.replace('"', "&quot;")
        text = text.replace("'", "&#x27;")
        
        return text
    
    def check_sql_injection(self, text: str) -> bool:
        """Check if text contains SQL injection patterns"""
        if not text:
            return False
        
        text_lower = text.lower()
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False
    
    def check_xss(self, text: str) -> bool:
        """Check if text contains XSS patterns"""
        if not text:
            return False
        
        for pattern in XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
    
    def is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is from a known security scanner"""
        if not user_agent:
            return False
        
        ua_lower = user_agent.lower()
        return any(tool in ua_lower for tool in SUSPICIOUS_USER_AGENTS)
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_password_strength(self, password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        return True, "Password is strong"
    
    # ==================== CAPTCHA VERIFICATION ====================
    
    async def verify_captcha(self, captcha_token: str, ip: str) -> bool:
        """Verify CAPTCHA token (supports hCaptcha and reCAPTCHA)"""
        captcha_secret = os.environ.get('CAPTCHA_SECRET_KEY')
        captcha_type = os.environ.get('CAPTCHA_TYPE', 'hcaptcha')  # 'hcaptcha' or 'recaptcha'
        
        if not captcha_secret:
            # CAPTCHA not configured, skip verification
            self.logger.warning("CAPTCHA not configured, skipping verification")
            return True
        
        try:
            import aiohttp
            
            if captcha_type == 'hcaptcha':
                verify_url = 'https://hcaptcha.com/siteverify'
            else:
                verify_url = 'https://www.google.com/recaptcha/api/siteverify'
            
            async with aiohttp.ClientSession() as session:
                async with session.post(verify_url, data={
                    'secret': captcha_secret,
                    'response': captcha_token,
                    'remoteip': ip
                }) as response:
                    result = await response.json()
                    return result.get('success', False)
        except Exception as e:
            self.logger.error(f"CAPTCHA verification failed: {e}")
            return False
    
    # ==================== SECURITY LOGGING ====================
    
    async def log_security_event(self, event_type: str, description: str, 
                                  ip: str = None, email: str = None,
                                  severity: str = "medium"):
        """Log a security event"""
        event = {
            "event_type": event_type,
            "description": description,
            "ip": ip,
            "email": email,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.security_events.insert_one(event)
        
        # Log to console for monitoring
        log_msg = f"[SECURITY] [{severity.upper()}] {event_type}: {description}"
        if ip:
            log_msg += f" (IP: {ip})"
        if email:
            log_msg += f" (Email: {email})"
        
        if severity == "high":
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)
    
    async def get_security_events(self, hours: int = 24, event_type: str = None):
        """Get recent security events"""
        query = {
            "timestamp": {
                "$gte": (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            }
        }
        if event_type:
            query["event_type"] = event_type
        
        events = await self.db.security_events.find(
            query, {"_id": 0}
        ).sort("timestamp", -1).to_list(1000)
        
        return events


# Security headers for responses
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://hcaptcha.com https://www.google.com; frame-src https://hcaptcha.com https://www.google.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' https:",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
}


def get_client_ip(request) -> str:
    """Get the real client IP from request"""
    # Check for forwarded headers (when behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    return request.client.host if request.client else "unknown"


def hash_ip(ip: str) -> str:
    """Hash IP for privacy-preserving logging"""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]
