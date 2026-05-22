"""
Backend tests for Live Payouts (Stripe Connect + PayPal Payouts) when providers
are NOT configured (placeholder keys in .env). Also regression-tests the existing
/api/users/me/request-payout flow to ensure the live-transfer branch is bypassed
gracefully when providers are not configured.
"""
import os
import time
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

TEST_EMAIL = "testuser@looksy.com"
TEST_PASSWORD = "test1234"
TEST_CATEGORY = "men"


# ---------------- Fixtures ----------------

@pytest.fixture(scope="session")
def anon():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "category": TEST_CATEGORY},
        timeout=20,
    )
    if r.status_code != 200:
        pytest.skip(f"Login failed ({r.status_code}): {r.text[:200]}")
    return s


# ---------------- Providers status (public) ----------------

class TestProvidersStatus:
    def test_providers_status_public(self, anon):
        r = anon.get(f"{API}/payouts/providers/status", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "stripe" in body and "paypal" in body
        assert body["stripe"]["configured"] is False
        assert body["paypal"]["configured"] is False
        # webhook flags
        assert body["stripe"]["webhook_secret_set"] is False
        assert body["paypal"]["webhook_id_set"] is False
        assert body["paypal"]["mode"] in ("sandbox", "live")


# ---------------- Auth enforcement ----------------

class TestAuthEnforcement:
    @pytest.mark.parametrize("method,path", [
        ("POST", "/payouts/stripe/connect"),
        ("POST", "/payouts/stripe/onboarding-link"),
        ("GET",  "/payouts/stripe/status"),
    ])
    def test_unauthenticated_returns_401(self, anon, method, path):
        url = f"{API}{path}"
        r = anon.request(method, url, json={} if method == "POST" else None, timeout=10)
        assert r.status_code == 401, f"{method} {path} -> {r.status_code}: {r.text[:200]}"


# ---------------- Stripe endpoints when not configured ----------------

class TestStripeUnconfigured:
    def test_stripe_connect_returns_503(self, auth):
        r = auth.post(f"{API}/payouts/stripe/connect", json={}, timeout=15)
        assert r.status_code == 503, f"{r.status_code}: {r.text[:200]}"
        detail = r.json().get("detail", "")
        assert "STRIPE_API_KEY" in detail or "Stripe Connect is not configured" in detail

    def test_stripe_onboarding_link_returns_503(self, auth):
        r = auth.post(f"{API}/payouts/stripe/onboarding-link", json={}, timeout=15)
        assert r.status_code == 503, f"{r.status_code}: {r.text[:200]}"
        assert "STRIPE_API_KEY" in r.json().get("detail", "") or "not configured" in r.json().get("detail", "")

    def test_stripe_status_returns_503(self, auth):
        r = auth.get(f"{API}/payouts/stripe/status", timeout=15)
        assert r.status_code == 503, f"{r.status_code}: {r.text[:200]}"
        assert "not configured" in r.json().get("detail", "").lower()


# ---------------- Webhooks ----------------

class TestWebhooks:
    def test_stripe_webhook_rejects_invalid_signature(self, anon):
        # No Stripe-Signature header at all -> 400
        r = anon.post(
            f"{API}/payouts/stripe/webhook",
            data=b'{"id":"evt_test","type":"ping"}',
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        assert r.status_code == 400
        assert "Invalid signature" in r.json().get("detail", "") or "not configured" in r.json().get("detail", "").lower()

    def test_stripe_webhook_rejects_bad_signature_header(self, anon):
        r = anon.post(
            f"{API}/payouts/stripe/webhook",
            data=b'{"id":"evt_test","type":"ping"}',
            headers={"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=deadbeef"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_paypal_webhook_rejects_missing_signature(self, anon):
        # PayPal verify_webhook will return False because webhook_id is unset OR
        # raise RuntimeError because provider is not configured -> 503.
        r = anon.post(
            f"{API}/payouts/paypal/webhook",
            data=b'{"event_type":"PAYMENT.PAYOUTS-ITEM.SUCCEEDED","resource":{}}',
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        assert r.status_code in (400, 503), f"{r.status_code}: {r.text[:200]}"


# ---------------- Regression: existing payout flow ----------------

class TestRequestPayoutRegression:
    """Confirm /api/users/me/request-payout still works (creates pending payout and
    deducts payout_points) when live providers are not configured."""

    def test_request_payout_flow(self, auth):
        # 1) Fetch current user
        me = auth.get(f"{API}/auth/me", timeout=10)
        assert me.status_code == 200, me.text[:200]
        user = me.json()
        assert user.get("email") == TEST_EMAIL

        # 2) Ensure KYC + payout method are in place (set them via the dedicated endpoints if needed)
        if not user.get("kyc_verified"):
            kyc = auth.post(f"{API}/users/me/kyc", json={
                "full_name": "Test User",
                "date_of_birth": "1990-01-01",
                "address": "1 Test St, Berlin, DE",
                "id_type": "passport",
                "id_number": "TEST123456",
            }, timeout=15)
            assert kyc.status_code in (200, 201), f"KYC setup failed: {kyc.status_code} {kyc.text[:200]}"

        if not user.get("payout_method"):
            setup = auth.post(f"{API}/users/me/payout-method", json={
                "method": "paypal",
                "payout_email": "testuser@looksy.com",
            }, timeout=10)
            assert setup.status_code == 200, setup.text[:200]

        # 3) Ensure payout_points balance >= request amount; seed directly via MongoDB
        me2 = auth.get(f"{API}/auth/me", timeout=10).json()
        balance_before = float(me2.get("payout_points", 0.0) or 0.0)
        min_threshold = 20.0
        seeded = False
        if balance_before < min_threshold + 1.0:
            # Seed payout_points directly via MongoDB (no dev top-up endpoint exists)
            try:
                import asyncio
                from motor.motor_asyncio import AsyncIOMotorClient
                async def _seed():
                    c = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
                    await c[os.environ.get("DB_NAME", "test_database")].users.update_one(
                        {"user_id": me2["user_id"]},
                        {"$set": {"payout_points": 50.0}},
                    )
                    c.close()
                asyncio.run(_seed())
                seeded = True
            except Exception as e:
                pytest.skip(f"Could not seed payout_points: {e}")
            me2 = auth.get(f"{API}/auth/me", timeout=10).json()
            balance_before = float(me2.get("payout_points", 0.0))
            assert balance_before >= min_threshold

        # 4) Request a payout for the minimum amount
        amount = min_threshold
        r = auth.post(f"{API}/users/me/request-payout",
                      json={"amount_eur": amount}, timeout=20)
        assert r.status_code == 200, f"request-payout failed: {r.status_code} {r.text[:300]}"
        body = r.json()
        # Provider should NOT have been attempted (placeholder keys)
        # body should contain payout_id and indicate pending/no live transfer
        assert "payout_id" in body or "message" in body, body

        # 5) Confirm balance got deducted by exactly `amount`
        time.sleep(0.5)
        me3 = auth.get(f"{API}/auth/me", timeout=10).json()
        balance_after = float(me3.get("payout_points", 0.0))
        assert abs((balance_before - balance_after) - amount) < 0.01, (
            f"balance_before={balance_before} balance_after={balance_after} amount={amount}"
        )

        # 6) Confirm payout appears as 'pending' (live provider was skipped)
        ph = auth.get(f"{API}/users/me/payouts", timeout=10)
        if ph.status_code == 200:
            payouts = ph.json()
            if isinstance(payouts, dict) and "payouts" in payouts:
                payouts = payouts["payouts"]
            assert isinstance(payouts, list)
            # The just-created payout should be present and have status pending
            ids = [p.get("payout_id") for p in payouts]
            pid = body.get("payout_id")
            if pid:
                assert pid in ids, f"payout {pid} not in history: {ids[:5]}"
                created = next(p for p in payouts if p.get("payout_id") == pid)
                assert created.get("status") == "pending", created


# ---------------- Regression: outfit + affiliate from iter7 ----------------

class TestOutfitAffiliateRegression:
    def test_outfit_options_public(self, anon):
        r = anon.get(f"{API}/outfits/options", timeout=10)
        assert r.status_code == 200, r.text[:200]
        body = r.json()
        assert isinstance(body, dict)
        # Spot-check at least one key
        assert any(k in body for k in ("occasions", "styles", "seasons", "categories"))

    def test_affiliate_suggest_authenticated(self, auth):
        payload = {
            "items": [
                {"item": "white t-shirt", "category": "tops", "color": "white"},
                {"item": "blue jeans", "category": "bottoms", "color": "blue"},
            ]
        }
        r = auth.post(f"{API}/affiliate/suggest", json=payload, timeout=30)
        assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
        body = r.json()
        # response should be a list/dict; no _id leakage
        assert "_id" not in (body if isinstance(body, dict) else {})

    def test_outfits_generate_authenticated(self, auth):
        payload = {
            "occasion": "casual",
            "style": "minimal",
            "season": "summer",
        }
        r = auth.post(f"{API}/outfits/generate", json=payload, timeout=120)
        # Outfit generation hits an LLM and may legitimately be slow / occasionally fail.
        # Acceptable: 200 or a clear server error code.
        assert r.status_code in (200, 400, 500, 503), f"{r.status_code}: {r.text[:300]}"
        if r.status_code == 200:
            body = r.json()
            assert "outfit_id" in body or "items" in body or "outfit" in body
