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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
    picture: Optional[str] = None
    category: Optional[str] = None  # "men", "women", or None
    earnings: float = 0.0
    earnings_eur: float = 0.0
    kyc_verified: bool = False
    kyc_documents: Optional[dict] = None
    payout_method: Optional[str] = None  # "paypal" or "stripe"
    payout_email: Optional[str] = None
    stripe_account_id: Optional[str] = None
    starred_posts: List[str] = []
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
async def update_user(request: Request, category: Optional[str] = None):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if category and category not in ["men", "women"]:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"category": category}}
    )
    
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    return User(**user_doc)

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
        users = await db.users.find({" category": category}, {"user_id": 1, "_id": 0}).to_list(1000)
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
    posts = await db.posts.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for post in posts:
        if isinstance(post["created_at"], str):
            post["created_at"] = datetime.fromisoformat(post["created_at"])
    
    return posts

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