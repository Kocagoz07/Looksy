"""End-to-end backend tests for Stories, Quick Reactions, and Feed (Following/Discover).

Credentials from /app/memory/test_credentials.md:
  - testuser@looksy.com / test1234 (men, user_899a61a17955)
  - newuser456@looksy.com / test1234 (women, user_2e79eca385b6)

newuser456 follows testuser; there is an existing conversation conv_667ef13ec6ee
containing many post_share messages from testuser for post_433af74f4413.
"""
import io
import os
import time
import pytest
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

TESTUSER = {"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
NEWUSER = {"email": "newuser456@looksy.com", "password": "test1234", "category": "women"}
TESTUSER_ID = "user_899a61a17955"
NEWUSER_ID = "user_2e79eca385b6"
EXISTING_POST = "post_433af74f4413"
EXISTING_CONV = "conv_667ef13ec6ee"


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


@pytest.fixture(scope="module")
def anon_sess():
    return requests.Session()


# ---------- helpers ----------
def _upload_image(sess) -> str:
    # Minimal PNG (1x1 red)
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
        b"\x00\x00\x00\x03\x00\x01\x5f\x36\x96\x8d\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    r = sess.post(
        f"{BASE_URL}/api/upload-image",
        files={"file": ("t.png", io.BytesIO(png), "image/png")},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    img_id = r.json().get("file_id") or r.json().get("image_id") or r.json().get("id")
    assert img_id and len(img_id) == 24
    return img_id


# =============== STORIES ===============
class TestStories:
    created_ids = []

    def test_01_auth_required(self, anon_sess):
        # Use proper payloads so we're testing auth, not validation
        png = b"\x89PNG\r\n\x1a\n"
        checks = [
            ("GET", "/api/stories/feed", None, None),
            ("POST", "/api/stories", {"image_id": "0" * 24}, None),
            ("POST", f"/api/stories/from-post/{EXISTING_POST}", {}, None),
            ("POST", "/api/stories/story_x/view", {}, None),
            ("GET", "/api/stories/story_x/viewers", None, None),
            ("DELETE", "/api/stories/story_x", None, None),
        ]
        for method, path, body, _ in checks:
            r = anon_sess.request(method, f"{BASE_URL}{path}",
                                  json=body if body is not None else None, timeout=15)
            assert r.status_code == 401, f"{method} {path} -> {r.status_code}"

    def test_02_create_story_from_upload(self, test_sess):
        img_id = _upload_image(test_sess)
        r = test_sess.post(f"{BASE_URL}/api/stories",
                           json={"image_id": img_id, "caption": "TEST_hello"}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user_id"] == TESTUSER_ID
        assert data["image_id"] == img_id
        assert data["caption"] == "TEST_hello"
        assert data["seen"] is True  # owner
        assert "view_count" in data
        # expires_at ~ created_at + 24h
        from datetime import datetime
        ca = datetime.fromisoformat(data["created_at"])
        ea = datetime.fromisoformat(data["expires_at"])
        delta = (ea - ca).total_seconds()
        assert 86390 <= delta <= 86410, f"expires_at delta = {delta}"
        TestStories.created_ids.append(data["story_id"])

    def test_03_create_story_bad_image(self, test_sess):
        r = test_sess.post(f"{BASE_URL}/api/stories",
                           json={"image_id": "0" * 24}, timeout=15)
        assert r.status_code == 400

    def test_04_create_from_post(self, test_sess):
        r = test_sess.post(f"{BASE_URL}/api/stories/from-post/{EXISTING_POST}", timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["shared_post"]["post_id"] == EXISTING_POST
        assert "author_id" in d["shared_post"]
        assert "author_name" in d["shared_post"]
        TestStories.created_ids.append(d["story_id"])

    def test_05_create_from_post_404(self, test_sess):
        r = test_sess.post(f"{BASE_URL}/api/stories/from-post/post_nonexistent_xx", timeout=15)
        assert r.status_code == 404

    def test_06_feed_contains_own_first(self, test_sess):
        r = test_sess.get(f"{BASE_URL}/api/stories/feed", timeout=15)
        assert r.status_code == 200
        groups = r.json()["groups"]
        assert groups, "expected at least own group"
        assert groups[0]["is_me"] is True
        assert groups[0]["user_id"] == TESTUSER_ID
        s0 = groups[0]["stories"][0]
        assert "view_count" in s0  # owner
        assert s0["seen"] is True

    def test_07_follower_sees_followed_user_story(self, new_sess):
        r = new_sess.get(f"{BASE_URL}/api/stories/feed", timeout=15)
        assert r.status_code == 200
        groups = r.json()["groups"]
        tu_group = next((g for g in groups if g["user_id"] == TESTUSER_ID), None)
        assert tu_group is not None, "newuser456 should see testuser's stories (follows testuser)"
        assert tu_group["has_unseen"] is True
        assert tu_group["is_me"] is False
        # at least one unseen in the group
        assert any(s["seen"] is False for s in tu_group["stories"])
        assert "view_count" not in tu_group["stories"][0]  # non-owner must not see
        # unseen groups should sort before seen groups among non-me
        non_me = [g for g in groups if not g["is_me"]]
        if len(non_me) > 1:
            seen_flags = [g["has_unseen"] for g in non_me]
            # all unseen come before seen
            assert seen_flags == sorted(seen_flags, reverse=True)

    def test_08_view_marks_seen_and_idempotent(self, new_sess, test_sess):
        story_id = TestStories.created_ids[0]
        r = new_sess.post(f"{BASE_URL}/api/stories/{story_id}/view", timeout=15)
        assert r.status_code == 200
        # second view idempotent
        r2 = new_sess.post(f"{BASE_URL}/api/stories/{story_id}/view", timeout=15)
        assert r2.status_code == 200
        # Verify in viewers (owner only)
        rv = test_sess.get(f"{BASE_URL}/api/stories/{story_id}/viewers", timeout=15)
        assert rv.status_code == 200
        viewers = rv.json()["viewers"]
        assert rv.json()["count"] == 1  # idempotent
        assert any(v["user_id"] == NEWUSER_ID for v in viewers)
        # Owner viewing own story should not be recorded as viewer
        test_sess.post(f"{BASE_URL}/api/stories/{story_id}/view", timeout=15)
        rv2 = test_sess.get(f"{BASE_URL}/api/stories/{story_id}/viewers", timeout=15)
        assert rv2.json()["count"] == 1

    def test_09_feed_shows_seen_after_view(self, new_sess):
        r = new_sess.get(f"{BASE_URL}/api/stories/feed", timeout=15)
        tu_group = next(g for g in r.json()["groups"] if g["user_id"] == TESTUSER_ID)
        # At least one story should now be seen
        assert any(s["seen"] for s in tu_group["stories"])

    def test_10_viewers_forbidden_for_others(self, new_sess):
        story_id = TestStories.created_ids[0]
        r = new_sess.get(f"{BASE_URL}/api/stories/{story_id}/viewers", timeout=15)
        assert r.status_code == 403

    def test_11_delete_wrong_owner_404(self, new_sess):
        story_id = TestStories.created_ids[0]
        r = new_sess.delete(f"{BASE_URL}/api/stories/{story_id}", timeout=15)
        assert r.status_code == 404

    def test_12_delete_by_owner_ok(self, test_sess):
        # delete the extra one, keep one around per instructions
        if len(TestStories.created_ids) > 1:
            sid = TestStories.created_ids.pop()
            r = test_sess.delete(f"{BASE_URL}/api/stories/{sid}", timeout=15)
            assert r.status_code == 200
            assert r.json().get("deleted") is True

    def test_13_ttl_index_present(self):
        # verify Mongo index on stories.expires_at with expireAfterSeconds
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            pytest.skip("Mongo env not available")
        c = MongoClient(mongo_url)
        idx = c[db_name].stories.index_information()
        ttl = [v for v in idx.values() if any(k[0] == "expires_at" for k in v.get("key", []))]
        assert ttl, "no index on stories.expires_at"
        assert any(v.get("expireAfterSeconds") == 0 for v in ttl), "TTL expireAfterSeconds=0 missing"


# =============== REACTIONS ===============
class TestReactions:
    # fetch an existing post_share message from the known conversation
    @pytest.fixture(scope="class")
    def share_msg_id(self, test_sess):
        r = test_sess.get(f"{BASE_URL}/api/chat/conversations/{EXISTING_CONV}/messages?limit=50", timeout=15)
        assert r.status_code == 200, r.text
        msgs = r.json().get("messages") or r.json()
        if isinstance(msgs, dict):
            msgs = msgs.get("messages", [])
        share = next((m for m in msgs if m.get("type") == "post_share"), None)
        assert share, "No post_share message found in existing conversation"
        return share["message_id"]

    @pytest.fixture(scope="class")
    def text_msg_id(self, test_sess):
        # send a text message to use for 400 case
        r = test_sess.post(
            f"{BASE_URL}/api/chat/conversations/{EXISTING_CONV}/messages",
            json={"content": "TEST_reaction_text"}, timeout=15,
        )
        assert r.status_code in (200, 201), r.text
        return (r.json().get("message") or r.json())["message_id"]

    def test_01_auth_required(self, anon_sess, share_msg_id):
        r = anon_sess.post(f"{BASE_URL}/api/chat/messages/{share_msg_id}/react",
                           json={"emoji": "❤️"}, timeout=15)
        assert r.status_code == 401

    def test_02_add_heart(self, new_sess, share_msg_id):
        r = new_sess.post(f"{BASE_URL}/api/chat/messages/{share_msg_id}/react",
                          json={"emoji": "❤️"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["message_id"] == share_msg_id
        assert any(x["user_id"] == NEWUSER_ID and x["emoji"] == "❤️" for x in data["reactions"])

    def test_03_same_emoji_removes(self, new_sess, share_msg_id):
        r = new_sess.post(f"{BASE_URL}/api/chat/messages/{share_msg_id}/react",
                          json={"emoji": "❤️"}, timeout=15)
        assert r.status_code == 200
        assert not any(x["user_id"] == NEWUSER_ID for x in r.json()["reactions"])

    def test_04_different_emoji_replaces(self, new_sess, share_msg_id):
        new_sess.post(f"{BASE_URL}/api/chat/messages/{share_msg_id}/react", json={"emoji": "😍"})
        r = new_sess.post(f"{BASE_URL}/api/chat/messages/{share_msg_id}/react",
                          json={"emoji": "🔥"}, timeout=15)
        own = [x for x in r.json()["reactions"] if x["user_id"] == NEWUSER_ID]
        assert len(own) == 1 and own[0]["emoji"] == "🔥"

    def test_05_invalid_emoji(self, new_sess, share_msg_id):
        r = new_sess.post(f"{BASE_URL}/api/chat/messages/{share_msg_id}/react",
                          json={"emoji": "💩"}, timeout=15)
        assert r.status_code == 400

    def test_06_text_message_400(self, new_sess, text_msg_id):
        r = new_sess.post(f"{BASE_URL}/api/chat/messages/{text_msg_id}/react",
                          json={"emoji": "❤️"}, timeout=15)
        assert r.status_code == 400

    def test_07_non_participant_403(self, share_msg_id):
        # register a brand new user, then try reacting
        s = requests.Session()
        email = f"qa_react_{int(time.time())}@looksy.com"
        reg = s.post(f"{BASE_URL}/api/auth/register",
                     json={"email": email, "password": "test1234",
                           "name": "QA React", "category": "men"}, timeout=20)
        assert reg.status_code in (200, 201), reg.text
        r = s.post(f"{BASE_URL}/api/chat/messages/{share_msg_id}/react",
                   json={"emoji": "❤️"}, timeout=15)
        assert r.status_code == 403

    def test_08_messages_endpoint_returns_reactions(self, test_sess, share_msg_id):
        r = test_sess.get(f"{BASE_URL}/api/chat/conversations/{EXISTING_CONV}/messages?limit=50", timeout=15)
        msgs = r.json().get("messages", r.json())
        if isinstance(msgs, dict):
            msgs = msgs.get("messages", [])
        m = next(m for m in msgs if m["message_id"] == share_msg_id)
        assert "reactions" in m
        assert any(x["user_id"] == NEWUSER_ID for x in m["reactions"])

    def test_09_sender_gets_notification(self, test_sess):
        # testuser is the sender of the shared posts
        r = test_sess.get(f"{BASE_URL}/api/notifications?limit=20", timeout=15)
        assert r.status_code == 200
        items = r.json().get("notifications", r.json())
        if isinstance(items, dict):
            items = items.get("items") or items.get("notifications") or []
        assert any(n.get("type") == "reaction" for n in items), f"no 'reaction' notification found: {items[:3]}"


# =============== FEEDS ===============
class TestFeeds:
    def test_01_auth_required(self, anon_sess):
        assert anon_sess.get(f"{BASE_URL}/api/feed/following", timeout=15).status_code == 401
        assert anon_sess.get(f"{BASE_URL}/api/feed/popular", timeout=15).status_code == 401

    def test_02_following_feed_only_followed_and_self(self, new_sess):
        r = new_sess.get(f"{BASE_URL}/api/feed/following", timeout=15)
        assert r.status_code == 200
        posts = r.json()["posts"]
        allowed = {TESTUSER_ID, NEWUSER_ID}
        for p in posts:
            assert p["user_id"] in allowed, f"unexpected author: {p['user_id']}"

    def test_03_popular_invalid_category(self, test_sess):
        r = test_sess.get(f"{BASE_URL}/api/feed/popular?category=kids", timeout=15)
        assert r.status_code == 422

    def test_04_popular_men(self, test_sess):
        r = test_sess.get(f"{BASE_URL}/api/feed/popular?category=men&limit=10", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["category"] == "men"
        # must not include own posts
        for p in d["posts"]:
            assert p["user_id"] != TESTUSER_ID

    def test_05_popular_women(self, new_sess):
        r = new_sess.get(f"{BASE_URL}/api/feed/popular?category=women&limit=10", timeout=15)
        assert r.status_code == 200
        assert r.json()["category"] == "women"

    def test_06_popular_exclude_following(self, new_sess):
        r = new_sess.get(f"{BASE_URL}/api/feed/popular?exclude_following=true&limit=20", timeout=15)
        assert r.status_code == 200
        for p in r.json()["posts"]:
            assert p["user_id"] not in {TESTUSER_ID, NEWUSER_ID}, \
                "exclude_following should drop followed-user posts"


# Final cleanup: keep at most 2 TEST stories for testuser (per request)
@pytest.fixture(scope="module", autouse=True)
def _cleanup(test_sess):
    yield
    try:
        r = test_sess.get(f"{BASE_URL}/api/stories/feed", timeout=15)
        groups = r.json().get("groups", [])
        own = next((g for g in groups if g["is_me"]), None)
        if not own:
            return
        test_stories = [s for s in own["stories"] if (s.get("caption") or "").startswith("TEST_")]
        for s in test_stories[2:]:
            test_sess.delete(f"{BASE_URL}/api/stories/{s['story_id']}", timeout=10)
    except Exception as e:
        print(f"cleanup error: {e}")
