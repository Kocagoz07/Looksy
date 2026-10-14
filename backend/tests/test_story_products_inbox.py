"""Backend tests for Story product tags + affiliate click tracking + inbox share.

Covers:
- POST /api/stories with products[] (validation, retailer domain, affiliate_links creation)
- POST /api/stories/from-post/{post_id} inheritance semantics (no body / {} / with overrides)
- GET /api/affiliate/track/{link_id} → 302 + clicks++
- GET /api/stories/{id}/viewers includes product_clicks[] and total_clicks (owner only)
- /api/stories/feed returns products for each story
- Share-via-DM returns conversation_ids used by the frontend inbox navigation
"""
import io
import os
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

TESTUSER = {"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
NEWUSER = {"email": "newuser456@looksy.com", "password": "test1234", "category": "women"}
TESTUSER_ID = "user_899a61a17955"
NEWUSER_ID = "user_2e79eca385b6"
EXISTING_POST = "post_433af74f4413"  # 5 Zara products


def _login(creds):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def test_sess():
    return _login(TESTUSER)


@pytest.fixture(scope="module")
def new_sess():
    return _login(NEWUSER)


def _upload_image(sess) -> str:
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x00\x03\x00\x01\x5f\x36\x96\x8d\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = sess.post(f"{BASE_URL}/api/upload-image",
                  files={"file": ("t.png", io.BytesIO(png), "image/png")}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    return data.get("file_id") or data.get("image_id") or data.get("id")


# ============= STORY PRODUCTS: create =============
class TestStoryProductsCreate:
    created = []

    def test_01_create_with_products(self, test_sess):
        img = _upload_image(test_sess)
        payload = {
            "image_id": img,
            "caption": "TEST_prod",
            "products": [
                {"name": "Linen Blazer", "url": "https://www.zara.com/x/blazer", "price": 89.9},
                {"name": "Jeans", "url": "www.zara.com/x/jeans"},  # bare domain -> https
            ],
        }
        r = test_sess.post(f"{BASE_URL}/api/stories", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert len(d["products"]) == 2
        p0, p1 = d["products"]
        assert p0["name"] == "Linen Blazer"
        assert p0["price"] == 89.9
        assert "retailer" not in p0
        assert p0["link_id"].startswith("aff_")
        assert p1["price"] is None
        assert "retailer" not in p1
        TestStoryProductsCreate.created.append((d["story_id"], p0["link_id"]))

    def test_02_reject_invalid_url(self, test_sess):
        img = _upload_image(test_sess)
        for bad in ["abc", "javascript:alert(1)", "ftp://x.com/x"]:
            r = test_sess.post(f"{BASE_URL}/api/stories", json={
                "image_id": img, "products": [{"name": "x", "url": bad}]
            }, timeout=15)
            assert r.status_code == 422, f"{bad!r} should be rejected: got {r.status_code}"

    def test_03_reject_more_than_5(self, test_sess):
        img = _upload_image(test_sess)
        prods = [{"name": f"P{i}", "url": "https://zara.com/x"} for i in range(6)]
        r = test_sess.post(f"{BASE_URL}/api/stories", json={"image_id": img, "products": prods}, timeout=15)
        assert r.status_code == 422

    def test_04_reject_empty_name(self, test_sess):
        img = _upload_image(test_sess)
        r = test_sess.post(f"{BASE_URL}/api/stories", json={
            "image_id": img, "products": [{"name": "", "url": "https://zara.com/x"}]
        }, timeout=15)
        assert r.status_code == 422

    def test_05_affiliate_link_doc_exists(self, test_sess):
        """Verify affiliate_links got a doc for the created product with story_id."""
        _, link_id = TestStoryProductsCreate.created[0]
        # Use /api/affiliate/my-links to confirm doc exists for owner
        r = test_sess.get(f"{BASE_URL}/api/affiliate/my-links?limit=100", timeout=15)
        assert r.status_code == 200
        links = r.json()["links"]
        match = [lk for lk in links if lk.get("link_id") == link_id]
        assert match, f"Expected affiliate link {link_id} for story product"
        assert match[0].get("story_id") is not None
        assert match[0].get("retailer") == "zara.com"


# ============= STORY FROM POST =============
class TestStoryFromPost:
    created = []

    def test_01_no_body_inherits_post_products(self, test_sess):
        r = test_sess.post(f"{BASE_URL}/api/stories/from-post/{EXISTING_POST}", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["shared_post"]["post_id"] == EXISTING_POST
        # Post has 5 Zara products -> inherited (cap 5)
        assert 1 <= len(d["products"]) <= 5
        TestStoryFromPost.created.append(d["story_id"])

    def test_02_empty_products_body_means_no_products(self, test_sess):
        r = test_sess.post(f"{BASE_URL}/api/stories/from-post/{EXISTING_POST}",
                           json={"products": []}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["products"] == []
        TestStoryFromPost.created.append(d["story_id"])

    def test_03_override_products(self, test_sess):
        r = test_sess.post(f"{BASE_URL}/api/stories/from-post/{EXISTING_POST}",
                           json={"caption": "TEST_ov", "products": [
                               {"name": "Custom Tee", "url": "https://example.com/tee", "price": 25}
                           ]}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["caption"] == "TEST_ov"
        assert len(d["products"]) == 1
        assert d["products"][0]["name"] == "Custom Tee"
        assert "retailer" not in d["products"][0]
        TestStoryFromPost.created.append(d["story_id"])


# ============= AFFILIATE TRACK =============
class TestAffiliateTrack:
    def test_01_track_increments_and_redirects(self, test_sess, new_sess):
        # Create a story with a product
        img = _upload_image(test_sess)
        r = test_sess.post(f"{BASE_URL}/api/stories", json={
            "image_id": img, "caption": "TEST_click",
            "products": [{"name": "Shoes", "url": "https://www.zara.com/x/shoes", "price": 59.0}],
        }, timeout=15)
        assert r.status_code == 200, r.text
        story = r.json()
        link_id = story["products"][0]["link_id"]
        story_id = story["story_id"]

        # Mark newuser as a viewer first so viewers endpoint has 1 viewer later
        new_sess.post(f"{BASE_URL}/api/stories/{story_id}/view", timeout=15)

        # Follower clicks -> 302 to target_url
        r = new_sess.get(f"{BASE_URL}/api/affiliate/track/{link_id}",
                         allow_redirects=False, timeout=15)
        assert r.status_code == 302, f"got {r.status_code} / {r.text[:200]}"
        loc = r.headers.get("location", "")
        assert "zara.com" in loc, f"redirect target wrong: {loc}"

        # Second click to ensure counter increments
        new_sess.get(f"{BASE_URL}/api/affiliate/track/{link_id}", allow_redirects=False, timeout=15)

        # Owner viewers payload now carries product_clicks
        rv = test_sess.get(f"{BASE_URL}/api/stories/{story_id}/viewers", timeout=15)
        assert rv.status_code == 200, rv.text
        v = rv.json()
        assert "product_clicks" in v and "total_clicks" in v
        assert v["total_clicks"] >= 1
        pc = v["product_clicks"]
        assert pc and pc[0]["link_id"] == link_id and pc[0]["clicks"] >= 1
        # cleanup
        test_sess.delete(f"{BASE_URL}/api/stories/{story_id}", timeout=10)

    def test_02_track_unknown_link_404(self, new_sess):
        r = new_sess.get(f"{BASE_URL}/api/affiliate/track/aff_doesnotexist",
                         allow_redirects=False, timeout=15)
        assert r.status_code == 404


# ============= FEED carries products =============
class TestFeedProducts:
    def test_feed_includes_products(self, new_sess):
        r = new_sess.get(f"{BASE_URL}/api/stories/feed", timeout=15)
        assert r.status_code == 200
        groups = r.json()["groups"]
        tu = next((g for g in groups if g["user_id"] == TESTUSER_ID), None)
        assert tu is not None
        # Find at least one story on testuser group that has products
        has_products = [s for s in tu["stories"] if s.get("products")]
        assert has_products, "Expected at least one testuser story with products in feed"
        p = has_products[0]["products"][0]
        for k in ("link_id", "name"):
            assert k in p


# ============= Share via DM returns conversation ids =============
class TestShareReturnsConversation:
    def test_share_single_recipient_returns_conversation_id(self, test_sess):
        r = test_sess.post(f"{BASE_URL}/api/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": [NEWUSER_ID], "note": "TEST_inbox"}, timeout=15)
        assert r.status_code in (200, 201), r.text
        d = r.json()
        assert d["shared"] == 1
        assert d["results"] and d["results"][0].get("conversation_id")


# ============= Cleanup TEST stories we created =============
@pytest.fixture(scope="module", autouse=True)
def _cleanup(test_sess):
    yield
    try:
        r = test_sess.get(f"{BASE_URL}/api/stories/feed", timeout=15)
        own = next((g for g in r.json().get("groups", []) if g["is_me"]), None)
        if not own:
            return
        to_del = [s for s in own["stories"]
                  if (s.get("caption") or "").startswith("TEST_")]
        # Keep two newest TEST stories alive (per convention)
        for s in to_del[:-2]:
            test_sess.delete(f"{BASE_URL}/api/stories/{s['story_id']}", timeout=10)
    except Exception as e:
        print(f"cleanup error: {e}")
