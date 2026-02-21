from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timezone, timedelta
import secrets
import io
from bson import ObjectId
import gridfs
import pymongo
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
sync_client = pymongo.MongoClient(mongo_url)
sync_db = sync_client[os.environ['DB_NAME']]
fs = gridfs.GridFS(sync_db)

# Create the main app without a prefix
app = FastAPI()

# Add CORS middleware FIRST (before routes)
cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    password_hash: Optional[str] = None  # For email/password auth
    picture: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None  # "men", "women", or None
    earnings: float = 0.0
    earnings_eur: float = 0.0
    stars: int = 0  # Stars earned from engagement
    payout_points: float = 0.0  # Converted from stars
    kyc_verified: bool = False
    kyc_documents: Optional[dict] = None
    payout_method: Optional[str] = None  # "paypal" or "stripe"
    payout_email: Optional[str] = None
    stripe_account_id: Optional[str] = None
    starred_posts: List[str] = []
    favorited_posts: List[str] = []
    followers: List[str] = []  # List of user_ids
    following: List[str] = []  # List of user_ids
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductLink(BaseModel):
    url: str
    name: str

class Post(BaseModel):
    model_config = ConfigDict(extra="ignore")
    post_id: str
    user_id: str
    image_id: str  # GridFS file ID
    caption: Optional[str] = None
    music: Optional[str] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    total_price: Optional[float] = None
    total_price_eur: Optional[float] = None
    products: List[ProductLink] = []
    likes_count: int = 0
    liked_by: List[str] = []  # List of user_ids
    starred_by: List[str] = []  # List of user_ids who starred this
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Comment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    comment_id: str
    post_id: str
    user_id: str
    user_name: str
    user_picture: Optional[str] = None
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MagicLink(BaseModel):
    model_config = ConfigDict(extra="ignore")
    email: str
    token: str
    category: str  # "men" or "women"
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MagicLinkRequest(BaseModel):
    email: EmailStr
    category: str

class EmailPasswordLogin(BaseModel):
    email: EmailStr
    password: str
    category: str

class EmailPasswordRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    category: str

class PostCreate(BaseModel):
    caption: Optional[str] = None
    music: Optional[str] = None
    location: Optional[str] = None
    venue: Optional[str] = None
    total_price: Optional[float] = None
    products: List[ProductLink] = []

class CommentCreate(BaseModel):
    text: str

class KYCSubmission(BaseModel):
    full_name: str
    date_of_birth: str
    address: str
    id_type: str  # "passport", "drivers_license", "national_id"
    id_number: str

class PayoutMethodSetup(BaseModel):
    method: str  # "paypal" or "stripe"
    payout_email: Optional[str] = None
    stripe_account_id: Optional[str] = None

class PayoutRequest(BaseModel):
    amount_eur: float

class Payout(BaseModel):
    model_config = ConfigDict(extra="ignore")
    payout_id: str
    user_id: str
    amount_eur: float
    method: str
    status: str  # "pending", "completed", "failed"
    payout_email: Optional[str] = None
    transaction_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class CollaborationMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message_id: str
    from_user_id: str
    from_user_name: str
    from_user_picture: Optional[str] = None
    to_user_id: str
    subject: str
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = False

class CollaborationRequest(BaseModel):
    to_user_id: str
    subject: str
    message: str

class AIAnalysisRequest(BaseModel):
    subject: str
    message: str
    from_user_name: str

class AIReplyRequest(BaseModel):
    subject: str
    message: str
    from_user_name: str
    reply_tone: str = "professional"  # professional, friendly, brief

# Payment Transaction Model
class PaymentTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    transaction_id: str
    user_id: str
    session_id: str
    amount: float
    currency: str
    payment_type: str  # "payout" or "topup"
    payment_method: str  # "stripe" or "paypal"
    payment_status: str  # "pending", "completed", "failed"
    metadata: Optional[Dict[str, str]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

# Stars to Payout Points conversion request
class ConvertStarsRequest(BaseModel):
    stars_to_convert: int

# Stripe payout request
class StripePayoutRequest(BaseModel):
    amount_eur: float
    origin_url: str

# PayPal payout request
class PayPalPayoutRequest(BaseModel):
    amount_eur: float
    paypal_email: str

# Helper function to convert USD to EUR
def usd_to_eur(usd_amount: float) -> float:
    rate = float(os.environ.get('USD_TO_EUR_RATE', '0.92'))
    return round(usd_amount * rate, 2)

# Helper function to calculate earnings from likes
def calculate_earnings(likes_count: int) -> float:
    if likes_count < 1000:
        return likes_count * 0.05
    elif likes_count < 3000:
        return 1000 * 0.05 + (likes_count - 1000) * 0.10
    elif likes_count < 10000:
        return 1000 * 0.05 + 2000 * 0.10 + (likes_count - 3000) * 0.20
    else:
        return 1000 * 0.05 + 2000 * 0.10 + 7000 * 0.20 + (likes_count - 10000) * 0.50

# Helper function to calculate payout points from stars
# 1-1000 stars: $0.0005 per star (0.05 cents)
# 1000-5000 stars: $0.001 per star (0.10 cents)
# 5000-10000 stars: $0.002 per star (0.20 cents)
# Max 10,000 stars per post
def calculate_payout_points(stars: int) -> float:
    """Convert stars to payout points (USD value)"""
    if stars <= 0:
        return 0.0
    
    # Cap at 10,000 stars
    stars = min(stars, 10000)
    
    points = 0.0
    
    # First 1000 stars: $0.0005 each (0.05 cents)
    first_tier = min(stars, 1000)
    points += first_tier * 0.0005
    
    # 1001-5000 stars: $0.001 each (0.10 cents)
    if stars > 1000:
        second_tier = min(stars - 1000, 4000)
        points += second_tier * 0.001
    
    # 5001-10000 stars: $0.002 each (0.20 cents)
    if stars > 5000:
        third_tier = min(stars - 5000, 5000)
        points += third_tier * 0.002
    
    return round(points, 4)

# Auth helper
async def get_current_user(request: Request) -> Optional[User]:
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        return None
    
    session_doc = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session_doc:
        return None
    
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    
    user_doc = await db.users.find_one({"user_id": session_doc["user_id"]}, {"_id": 0})
    if not user_doc:
        return None
    
    return User(**user_doc)

# Auth endpoints
@api_router.post("/auth/register")
async def register_with_password(request: EmailPasswordRegister, response: Response):
    email = request.email.lower()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    password_hash = pwd_context.hash(request.password)
    
    # Create new user
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    new_user = User(
        user_id=user_id,
        email=email,
        name=request.name,
        password_hash=password_hash,
        category=request.category
    )
    
    user_dict = new_user.model_dump()
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    await db.users.insert_one(user_dict)
    
    # Create session
    session_token = f"session_{secrets.token_urlsafe(32)}"
    session_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=session_expires_at
    )
    session_dict = session.model_dump()
    session_dict["expires_at"] = session_dict["expires_at"].isoformat()
    session_dict["created_at"] = session_dict["created_at"].isoformat()
    
    await db.user_sessions.insert_one(session_dict)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    # Fetch user from DB without _id and password_hash
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return user_doc

