"""
Live Payout Providers for Looksy: Stripe Connect Express + PayPal Payouts.

Each provider checks for properly-formatted credentials on init.
If keys are placeholders (e.g. "sk_test_emergent"), endpoints will return
a clear "provider not configured" error rather than silently calling out.
"""

import os
import json
import uuid
import logging
import httpx
import stripe
from datetime import datetime, timezone
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


def _looks_like_real_stripe_key(key: Optional[str]) -> bool:
    return bool(key and (key.startswith("sk_live_") or key.startswith("sk_test_")) and key != "sk_test_emergent")


def _looks_like_real_paypal_creds(client_id: Optional[str], secret: Optional[str]) -> bool:
    placeholders = {"sandbox_client_id", "sandbox_client_secret", "", None}
    if client_id in placeholders or secret in placeholders:
        return False
    # PayPal IDs are typically 80+ chars
    return len(client_id) > 20 and len(secret) > 20


class StripeConnectProvider:
    """Stripe Connect Express: hosted onboarding + EUR transfers to creators."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.api_key = os.environ.get("STRIPE_API_KEY")
        self.webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        self.return_url = os.environ.get(
            "STRIPE_RETURN_URL",
            f"{os.environ.get('FRONTEND_URL', '')}/payouts?stripe=success",
        )
        self.refresh_url = os.environ.get(
            "STRIPE_REFRESH_URL",
            f"{os.environ.get('FRONTEND_URL', '')}/payouts?stripe=refresh",
        )
        self.configured = _looks_like_real_stripe_key(self.api_key)
        if self.configured:
            stripe.api_key = self.api_key
            logger.info("Stripe Connect provider configured")
        else:
            logger.warning("Stripe Connect provider NOT configured (placeholder key)")

    def _require_configured(self):
        if not self.configured:
            raise RuntimeError(
                "Stripe Connect is not configured. Set STRIPE_API_KEY (sk_live_... or sk_test_...) in /app/backend/.env"
            )

    async def create_express_account(self, user_id: str, email: str, country: str = "DE") -> Dict:
        """Create an Express connected account and store the account_id on the user."""
        self._require_configured()

        existing = await self.db.users.find_one(
            {"user_id": user_id}, {"_id": 0, "stripe_account_id": 1}
        )
        if existing and existing.get("stripe_account_id"):
            return {"stripe_account_id": existing["stripe_account_id"], "existing": True}

        account = stripe.Account.create(
            type="express",
            country=country,
            email=email,
            capabilities={
                "transfers": {"requested": True},
            },
            business_type="individual",
        )

        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "stripe_account_id": account.id,
                "stripe_charges_enabled": False,
                "stripe_payouts_enabled": False,
                "stripe_details_submitted": False,
            }},
        )
        return {"stripe_account_id": account.id, "existing": False}

    async def create_onboarding_link(self, user_id: str) -> str:
        self._require_configured()
        user = await self.db.users.find_one(
            {"user_id": user_id}, {"_id": 0, "stripe_account_id": 1}
        )
        if not user or not user.get("stripe_account_id"):
            raise ValueError("No Stripe account on file. Create one first.")

        link = stripe.AccountLink.create(
            account=user["stripe_account_id"],
            refresh_url=self.refresh_url,
            return_url=self.return_url,
            type="account_onboarding",
        )
        return link.url

    async def get_account_status(self, user_id: str) -> Dict:
        self._require_configured()
        user = await self.db.users.find_one(
            {"user_id": user_id}, {"_id": 0, "stripe_account_id": 1}
        )
        if not user or not user.get("stripe_account_id"):
            return {"connected": False}

        account = stripe.Account.retrieve(user["stripe_account_id"])
        status = {
            "connected": True,
            "stripe_account_id": account.id,
            "charges_enabled": bool(account.charges_enabled),
            "payouts_enabled": bool(account.payouts_enabled),
            "details_submitted": bool(account.details_submitted),
            "requirements": (account.requirements.currently_due or []) if account.requirements else [],
        }
        await self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "stripe_charges_enabled": status["charges_enabled"],
                "stripe_payouts_enabled": status["payouts_enabled"],
                "stripe_details_submitted": status["details_submitted"],
            }},
        )
        return status

    async def create_transfer(self, user_id: str, amount_eur: float, description: str = "Looksy creator payout") -> Dict:
        """Move EUR from platform balance to the creator's connected account."""
        self._require_configured()
        user = await self.db.users.find_one(
            {"user_id": user_id}, {"_id": 0, "stripe_account_id": 1, "stripe_payouts_enabled": 1}
        )
        if not user or not user.get("stripe_account_id"):
            raise ValueError("User has no Stripe Connect account")
        if not user.get("stripe_payouts_enabled"):
            raise ValueError("Stripe onboarding incomplete (payouts disabled)")

        amount_cents = int(round(amount_eur * 100))
        transfer = stripe.Transfer.create(
            amount=amount_cents,
            currency="eur",
            destination=user["stripe_account_id"],
            description=description,
        )
        return {
            "transfer_id": transfer.id,
            "amount_eur": amount_eur,
            "currency": "eur",
            "status": "created",
        }

    def verify_webhook(self, payload: bytes, signature_header: str) -> Dict:
        self._require_configured()
        if not self.webhook_secret:
            raise RuntimeError("STRIPE_WEBHOOK_SECRET not set")
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature_header,
            secret=self.webhook_secret,
        )
        return event


