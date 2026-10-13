"""Password reset + email verification routes. Emails are MOCKED (logged to console)."""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

import deps

router = APIRouter()
logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

RESET_TTL = timedelta(hours=1)
VERIFY_TTL = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(seconds=60)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


def _dev_mode() -> bool:
    return os.environ.get("AUTH_DEV_MODE", "false").lower() == "true"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _recently_issued(collection, user_id: str) -> bool:
    last = await collection.find_one({"user_id": user_id}, sort=[("created_at", -1)])
    return bool(last) and _now() - _aware(last["created_at"]) < RESEND_COOLDOWN


async def ensure_auth_indexes(db):
    await db.users.create_index("email", unique=True)
    for coll in (db.password_reset_tokens, db.email_verification_tokens):
        await coll.create_index("expires_at", expireAfterSeconds=0)
        await coll.create_index("token_hash", unique=True)
        await coll.create_index("user_id")


async def issue_email_verification(user_id: str, email: str) -> str:
    token = secrets.token_urlsafe(32)
    await deps.db.email_verification_tokens.delete_many({"user_id": user_id})
    await deps.db.email_verification_tokens.insert_one({
        "token_hash": _hash(token),
        "user_id": user_id,
        "email": email,
        "created_at": _now(),
        "expires_at": _now() + VERIFY_TTL,
    })
    link = f"{os.environ['FRONTEND_URL']}/verify-email?token={token}"
    logger.info(f"[MOCK EMAIL] Verify email for {email}: {link}")
    return link


@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    email = payload.email.lower()
    response = {"message": "If an account exists for that email, a reset link has been sent."}
    user = await deps.db.users.find_one({"email": email}, {"_id": 0, "user_id": 1})
    if not user or await _recently_issued(deps.db.password_reset_tokens, user["user_id"]):
        return response

    token = secrets.token_urlsafe(32)
    await deps.db.password_reset_tokens.update_many(
        {"user_id": user["user_id"], "used": False}, {"$set": {"used": True}}
    )
    await deps.db.password_reset_tokens.insert_one({
        "token_hash": _hash(token),
        "user_id": user["user_id"],
        "used": False,
        "created_at": _now(),
        "expires_at": _now() + RESET_TTL,
    })
    link = f"{os.environ['FRONTEND_URL']}/reset-password?token={token}"
    logger.info(f"[MOCK EMAIL] Password reset for {email}: {link}")
    if _dev_mode():
        response["reset_link"] = link
    return response


@router.post("/auth/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    record = await deps.db.password_reset_tokens.find_one({"token_hash": _hash(payload.token)})
    if not record or record.get("used") or _aware(record["expires_at"]) < _now():
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    user = await deps.db.users.find_one({"user_id": record["user_id"]}, {"_id": 0, "email": 1})
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")

    await deps.db.users.update_one(
        {"user_id": record["user_id"]},
        {"$set": {
            "password_hash": pwd_context.hash(payload.new_password),
            "email_verified": True,
            "password_changed_at": _now().isoformat(),
        }},
    )
    await deps.db.password_reset_tokens.update_one({"_id": record["_id"]}, {"$set": {"used": True}})
    await deps.db.user_sessions.delete_many({"user_id": record["user_id"]})
    if deps.security_manager:
        await deps.security_manager.clear_login_attempts(user["email"])
    return {"message": "Password updated. Please sign in with your new password."}


@router.post("/auth/verify-email")
async def verify_email(payload: VerifyEmailRequest):
    record = await deps.db.email_verification_tokens.find_one({"token_hash": _hash(payload.token)})
    if not record or _aware(record["expires_at"]) < _now():
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")

    await deps.db.users.update_one(
        {"user_id": record["user_id"]},
        {"$set": {"email_verified": True, "email_verified_at": _now().isoformat()}},
    )
    await deps.db.email_verification_tokens.delete_many({"user_id": record["user_id"]})
    return {"verified": True, "email": record["email"]}


@router.post("/auth/resend-verification")
async def resend_verification(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if user.email_verified is not False:
        return {"message": "Your email is already verified.", "already_verified": True}
    if await _recently_issued(deps.db.email_verification_tokens, user.user_id):
        raise HTTPException(status_code=429, detail="Please wait a minute before requesting another email.")

    link = await issue_email_verification(user.user_id, user.email)
    response = {"message": "Verification email sent."}
    if _dev_mode():
        response["verification_link"] = link
    return response