@api_router.post("/auth/login")
async def login_with_password(request: EmailPasswordLogin, response: Response):
    email = request.email.lower()
    
    # Find user
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not user_doc.get("password_hash"):
        raise HTTPException(status_code=401, detail="Please use magic link to sign in")
    
    if not pwd_context.verify(request.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Update category if provided
    if user_doc.get("category") != request.category:
        await db.users.update_one(
            {"user_id": user_doc["user_id"]},
            {"$set": {"category": request.category}}
        )
    
    # Create session
    session_token = f"session_{secrets.token_urlsafe(32)}"
    session_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user_doc["user_id"],
        session_token=session_token,
        expires_at=session_expires_at
    )
    session_dict = session.model_dump()
    session_dict["expires_at"] = session_dict["expires_at"].isoformat()
    session_dict["created_at"] = session_dict["created_at"].isoformat()
    
    await db.user_sessions.insert_one(session_dict)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    # Return user without password_hash
    user_dict_response = {k: v for k, v in user_doc.items() if k != 'password_hash'}
    return user_dict_response

@api_router.post("/auth/send-magic-link")
async def send_magic_link(request: MagicLinkRequest):
    email = request.email.lower()
    category = request.category
    
    if category not in ["men", "women"]:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    # Generate magic link token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Store magic link
    magic_link = MagicLink(
        email=email,
        token=token,
        category=category,
        expires_at=expires_at
    )
    
    magic_link_dict = magic_link.model_dump()
    magic_link_dict["expires_at"] = magic_link_dict["expires_at"].isoformat()
    magic_link_dict["created_at"] = magic_link_dict["created_at"].isoformat()
    
    # Delete any existing magic links for this email
    await db.magic_links.delete_many({"email": email})
    await db.magic_links.insert_one(magic_link_dict)
    
    # In production, send email here. For now, return the link for testing
    magic_link_url = f"{os.environ.get('FRONTEND_URL', 'http://localhost:3000')}/auth/verify?token={token}"
    
    # For development: log the magic link
    logger.info(f"Magic link for {email}: {magic_link_url}")
    
    return {
        "message": "Magic link sent to your email",
        "magic_link": magic_link_url  # Remove this in production
    }

@api_router.get("/auth/verify-magic-link")
async def verify_magic_link(token: str, response: Response):
    # Find magic link
    magic_link_doc = await db.magic_links.find_one({"token": token}, {"_id": 0})
    
    if not magic_link_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired magic link")
    
    # Check expiry
    expires_at = magic_link_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        await db.magic_links.delete_one({"token": token})
        raise HTTPException(status_code=400, detail="Magic link has expired")
    
    email = magic_link_doc["email"]
    category = magic_link_doc["category"]
    
    # Check if user exists
    user_doc = await db.users.find_one({"email": email}, {"_id": 0})
    
    if user_doc:
        user_id = user_doc["user_id"]
        # Update category if changed
        if user_doc.get("category") != category:
            await db.users.update_one(
                {"user_id": user_id},
                {"$set": {"category": category}}
            )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        name = email.split("@")[0].title()
        new_user = User(
            user_id=user_id,
            email=email,
            name=name,
            category=category
        )
        user_dict = new_user.model_dump()
        user_dict["created_at"] = user_dict["created_at"].isoformat()
        await db.users.insert_one(user_dict)
    
    # Create session
    session_token = f"session_{secrets.token_urlsafe(32)}"
    session_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=session_expires_at
    )
    session_dict = session.model_dump()
    session_dict["expires_at"] = session_dict["expires_at"].isoformat()
    session_dict["created_at"] = session_dict["created_at"].isoformat()
    
    await db.user_sessions.insert_one(session_dict)
    
    # Delete used magic link
    await db.magic_links.delete_one({"token": token})
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return User(**user_doc)

