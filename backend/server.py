from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import secrets
import io
from bson import ObjectId
import gridfs
import pymongo
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage

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

# Helper function to convert USD to EUR
def usd_to_eur(usd_amount: float) -> float:
    rate = float(os.environ.get('USD_TO_EUR_RATE', '0.92'))
    return round(usd_amount * rate, 2)

# Helper function to calculate earnings
def calculate_earnings(likes_count: int) -> float:
    if likes_count < 1000:
        return likes_count * 0.05
    elif likes_count < 3000:
        return 1000 * 0.05 + (likes_count - 1000) * 0.10
    elif likes_count < 10000:
        return 1000 * 0.05 + 2000 * 0.10 + (likes_count - 3000) * 0.20
    else:
        return 1000 * 0.05 + 2000 * 0.10 + 7000 * 0.20 + (likes_count - 10000) * 0.50

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