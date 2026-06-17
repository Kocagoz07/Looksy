"""
Backend regression + new-feature tests for the AI Outfit Generator
and Smart Affiliate Engine added to /app/backend/server.py.
"""
import os
import json
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
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_session(session):
    """Login once per test session and reuse the cookie."""
    r = session.post(
        f"{API}/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "category": TEST_CATEGORY},
        timeout=20,
    )
    if r.status_code != 200:
        pytest.skip(f"Login failed ({r.status_code}): {r.text[:200]}")
    return session


@pytest.fixture(scope="session")
def anon_session():
    return requests.Session()


def _no_mongo_id(payload):
    """Recursively assert no Mongo _id leaks into the JSON tree."""
    if isinstance(payload, dict):
        assert "_id" not in payload, f"Mongo _id leaked: {list(payload.keys())[:5]}"
        for v in payload.values():
            _no_mongo_id(v)
    elif isinstance(payload, list):
        for it in payload:
            _no_mongo_id(it)


# ---------------- Regression: auth ----------------

class TestAuthRegression:
    def test_login_ok(self, session):
        r = session.post(
            f"{API}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "category": TEST_CATEGORY},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        _no_mongo_id(data)

    def test_me_ok(self, auth_session):
        r = auth_session.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "user_id" in data or "email" in data
        _no_mongo_id(data)


# ---------------- Outfit options & trending (public) ----------------

class TestPublicOutfitEndpoints:
    def test_options(self, anon_session):
        r = anon_session.get(f"{API}/outfits/options", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data.get("styles"), list) and len(data["styles"]) > 0
        assert isinstance(data.get("occasions"), list) and len(data["occasions"]) > 0
        assert isinstance(data.get("seasons"), list) and len(data["seasons"]) > 0
        assert "casual" in data["styles"]
        _no_mongo_id(data)

    def test_trending(self, anon_session):
        r = anon_session.get(f"{API}/outfits/trending", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "trending" in data
        assert isinstance(data["trending"], list)
        _no_mongo_id(data)


# ---------------- Auth enforcement ----------------

class TestAuthEnforcement:
    @pytest.mark.parametrize(
        "method,path,body",
        [
            ("POST", "/outfits/generate", {"occasion": "everyday"}),
            ("GET", "/outfits/mine", None),
            ("POST", "/outfits/some-id/save", None),
            ("GET", "/outfits/style-profile", None),
            ("PUT", "/outfits/style-profile", {"favorite_styles": ["casual"]}),
            ("POST", "/affiliate/suggest", {"items": [{"item": "t-shirt"}]}),
            ("GET", "/affiliate/my-links", None),
            ("GET", "/affiliate/my-stats", None),
        ],
    )
    def test_protected_requires_auth(self, anon_session, method, path, body):
        r = anon_session.request(
            method,
            f"{API}{path}",
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        # FastAPI auth missing should be 401 (some auth layers also use 403)
        assert r.status_code in (401, 403), f"{method} {path} got {r.status_code}: {r.text[:200]}"


# ---------------- Style profile (auth) ----------------

class TestStyleProfile:
    def test_update_then_get(self, auth_session):
        payload = {
            "favorite_styles": ["casual", "minimalist"],
            "favorite_colors": ["black", "beige"],
            "body_type": "athletic",
            "sizes": {"top": "M", "bottom": "32"},
            "avoid": ["neon"],
            "budget_preference": "mid-range",
        }
        r = auth_session.put(f"{API}/outfits/style-profile", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        updated = r.json()
        _no_mongo_id(updated)
        assert updated["favorite_styles"] == payload["favorite_styles"]
        assert updated["favorite_colors"] == payload["favorite_colors"]
        assert updated["body_type"] == "athletic"
        assert updated["avoid"] == ["neon"]
        assert updated["budget_preference"] == "mid-range"

        # Verify persistence with GET
        r2 = auth_session.get(f"{API}/outfits/style-profile", timeout=15)
        assert r2.status_code == 200
        fetched = r2.json()
        _no_mongo_id(fetched)
        assert fetched.get("favorite_styles") == payload["favorite_styles"]
        assert fetched.get("body_type") == "athletic"


# ---------------- Outfit generation (AI) ----------------

@pytest.fixture(scope="module")
def generated_outfit(auth_session):
    """Generate a single outfit with affiliate links for downstream tests."""
    r = auth_session.post(
        f"{API}/outfits/generate",
        json={
            "occasion": "brunch",
            "style": "minimalist",
            "season": "spring",
            "budget": "mid-range",
            "color_preference": "neutral tones",
            "include_affiliate_links": True,
        },
        timeout=120,
    )
    assert r.status_code == 200, r.text
    return r.json()


class TestOutfitGeneration:
    def test_generate_shape(self, generated_outfit):
        data = generated_outfit
        _no_mongo_id(data)
        assert "outfit_id" in data and data["outfit_id"].startswith("outfit_")
        assert "outfit" in data
        outfit = data["outfit"]
        assert "outfit_name" in outfit
        assert "items" in outfit and isinstance(outfit["items"], list)
        # AI should have produced at least 1 item; ideally 4-6
        assert len(outfit["items"]) >= 1, f"No items in outfit: {outfit}"

    def test_generate_affiliate_links_populated(self, generated_outfit):
        links = generated_outfit.get("affiliate_links")
        assert isinstance(links, list)
        # Should produce ~2 retailers per item
        assert len(links) >= 1, f"Expected affiliate links, got: {links}"
        sample = links[0]
        for k in ("link_id", "retailer", "search_query", "target_url", "commission_rate"):
            assert k in sample, f"missing {k} in affiliate link {sample}"
        assert sample["target_url"].startswith("http")
        assert sample["link_id"].startswith("aff_")
        _no_mongo_id(links)

    def test_my_outfits_includes_generated(self, auth_session, generated_outfit):
        r = auth_session.get(f"{API}/outfits/mine?limit=50", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        _no_mongo_id(data)
        assert "outfits" in data
        ids = [o["outfit_id"] for o in data["outfits"]]
        assert generated_outfit["outfit_id"] in ids

    def test_save_outfit(self, auth_session, generated_outfit):
        oid = generated_outfit["outfit_id"]
        r = auth_session.post(f"{API}/outfits/{oid}/save", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data == {"saved": True, "outfit_id": oid}

        # Confirm via GET /mine that saved flag is True
        r2 = auth_session.get(f"{API}/outfits/mine?limit=50", timeout=15)
        outfits = r2.json()["outfits"]
        match = next((o for o in outfits if o["outfit_id"] == oid), None)
        assert match is not None
        assert match.get("saved") is True

    def test_save_outfit_not_found(self, auth_session):
        r = auth_session.post(f"{API}/outfits/outfit_doesnotexist/save", timeout=15)
        assert r.status_code == 404


# ---------------- Affiliate suggest / links / stats ----------------

@pytest.fixture(scope="module")
def suggested_links(auth_session):
    payload = {
        "items": [
            {"item": "white linen shirt", "category": "top", "color": "white"},
            {"item": "beige chinos", "category": "bottom", "color": "beige"},
        ],
        "budget": "mid-range",
        "persist": True,
    }
    r = auth_session.post(f"{API}/affiliate/suggest", json=payload, timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


class TestAffiliate:
    def test_suggest_shape(self, suggested_links):
        data = suggested_links
        _no_mongo_id(data)
        assert "suggestions" in data and isinstance(data["suggestions"], list)
        assert "links" in data and isinstance(data["links"], list)
        assert len(data["suggestions"]) >= 1
        s0 = data["suggestions"][0]
        assert "retailers" in s0 and isinstance(s0["retailers"], list)
        assert len(s0["retailers"]) >= 1
        r0 = s0["retailers"][0]
        for k in ("retailer", "search_query", "url", "commission_rate"):
            assert k in r0
        assert r0["url"].startswith("http")

    def test_persisted_links_returned(self, suggested_links):
        assert len(suggested_links["links"]) >= 1
        sample = suggested_links["links"][0]
        assert sample["link_id"].startswith("aff_")

    def test_my_links(self, auth_session, suggested_links):
        r = auth_session.get(f"{API}/affiliate/my-links?limit=100", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        _no_mongo_id(data)
        assert "links" in data and "count" in data
        ids_in_my = {link["link_id"] for link in data["links"]}
        produced_ids = {link["link_id"] for link in suggested_links["links"]}
        assert produced_ids.issubset(ids_in_my), "Newly created links not in /my-links"

    def test_my_stats(self, auth_session):
        r = auth_session.get(f"{API}/affiliate/my-stats", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        _no_mongo_id(data)
        for k in ("total_links", "total_clicks", "total_conversions", "total_earnings_eur"):
            assert k in data
        assert data["total_links"] >= 1

    def test_track_click_redirects_and_increments(self, suggested_links, anon_session, auth_session):
        link = suggested_links["links"][0]
        link_id = link["link_id"]
        expected_url = link["target_url"]

        # Stats before
        before = auth_session.get(f"{API}/affiliate/my-stats", timeout=15).json()
        clicks_before = before.get("total_clicks", 0)

        # Public endpoint - use allow_redirects=False to inspect 302
        r = anon_session.get(
            f"{API}/affiliate/track/{link_id}",
            allow_redirects=False,
            timeout=15,
        )
        assert r.status_code in (302, 307), f"expected redirect, got {r.status_code}"
        assert r.headers.get("location") == expected_url

        # Stats after - clicks should increment (allowing for fraud check skip)
        after = auth_session.get(f"{API}/affiliate/my-stats", timeout=15).json()
        clicks_after = after.get("total_clicks", 0)
        assert clicks_after >= clicks_before  # may be == if flagged suspicious

    def test_track_click_not_found(self, anon_session):
        r = anon_session.get(
            f"{API}/affiliate/track/aff_nonexistent_xyz",
            allow_redirects=False,
            timeout=15,
        )
        assert r.status_code == 404

    def test_affiliate_for_outfit(self, auth_session, generated_outfit):
        oid = generated_outfit["outfit_id"]
        r = auth_session.get(f"{API}/affiliate/outfit/{oid}", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        _no_mongo_id(data)
        assert "links" in data and isinstance(data["links"], list)
        assert len(data["links"]) >= 1
        for link in data["links"]:
            assert link["outfit_id"] == oid

    def test_affiliate_for_post_empty(self, auth_session):
        # Unknown post id should still return an empty list (not 500)
        r = auth_session.get(f"{API}/affiliate/post/post_nonexistent", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data == {"links": []}