@api_router.get("/auth/me", response_model=User)
async def get_me(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"message": "Logged out"}

# User search endpoint
@api_router.get("/users/search")
async def search_users(request: Request, q: str = ""):
    """Search users by name or email"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not q or len(q) < 2:
        return {"users": []}
    
    # Search by name (case-insensitive) or email prefix
    users = await db.users.find(
        {
            "$or": [
                {"name": {"$regex": q, "$options": "i"}},
                {"email": {"$regex": f"^{q}", "$options": "i"}}
            ]
        },
        {"_id": 0, "user_id": 1, "name": 1, "picture": 1, "category": 1, "bio": 1}
    ).limit(20).to_list(20)
    
    return {"users": users}

# User endpoints
@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user_doc)

@api_router.patch("/users/me")
async def update_user(request: Request, category: Optional[str] = None, bio: Optional[str] = None, name: Optional[str] = None):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    update_data = {}
    if category and category not in ["men", "women"]:
        raise HTTPException(status_code=400, detail="Invalid category")
    if category:
        update_data["category"] = category
    if bio is not None:
        update_data["bio"] = bio
    if name:
        update_data["name"] = name
    
    if update_data:
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$set": update_data}
        )
    
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    # Remove password_hash from response
    if "password_hash" in user_doc:
        del user_doc["password_hash"]
    return User(**user_doc)

@api_router.post("/users/me/profile-picture")
async def update_profile_picture(request: Request, file: UploadFile = File(...)):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Upload image to GridFS
    contents = await file.read()
    file_id = fs.put(contents, filename=file.filename, content_type=file.content_type)
    
    # Update user picture
    picture_url = f"/api/images/{str(file_id)}"
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"picture": picture_url}}
    )
    
    return {"picture": picture_url}

# Image upload to GridFS
@api_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    contents = await file.read()
    file_id = fs.put(contents, filename=file.filename, content_type=file.content_type)
    return {"file_id": str(file_id)}

@api_router.get("/images/{file_id}")
async def get_image(file_id: str):
    try:
        grid_out = fs.get(ObjectId(file_id))
        return StreamingResponse(
            io.BytesIO(grid_out.read()),
            media_type=grid_out.content_type or "image/jpeg"
        )
    except:
        raise HTTPException(status_code=404, detail="Image not found")

# Post endpoints
@api_router.post("/posts", response_model=Post)
async def create_post(request: Request, post_data: PostCreate, image_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    post_id = f"post_{uuid.uuid4().hex[:12]}"
    
    # Convert USD to EUR if price provided
    total_price_eur = None
    if post_data.total_price:
        total_price_eur = usd_to_eur(post_data.total_price)
    
    post = Post(
        post_id=post_id,
        user_id=user.user_id,
        image_id=image_id,
        total_price_eur=total_price_eur,
        **post_data.model_dump()
    )
    
    post_dict = post.model_dump()
    post_dict["created_at"] = post_dict["created_at"].isoformat()
    await db.posts.insert_one(post_dict)
    
    return post

@api_router.get("/posts", response_model=List[Post])
async def get_posts(category: Optional[str] = None, limit: int = 50):
    query = {"is_deleted": {"$ne": True}}
    if category:
        # Get users in this category
        users = await db.users.find({"category": category}, {"user_id": 1, "_id": 0}).to_list(1000)
        user_ids = [u["user_id"] for u in users]
        query["user_id"] = {"$in": user_ids}
    
    posts = await db.posts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    
    for post in posts:
        if isinstance(post["created_at"], str):
            post["created_at"] = datetime.fromisoformat(post["created_at"])
    
    return posts

@api_router.get("/posts/stars", response_model=List[Post])
async def get_stars_posts(limit: int = 50):
    posts = await db.posts.find({"likes_count": {"$gte": 10000}, "is_deleted": {"$ne": True}}, {"_id": 0}).sort("likes_count", -1).limit(limit).to_list(limit)
    
    for post in posts:
        if isinstance(post["created_at"], str):
            post["created_at"] = datetime.fromisoformat(post["created_at"])
    
    return posts

@api_router.get("/posts/celebrity")
async def get_celebrity_posts_v2(skip: int = 0, limit: int = 20):
    """Get posts with 10,000+ likes - Celebrity/Star posts"""
    posts = await db.posts.find(
        {"is_deleted": False, "likes_count": {"$gte": 10000}},
        {"_id": 0}
    ).sort("likes_count", -1).skip(skip).limit(limit).to_list(limit)
    
    # Add user info to each post
    for post in posts:
        owner = await db.users.find_one({"user_id": post["user_id"]}, {"_id": 0, "name": 1, "picture": 1, "category": 1})
        if owner:
            post["user_name"] = owner.get("name", "Unknown")
            post["user_picture"] = owner.get("picture")
            post["user_category"] = owner.get("category")
    
    total = await db.posts.count_documents({"is_deleted": False, "likes_count": {"$gte": 10000}})
    
    return {
        "posts": posts,
        "total": total,
        "has_more": skip + limit < total
    }

@api_router.get("/posts/{post_id}", response_model=Post)
async def get_post(post_id: str):
    post_doc = await db.posts.find_one({"post_id": post_id}, {"_id": 0})
    if not post_doc:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if isinstance(post_doc["created_at"], str):
        post_doc["created_at"] = datetime.fromisoformat(post_doc["created_at"])
    
    return Post(**post_doc)

@api_router.delete("/posts/{post_id}")
async def delete_post(request: Request, post_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    post = await db.posts.find_one({"post_id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Soft delete
    await db.posts.update_one(
        {"post_id": post_id},
        {
            "$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Post deleted successfully"}

@api_router.post("/posts/{post_id}/star")
async def toggle_star(request: Request, post_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    post = await db.posts.find_one({"post_id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    starred_by = post.get("starred_by", [])
    
    if user.user_id in starred_by:
        # Unstar
        await db.posts.update_one(
            {"post_id": post_id},
            {"$pull": {"starred_by": user.user_id}}
        )
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$pull": {"starred_posts": post_id}}
        )
        return {"starred": False}
    else:
        # Star
        await db.posts.update_one(
            {"post_id": post_id},
            {"$addToSet": {"starred_by": user.user_id}}
        )
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$addToSet": {"starred_posts": post_id}}
        )
        return {"starred": True}

@api_router.post("/posts/{post_id}/like")
async def toggle_like(request: Request, post_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    post = await db.posts.find_one({"post_id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    liked_by = post.get("liked_by", [])
    
    if user.user_id in liked_by:
        # Unlike
        await db.posts.update_one(
            {"post_id": post_id},
            {
                "$pull": {"liked_by": user.user_id},
                "$inc": {"likes_count": -1}
            }
        )
        new_likes = post["likes_count"] - 1
    else:
        # Like
        await db.posts.update_one(
            {"post_id": post_id},
            {
                "$addToSet": {"liked_by": user.user_id},
                "$inc": {"likes_count": 1}
            }
        )
        new_likes = post["likes_count"] + 1
    
    # Update post owner's earnings
    earnings_usd = calculate_earnings(new_likes)
    earnings_eur = usd_to_eur(earnings_usd)
    await db.users.update_one(
        {"user_id": post["user_id"]},
        {
            "$set": {
                "earnings": earnings_usd,
                "earnings_eur": earnings_eur
            }
        }
    )
    
    return {"likes_count": new_likes, "liked": user.user_id not in liked_by}

# Comment endpoints
@api_router.get("/posts/{post_id}/comments", response_model=List[Comment])
async def get_comments(post_id: str):
    comments = await db.comments.find({"post_id": post_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for comment in comments:
        if isinstance(comment["created_at"], str):
            comment["created_at"] = datetime.fromisoformat(comment["created_at"])
    
    return comments

@api_router.post("/posts/{post_id}/comments", response_model=Comment)
async def create_comment(request: Request, post_id: str, comment_data: CommentCreate):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    comment_id = f"comment_{uuid.uuid4().hex[:12]}"
    comment = Comment(
        comment_id=comment_id,
        post_id=post_id,
        user_id=user.user_id,
        user_name=user.name,
        user_picture=user.picture,
        text=comment_data.text
    )
    
    comment_dict = comment.model_dump()
    comment_dict["created_at"] = comment_dict["created_at"].isoformat()
    await db.comments.insert_one(comment_dict)
    
    return comment

@api_router.delete("/comments/{comment_id}")
async def delete_comment(request: Request, comment_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    comment = await db.comments.find_one({"comment_id": comment_id}, {"_id": 0})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment["user_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.comments.delete_one({"comment_id": comment_id})
    
    return {"message": "Comment deleted"}

@api_router.get("/users/{user_id}/posts", response_model=List[Post])
async def get_user_posts(user_id: str):
    posts = await db.posts.find({"user_id": user_id, "is_deleted": {"$ne": True}}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for post in posts:
        if isinstance(post["created_at"], str):
            post["created_at"] = datetime.fromisoformat(post["created_at"])
    
    return posts

# KYC and Payout endpoints
@api_router.post("/users/me/kyc")
async def submit_kyc(request: Request, kyc_data: KYCSubmission):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Store KYC documents
    kyc_dict = kyc_data.model_dump()
    
    await db.users.update_one(
        {"user_id": user.user_id},
        {
            "$set": {
                "kyc_verified": True,  # In production, this should be False until verified
                "kyc_documents": kyc_dict
            }
        }
    )
    
    return {"message": "KYC documents submitted successfully", "verified": True}

@api_router.post("/users/{user_id}/follow")
async def toggle_follow(request: Request, user_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if user.user_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Check if target user exists
    target_user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already following
    current_user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    following_list = current_user_doc.get("following", [])
    
    if user_id in following_list:
        # Unfollow
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$pull": {"following": user_id}}
        )
        await db.users.update_one(
            {"user_id": user_id},
            {"$pull": {"followers": user.user_id}}
        )
        return {"following": False}
    else:
        # Follow
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$addToSet": {"following": user_id}}
        )
        await db.users.update_one(
            {"user_id": user_id},
            {"$addToSet": {"followers": user.user_id}}
        )
        return {"following": True}

@api_router.post("/users/me/payout-method")
async def set_payout_method(request: Request, payout_setup: PayoutMethodSetup):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if payout_setup.method not in ["paypal", "stripe"]:
        raise HTTPException(status_code=400, detail="Invalid payout method")
    
    update_data = {"payout_method": payout_setup.method}
    
    if payout_setup.method == "paypal":
        if not payout_setup.payout_email:
            raise HTTPException(status_code=400, detail="PayPal email required")
        update_data["payout_email"] = payout_setup.payout_email
    elif payout_setup.method == "stripe":
        if not payout_setup.stripe_account_id:
            raise HTTPException(status_code=400, detail="Stripe account ID required")
        update_data["stripe_account_id"] = payout_setup.stripe_account_id
    
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": update_data}
    )
    
    return {"message": "Payout method set successfully"}

@api_router.post("/users/me/request-payout")
async def request_payout(request: Request, payout_req: PayoutRequest):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Refresh user data
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check KYC verification
    if not user_doc.get("kyc_verified"):
        raise HTTPException(status_code=400, detail="KYC verification required")
    
    # Check payout method
    if not user_doc.get("payout_method"):
        raise HTTPException(status_code=400, detail="Please set up a payout method first")
    
    # Check minimum threshold
    min_threshold = float(os.environ.get('MIN_PAYOUT_THRESHOLD_EUR', '20.0'))
    if payout_req.amount_eur < min_threshold:
        raise HTTPException(status_code=400, detail=f"Minimum payout is €{min_threshold}")
    
    # Check available balance
    available_balance = user_doc.get("earnings_eur", 0.0)
    if payout_req.amount_eur > available_balance:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Create payout record
    payout_id = f"payout_{uuid.uuid4().hex[:12]}"
    payout = Payout(
        payout_id=payout_id,
        user_id=user.user_id,
        amount_eur=payout_req.amount_eur,
        method=user_doc["payout_method"],
        status="pending",
        payout_email=user_doc.get("payout_email")
    )
    
    payout_dict = payout.model_dump()
    payout_dict["created_at"] = payout_dict["created_at"].isoformat()
    await db.payouts.insert_one(payout_dict)
    
    # Deduct from user balance (escrow until payout completes)
    new_balance = available_balance - payout_req.amount_eur
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"earnings_eur": new_balance}}
    )
    
    return {
        "message": "Payout requested successfully",
        "payout_id": payout_id,
        "status": "pending"
    }

@api_router.get("/users/me/payouts")
async def get_my_payouts(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payouts = await db.payouts.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for payout in payouts:
        if isinstance(payout["created_at"], str):
            payout["created_at"] = datetime.fromisoformat(payout["created_at"])
        if payout.get("completed_at") and isinstance(payout["completed_at"], str):
            payout["completed_at"] = datetime.fromisoformat(payout["completed_at"])
    
    return payouts

# Collaboration endpoints
@api_router.post("/collaborations/send")
async def send_collaboration_request(request: Request, collab_req: CollaborationRequest):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if target user exists
    to_user = await db.users.find_one({"user_id": collab_req.to_user_id}, {"_id": 0})
    if not to_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create collaboration message
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    collab_message = CollaborationMessage(
        message_id=message_id,
        from_user_id=user.user_id,
        from_user_name=user.name,
        from_user_picture=user.picture,
        to_user_id=collab_req.to_user_id,
        subject=collab_req.subject,
        message=collab_req.message
    )
    
    message_dict = collab_message.model_dump()
    message_dict["created_at"] = message_dict["created_at"].isoformat()
    await db.collaboration_messages.insert_one(message_dict)
    
    return {"message": "Collaboration request sent successfully", "message_id": message_id}

@api_router.get("/collaborations/inbox")
async def get_collaboration_inbox(request: Request):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    messages = await db.collaboration_messages.find(
        {"to_user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    for msg in messages:
        if isinstance(msg["created_at"], str):
            msg["created_at"] = datetime.fromisoformat(msg["created_at"])
    
    return messages

@api_router.patch("/collaborations/{message_id}/read")
async def mark_message_read(request: Request, message_id: str):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await db.collaboration_messages.update_one(
        {"message_id": message_id, "to_user_id": user.user_id},
        {"$set": {"read": True}}
    )
    
    return {"message": "Message marked as read"}

@api_router.post("/collaborations/{message_id}/accept")
async def accept_collaboration(request: Request, message_id: str):
    """Accept a collaboration request"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.collaboration_messages.update_one(
        {"message_id": message_id, "to_user_id": user.user_id},
        {"$set": {"status": "accepted", "accepted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    
    return {"message": "Collaboration accepted"}

@api_router.post("/collaborations/{message_id}/decline")
async def decline_collaboration(request: Request, message_id: str):
    """Decline a collaboration request"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.collaboration_messages.update_one(
        {"message_id": message_id, "to_user_id": user.user_id},
        {"$set": {"status": "declined"}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    
    return {"message": "Collaboration declined"}

@api_router.get("/collaborations/accepted")
async def get_accepted_collaborations(request: Request):
    """Get user's accepted collaborations to show on profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get both sent and received accepted collaborations
    collaborations = await db.collaboration_messages.find(
        {
            "$or": [
                {"to_user_id": user.user_id, "status": "accepted"},
                {"from_user_id": user.user_id, "status": "accepted"}
            ]
        },
        {"_id": 0}
    ).sort("accepted_at", -1).to_list(20)
    
    return {"collaborations": collaborations}

# AI-powered collaboration analysis endpoints
@api_router.post("/collaborations/ai/analyze")
async def analyze_collaboration(request: Request, analysis_req: AIAnalysisRequest):
    """AI-powered analysis of collaboration request - generates summary and key insights"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"collab_analyze_{user.user_id}_{uuid.uuid4().hex[:8]}",
            system_message="""You are a professional collaboration assistant for Looksy, a fashion social media platform.
Analyze collaboration requests and provide concise, actionable insights.
Keep responses brief and professional. Focus on the key points."""
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze this collaboration request and provide:
1. A brief summary (1-2 sentences)
2. Request type (Brand Partnership, Influencer Collab, Editorial, Photo Shoot, or General)
3. Priority level (High/Medium/Low) based on content
4. Key action items (2-3 bullet points)

From: {analysis_req.from_user_name}
Subject: {analysis_req.subject}
Message: {analysis_req.message}

Respond in JSON format:
{{"summary": "...", "request_type": "...", "priority": "...", "action_items": ["...", "..."]}}"""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse the JSON response
        import json
        try:
            # Try to extract JSON from the response
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            result = json.loads(response_text)
        except:
            result = {
                "summary": response[:200] if len(response) > 200 else response,
                "request_type": "General",
                "priority": "Medium",
                "action_items": ["Review the collaboration request", "Consider your availability"]
            }
        
        return result
        
    except Exception as e:
        logger.error(f"AI analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@api_router.post("/collaborations/ai/suggest-reply")
async def suggest_reply(request: Request, reply_req: AIReplyRequest):
    """AI-powered reply suggestion for collaboration requests"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    tone_instructions = {
        "professional": "formal and businesslike",
        "friendly": "warm and approachable while still professional",
        "brief": "short and to the point"
    }
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"collab_reply_{user.user_id}_{uuid.uuid4().hex[:8]}",
            system_message=f"""You are a collaboration assistant for {user.name}, a fashion content creator on Looksy.
Generate reply suggestions that are {tone_instructions.get(reply_req.reply_tone, 'professional')}.
Keep replies concise and actionable."""
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Generate 3 different reply options for this collaboration request.
The replies should be {tone_instructions.get(reply_req.reply_tone, 'professional')}.

Original Request:
From: {reply_req.from_user_name}
Subject: {reply_req.subject}
Message: {reply_req.message}

Provide 3 replies in JSON format:
{{"replies": [
    {{"type": "accept", "text": "..."}},
    {{"type": "interested", "text": "..."}},
    {{"type": "decline", "text": "..."}}
]}}"""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        # Parse the JSON response
        import json
        try:
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            result = json.loads(response_text)
        except:
            result = {
                "replies": [
                    {"type": "accept", "text": f"Hi {reply_req.from_user_name}! Thank you for reaching out. I'd love to collaborate with you on this project. Let's discuss the details further."},
                    {"type": "interested", "text": f"Hi {reply_req.from_user_name}, thank you for your interest in collaborating. Could you share more details about the timeline and expectations?"},
                    {"type": "decline", "text": f"Hi {reply_req.from_user_name}, thank you for thinking of me for this opportunity. Unfortunately, I'm unable to take on new collaborations at this time."}
                ]
            }
        
        return result
        
    except Exception as e:
        logger.error(f"AI reply suggestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI reply suggestion failed: {str(e)}")

@api_router.post("/collaborations/ai/batch-analyze")
async def batch_analyze_collaborations(request: Request):
    """Analyze all unread collaboration requests for a user"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get unread messages
    messages = await db.collaboration_messages.find(
        {"to_user_id": user.user_id, "read": False},
        {"_id": 0}
    ).to_list(10)  # Limit to 10 for performance
    
    if not messages:
        return {"analyses": [], "summary": "No unread collaboration requests"}
    
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="AI service not configured")
    
    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"collab_batch_{user.user_id}_{uuid.uuid4().hex[:8]}",
            system_message="""You are a collaboration assistant. Provide brief summaries and prioritization."""
        ).with_model("openai", "gpt-4o-mini")
        
        # Create a summary of all messages
        messages_text = "\n\n".join([
            f"Request {i+1}:\nFrom: {m['from_user_name']}\nSubject: {m['subject']}\nMessage: {m['message']}"
            for i, m in enumerate(messages)
        ])
        
        prompt = f"""Analyze these {len(messages)} collaboration requests and provide:
1. An overall summary
2. Which ones are high priority
3. Recommended order to respond

{messages_text}

Respond in JSON:
{{"overall_summary": "...", "high_priority_count": N, "recommendations": ["..."]}}"""

        user_message = UserMessage(text=prompt)
        response = await chat.send_message(user_message)
        
        import json
        try:
            response_text = response.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            result = json.loads(response_text)
        except:
            result = {
                "overall_summary": f"You have {len(messages)} unread collaboration requests to review.",
                "high_priority_count": 0,
                "recommendations": ["Review each request individually"]
            }
        
        result["total_unread"] = len(messages)
        return result
        
    except Exception as e:
        logger.error(f"AI batch analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI batch analysis failed: {str(e)}")

# ================= FAVORITES FEATURE =================

@api_router.post("/posts/{post_id}/favorite")
async def toggle_favorite(request: Request, post_id: str):
    """Add or remove a post from user's favorites"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check if post exists
    post = await db.posts.find_one({"post_id": post_id, "is_deleted": False}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get current favorites
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "favorited_posts": 1})
    favorites = user_doc.get("favorited_posts", []) if user_doc else []
    
    if post_id in favorites:
        # Remove from favorites
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$pull": {"favorited_posts": post_id}}
        )
        return {"message": "Removed from favorites", "is_favorited": False}
    else:
        # Add to favorites
        await db.users.update_one(
            {"user_id": user.user_id},
            {"$addToSet": {"favorited_posts": post_id}}
        )
        return {"message": "Added to favorites", "is_favorited": True}

@api_router.get("/users/me/favorites")
async def get_my_favorites(request: Request):
    """Get current user's favorited posts"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get user's favorited post IDs
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "favorited_posts": 1})
    favorite_ids = user_doc.get("favorited_posts", []) if user_doc else []
    
    if not favorite_ids:
        return {"favorites": [], "count": 0}
    
    # Fetch the posts
    posts = await db.posts.find(
        {"post_id": {"$in": favorite_ids}, "is_deleted": False},
        {"_id": 0}
    ).to_list(100)
    
    # Add user info to each post
    for post in posts:
        owner = await db.users.find_one({"user_id": post["user_id"]}, {"_id": 0, "name": 1, "picture": 1})
        if owner:
            post["user_name"] = owner.get("name", "Unknown")
            post["user_picture"] = owner.get("picture")
        post["is_favorited"] = True
    
    return {"favorites": posts, "count": len(posts)}

# ================= STARS TO PAYOUT POINTS CONVERSION =================

@api_router.get("/rewards/info")
async def get_rewards_info(request: Request):
    """Get current user's rewards information"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_doc = await db.users.find_one(
        {"user_id": user.user_id},
        {"_id": 0, "stars": 1, "payout_points": 1, "earnings": 1, "earnings_eur": 1, "kyc_verified": 1, "payout_method": 1}
    )
    
    stars = user_doc.get("stars", 0) if user_doc else 0
    payout_points = user_doc.get("payout_points", 0.0) if user_doc else 0.0
    earnings = user_doc.get("earnings", 0.0) if user_doc else 0.0
    earnings_eur = user_doc.get("earnings_eur", 0.0) if user_doc else 0.0
    
    # Calculate potential conversion value
    potential_value = calculate_payout_points(stars)
    
    # Min payout threshold
    min_threshold = float(os.environ.get('MIN_PAYOUT_THRESHOLD_EUR', '20.0'))
    
    return {
        "stars": stars,
        "payout_points_usd": payout_points,
        "payout_points_eur": usd_to_eur(payout_points),
        "earnings_usd": earnings,
        "earnings_eur": earnings_eur,
        "potential_conversion_value_usd": potential_value,
        "potential_conversion_value_eur": usd_to_eur(potential_value),
        "kyc_verified": user_doc.get("kyc_verified", False) if user_doc else False,
        "payout_method": user_doc.get("payout_method") if user_doc else None,
        "min_payout_threshold_eur": min_threshold,
        "can_request_payout": payout_points >= min_threshold,
        "conversion_rates": {
            "tier1": {"range": "1-1000 stars", "rate_usd": 0.0005, "rate_cents": 0.05},
            "tier2": {"range": "1001-5000 stars", "rate_usd": 0.001, "rate_cents": 0.10},
            "tier3": {"range": "5001-10000 stars", "rate_usd": 0.002, "rate_cents": 0.20},
            "max_stars_per_post": 10000
        }
    }

