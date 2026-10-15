"""Live Payouts routes (Stripe Connect Express + PayPal Payouts)."""

import json
import logging
from fastapi import APIRouter, HTTPException, Request

import deps

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/payouts/providers/status")
async def payouts_providers_status():
    """Public: shows which payout providers are configured."""
    return {
        "stripe": {
            "configured": bool(deps.stripe_connect_provider and deps.stripe_connect_provider.configured),
            "webhook_secret_set": bool(
                deps.stripe_connect_provider and deps.stripe_connect_provider.webhook_secret
            ),
        },
        "paypal": {
            "configured": bool(deps.paypal_payouts_provider and deps.paypal_payouts_provider.configured),
            "mode": deps.paypal_payouts_provider.mode if deps.paypal_payouts_provider else None,
            "webhook_id_set": bool(
                deps.paypal_payouts_provider and deps.paypal_payouts_provider.webhook_id
            ),
        },
    }


@router.post("/payouts/stripe/connect")
async def stripe_connect_create(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await deps.stripe_connect_provider.create_express_account(
            user_id=user.user_id, email=user.email
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Stripe account creation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/payouts/stripe/onboarding-link")
async def stripe_connect_onboarding_link(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        url = await deps.stripe_connect_provider.create_onboarding_link(user.user_id)
        return {"url": url}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payouts/stripe/status")
async def stripe_connect_status(request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await deps.stripe_connect_provider.get_account_status(user.user_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


PAYPAL_FAILURE_EVENTS = {
    "PAYMENT.PAYOUTS-ITEM.FAILED", "PAYMENT.PAYOUTS-ITEM.RETURNED", "PAYMENT.PAYOUTS-ITEM.BLOCKED",
    "PAYMENT.PAYOUTS-ITEM.CANCELED", "PAYMENT.PAYOUTS-ITEM.DENIED", "PAYMENT.PAYOUTS-ITEM.REFUNDED",
}
FINAL_FAILED = ["failed", "rejected"]


async def refund_failed_payouts(query: dict, reason: str) -> int:
    """Mark matching payouts failed and give the escrowed balance back exactly once."""
    refunded = 0
    while True:
        payout = await deps.db.payouts.find_one_and_update(
            {**query, "status": {"$nin": FINAL_FAILED}, "refunded": {"$ne": True}},
            {"$set": {"status": "failed", "refunded": True, "failure_message": reason,
                      "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        if not payout:
            return refunded
        await deps.db.users.update_one({"user_id": payout["user_id"]}, {"$inc": {"payout_points": payout["amount_eur"]}})
        logger.info(f"Refunded €{payout['amount_eur']} for failed payout {payout['payout_id']}")
        refunded += 1


@router.post("/payouts/stripe/webhook")
async def stripe_payouts_webhook(request: Request):
    """Stripe webhook for account.updated, payout.paid, payout.failed, transfer.*"""
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = deps.stripe_connect_provider.verify_webhook(payload, sig)
    except RuntimeError as e:
        # Provider not configured — distinguish from a bad signature
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.warning(f"Stripe webhook signature failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event.get("type", "")
    data = event.get("data", {}).get("object", {})
    logger.info(f"Stripe webhook: {event_type}")

    if event_type == "account.updated":
        await deps.db.users.update_many(
            {"stripe_account_id": data.get("id")},
            {"$set": {
                "stripe_charges_enabled": bool(data.get("charges_enabled")),
                "stripe_payouts_enabled": bool(data.get("payouts_enabled")),
                "stripe_details_submitted": bool(data.get("details_submitted")),
            }},
        )
    elif event_type in ("transfer.created", "transfer.paid"):
        await deps.db.payouts.update_many(
            {"stripe_transfer_id": data.get("id")},
            {"$set": {"status": "succeeded" if event_type == "transfer.paid" else "processing"}},
        )
    elif event_type in ("transfer.reversed", "transfer.failed", "payout.failed"):
        await refund_failed_payouts(
            {"stripe_transfer_id": data.get("id")}, data.get("failure_message") or event_type
        )

    return {"received": True}


@router.post("/payouts/paypal/webhook")
async def paypal_payouts_webhook(request: Request):
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        verified = await deps.paypal_payouts_provider.verify_webhook(headers, body_str)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid PayPal webhook signature")

    event = json.loads(body_str)
    event_type = event.get("event_type", "")
    resource = event.get("resource", {})
    logger.info(f"PayPal webhook: {event_type}")

    if event_type == "PAYMENT.PAYOUTS-ITEM.SUCCEEDED":
        await deps.db.payouts.update_many(
            {"paypal_batch_id": resource.get("payout_batch_id")},
            {"$set": {"status": "succeeded"}},
        )
    elif event_type in PAYPAL_FAILURE_EVENTS:
        errors = resource.get("errors")
        await refund_failed_payouts(
            {"paypal_batch_id": resource.get("payout_batch_id")},
            (errors.get("message") if isinstance(errors, dict) else None) or event_type,
        )
    return {"received": True}
