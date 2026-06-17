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
    elif event_type == "payout.failed":
        await deps.db.payouts.update_many(
            {"stripe_transfer_id": data.get("id")},
            {"$set": {
                "status": "failed",
                "failure_message": data.get("failure_message"),
            }},
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
    elif event_type == "PAYMENT.PAYOUTS-ITEM.FAILED":
        await deps.db.payouts.update_many(
            {"paypal_batch_id": resource.get("payout_batch_id")},
            {"$set": {"status": "failed", "failure_message": resource.get("errors")}},
        )
    return {"received": True}