@api_router.post("/rewards/convert-stars")
async def convert_stars_to_points(request: Request, convert_req: ConvertStarsRequest):
    """Convert accumulated stars to payout points"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "stars": 1, "payout_points": 1})
    current_stars = user_doc.get("stars", 0) if user_doc else 0
    
    if convert_req.stars_to_convert <= 0:
        raise HTTPException(status_code=400, detail="Stars to convert must be greater than 0")
    
    if convert_req.stars_to_convert > current_stars:
        raise HTTPException(status_code=400, detail=f"Insufficient stars. You have {current_stars} stars.")
    
    # Calculate payout points value
    points_value = calculate_payout_points(convert_req.stars_to_convert)
    
    # Update user's stars and payout points
    await db.users.update_one(
        {"user_id": user.user_id},
        {
            "$inc": {
                "stars": -convert_req.stars_to_convert,
                "payout_points": points_value
            }
        }
    )
    
    # Get updated values
    updated_user = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "stars": 1, "payout_points": 1})
    
    return {
        "message": "Stars converted successfully",
        "stars_converted": convert_req.stars_to_convert,
        "points_earned_usd": points_value,
        "points_earned_eur": usd_to_eur(points_value),
        "remaining_stars": updated_user.get("stars", 0),
        "total_payout_points_usd": updated_user.get("payout_points", 0.0),
        "total_payout_points_eur": usd_to_eur(updated_user.get("payout_points", 0.0))
    }

# ================= KYC VERIFICATION =================

class KYCSubmission(BaseModel):
    full_name: str
    date_of_birth: str
    address: str
    country: str
    id_type: str  # "passport", "id_card", "drivers_license"
    id_number: str

@api_router.post("/kyc/submit")
async def submit_kyc(request: Request, kyc_data: KYCSubmission):
    """Submit KYC verification documents"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Store KYC data (in production, this would go through a proper KYC provider)
    kyc_record = {
        "full_name": kyc_data.full_name,
        "date_of_birth": kyc_data.date_of_birth,
        "address": kyc_data.address,
        "country": kyc_data.country,
        "id_type": kyc_data.id_type,
        "id_number": kyc_data.id_number[-4:] + "****",  # Mask for security
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
    }
    
    # For demo purposes, auto-approve KYC
    await db.users.update_one(
        {"user_id": user.user_id},
        {
            "$set": {
                "kyc_verified": True,
                "kyc_documents": kyc_record
            }
        }
    )
    
    return {
        "message": "KYC submitted and verified successfully",
        "kyc_verified": True
    }