class PayPalPayoutsProvider:
    """PayPal Payouts API: OAuth2 + batch payouts in EUR."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.client_id = os.environ.get("PAYPAL_CLIENT_ID")
        self.client_secret = os.environ.get("PAYPAL_CLIENT_SECRET")
        self.mode = os.environ.get("PAYPAL_MODE", "sandbox").lower()
        self.webhook_id = os.environ.get("PAYPAL_WEBHOOK_ID")
        self.configured = _looks_like_real_paypal_creds(self.client_id, self.client_secret)
        self._access_token: Optional[str] = None
        if self.configured:
            logger.info(f"PayPal Payouts provider configured ({self.mode})")
        else:
            logger.warning("PayPal Payouts provider NOT configured (placeholder credentials)")

    @property
    def base_url(self) -> str:
        return "https://api-m.paypal.com" if self.mode == "live" else "https://api-m.sandbox.paypal.com"

    def _require_configured(self):
        if not self.configured:
            raise RuntimeError(
                "PayPal Payouts is not configured. Set PAYPAL_CLIENT_ID + PAYPAL_CLIENT_SECRET in /app/backend/.env"
            )

    async def _get_token(self) -> str:
        # Always fetch fresh on first call (simple impl; tokens last ~9h)
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            self._access_token = resp.json()["access_token"]
            return self._access_token

    async def create_payout(self, user_id: str, email: str, amount_eur: float, note: str = "Looksy payout") -> Dict:
        self._require_configured()
        token = await self._get_token()
        batch_id = f"looksy-{uuid.uuid4().hex[:16]}"
        body = {
            "sender_batch_header": {
                "sender_batch_id": batch_id,
                "recipient_type": "EMAIL",
                "email_subject": "You have a Looksy payout!",
                "email_message": "Your Looksy earnings have been paid out. Thank you for creating!",
            },
            "items": [{
                "recipient_type": "EMAIL",
                "amount": {"value": f"{amount_eur:.2f}", "currency": "EUR"},
                "receiver": email,
                "note": note,
                "sender_item_id": f"looksy-{user_id}-{uuid.uuid4().hex[:8]}",
            }],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/payments/payouts",
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code != 201:
            raise RuntimeError(f"PayPal payout failed: {resp.status_code} {resp.text}")

        data = resp.json()
        batch_header = data.get("batch_header", {})
        return {
            "payout_batch_id": batch_header.get("payout_batch_id"),
            "batch_status": batch_header.get("batch_status"),
            "sender_batch_id": batch_id,
        }

    async def get_payout_status(self, payout_batch_id: str) -> Dict:
        self._require_configured()
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{self.base_url}/v1/payments/payouts/{payout_batch_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        if resp.status_code != 200:
            raise RuntimeError(f"PayPal status failed: {resp.status_code} {resp.text}")
        return resp.json()

    async def verify_webhook(self, headers: Dict[str, str], body_str: str) -> bool:
        """Call PayPal's verify-webhook-signature API to validate event authenticity."""
        if not self.webhook_id:
            logger.warning("PAYPAL_WEBHOOK_ID not set — skipping verification")
            return False
        self._require_configured()
        token = await self._get_token()
        verify_body = {
            "auth_algo": headers.get("paypal-auth-algo") or headers.get("PAYPAL-AUTH-ALGO"),
            "cert_url": headers.get("paypal-cert-url") or headers.get("PAYPAL-CERT-URL"),
            "transmission_id": headers.get("paypal-transmission-id") or headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_sig": headers.get("paypal-transmission-sig") or headers.get("PAYPAL-TRANSMISSION-SIG"),
            "transmission_time": headers.get("paypal-transmission-time") or headers.get("PAYPAL-TRANSMISSION-TIME"),
            "webhook_id": self.webhook_id,
            "webhook_event": json.loads(body_str),
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/notifications/verify-webhook-signature",
                json=verify_body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            return False
        return resp.json().get("verification_status") == "SUCCESS"