@api_router.get("/kyc/status")
async def get_kyc_status(request: Request):
    """Get KYC verification status"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user_doc = await db.users.find_one(
        {"user_id": user.user_id},
        {"_id": 0, "kyc_verified": 1, "kyc_documents": 1}
    )
    
    return {
        "kyc_verified": user_doc.get("kyc_verified", False) if user_doc else False,
        "kyc_status": user_doc.get("kyc_documents", {}).get("status", "not_submitted") if user_doc and user_doc.get("kyc_documents") else "not_submitted"
    }

# ================= STRIPE PAYOUT INTEGRATION =================

@api_router.post("/payout/stripe/setup")
async def setup_stripe_payout(request: Request, payout_req: StripePayoutRequest):
    """Setup Stripe payout - creates a checkout session for the user to add their bank details"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check KYC
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "kyc_verified": 1, "payout_points": 1})
    if not user_doc or not user_doc.get("kyc_verified"):
        raise HTTPException(status_code=400, detail="KYC verification required before payout")
    
    # Check minimum threshold (€20)
    min_threshold = float(os.environ.get('MIN_PAYOUT_THRESHOLD_EUR', '20.0'))
    payout_points = user_doc.get("payout_points", 0.0)
    payout_points_eur = usd_to_eur(payout_points)
    
    if payout_req.amount_eur > payout_points_eur:
        raise HTTPException(status_code=400, detail=f"Insufficient payout points. You have €{payout_points_eur:.2f}")
    
    if payout_req.amount_eur < min_threshold:
        raise HTTPException(status_code=400, detail=f"Minimum payout amount is €{min_threshold}")
    
    # Set user's payout method to Stripe
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"payout_method": "stripe"}}
    )
    
    # Create a pending payout transaction
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    transaction = PaymentTransaction(
        transaction_id=transaction_id,
        user_id=user.user_id,
        session_id=f"payout_{transaction_id}",
        amount=payout_req.amount_eur,
        currency="EUR",
        payment_type="payout",
        payment_method="stripe",
        payment_status="pending"
    )
    
    tx_dict = transaction.model_dump()
    tx_dict["created_at"] = tx_dict["created_at"].isoformat()
    await db.payment_transactions.insert_one(tx_dict)
    
    # Deduct payout points
    amount_usd = payout_req.amount_eur / float(os.environ.get('USD_TO_EUR_RATE', '0.92'))
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$inc": {"payout_points": -amount_usd}}
    )
    
    # Mark transaction as completed (in production, would process actual Stripe payout)
    await db.payment_transactions.update_one(
        {"transaction_id": transaction_id},
        {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": "Stripe payout initiated successfully",
        "transaction_id": transaction_id,
        "amount_eur": payout_req.amount_eur,
        "status": "completed",
        "note": "In production, funds would be transferred to your Stripe account"
    }

# ================= PAYPAL PAYOUT INTEGRATION =================

@api_router.post("/payout/paypal/setup")
async def setup_paypal_payout(request: Request, payout_req: PayPalPayoutRequest):
    """Setup PayPal payout - sends funds to user's PayPal email"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Check KYC
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0, "kyc_verified": 1, "payout_points": 1})
    if not user_doc or not user_doc.get("kyc_verified"):
        raise HTTPException(status_code=400, detail="KYC verification required before payout")
    
    # Check minimum threshold (€20)
    min_threshold = float(os.environ.get('MIN_PAYOUT_THRESHOLD_EUR', '20.0'))
    payout_points = user_doc.get("payout_points", 0.0)
    payout_points_eur = usd_to_eur(payout_points)
    
    if payout_req.amount_eur > payout_points_eur:
        raise HTTPException(status_code=400, detail=f"Insufficient payout points. You have €{payout_points_eur:.2f}")
    
    if payout_req.amount_eur < min_threshold:
        raise HTTPException(status_code=400, detail=f"Minimum payout amount is €{min_threshold}")
    
    # Set user's payout method and email
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"payout_method": "paypal", "payout_email": payout_req.paypal_email}}
    )
    
    # Create a payout transaction
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    transaction = PaymentTransaction(
        transaction_id=transaction_id,
        user_id=user.user_id,
        session_id=f"payout_{transaction_id}",
        amount=payout_req.amount_eur,
        currency="EUR",
        payment_type="payout",
        payment_method="paypal",
        payment_status="pending",
        metadata={"paypal_email": payout_req.paypal_email}
    )
    
    tx_dict = transaction.model_dump()
    tx_dict["created_at"] = tx_dict["created_at"].isoformat()
    await db.payment_transactions.insert_one(tx_dict)
    
    # Deduct payout points
    amount_usd = payout_req.amount_eur / float(os.environ.get('USD_TO_EUR_RATE', '0.92'))
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$inc": {"payout_points": -amount_usd}}
    )
    
    # Mark transaction as completed (in production, would call PayPal Payouts API)
    await db.payment_transactions.update_one(
        {"transaction_id": transaction_id},
        {"$set": {"payment_status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {
        "message": "PayPal payout initiated successfully",
        "transaction_id": transaction_id,
        "amount_eur": payout_req.amount_eur,
        "paypal_email": payout_req.paypal_email,
        "status": "completed",
        "note": "In production, funds would be transferred to your PayPal account"
    }

@api_router.get("/payout/history")
async def get_payout_history(request: Request):
    """Get user's payout transaction history"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    transactions = await db.payment_transactions.find(
        {"user_id": user.user_id, "payment_type": "payout"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return {"transactions": transactions, "count": len(transactions)}

# ================= STRIPE WEBHOOK =================

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    try:
        body = await request.body()
        signature = request.headers.get("Stripe-Signature")
        
        stripe_api_key = os.environ.get('STRIPE_API_KEY')
        if not stripe_api_key:
            raise HTTPException(status_code=500, detail="Stripe not configured")
        
        # Process webhook (in production, verify signature and handle events)
        logger.info(f"Received Stripe webhook")
        
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    sync_client.close()