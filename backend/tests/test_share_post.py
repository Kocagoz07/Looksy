"""Tests for the Share Post via DM feature (iteration 11)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://looksy-ai-outfit.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

USER_A = {"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
USER_B = {"email": "newuser456@looksy.com", "password": "test1234", "category": "women"}
USER_A_ID = "user_899a61a17955"
USER_B_ID = "user_2e79eca385b6"
EXISTING_POST = "post_433af74f4413"


def login(user):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=user, timeout=20)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def session_a():
    return login(USER_A)


@pytest.fixture(scope="module")
def session_b():
    return login(USER_B)


# ---- /api/share/recipients ----

class TestShareRecipients:
    def test_unauthenticated_401(self):
        r = requests.get(f"{API}/share/recipients", timeout=15)
        assert r.status_code == 401

    def test_default_list(self, session_a):
        r = session_a.get(f"{API}/share/recipients", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "users" in data and isinstance(data["users"], list)
        for u in data["users"]:
            assert u["user_id"] != USER_A_ID
            assert "name" in u and "is_following" in u
            assert "_id" not in u

    def test_search_min_chars(self, session_a):
        r = session_a.get(f"{API}/share/recipients", params={"q": "a"}, timeout=15)
        assert r.status_code == 200
        # q too short -> treated as default list; still excludes self
        for u in r.json()["users"]:
            assert u["user_id"] != USER_A_ID

    def test_search_by_name(self, session_a):
        # Search for 'new' should match newuser456
        r = session_a.get(f"{API}/share/recipients", params={"q": "new"}, timeout=15)
        assert r.status_code == 200
        users = r.json()["users"]
        assert any(u["user_id"] == USER_B_ID for u in users), f"newuser456 not found: {[u['name'] for u in users]}"


# ---- /api/posts/{post_id}/share ----

class TestSharePost:
    def test_unauthenticated_401(self):
        r = requests.post(f"{API}/posts/{EXISTING_POST}/share",
                          json={"recipient_ids": [USER_B_ID]}, timeout=15)
        assert r.status_code == 401

    def test_unknown_post_404(self, session_a):
        r = session_a.post(f"{API}/posts/post_doesnotexist/share",
                           json={"recipient_ids": [USER_B_ID]}, timeout=15)
        assert r.status_code == 404

    def test_empty_recipients_422(self, session_a):
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": []}, timeout=15)
        assert r.status_code == 422

    def test_too_many_recipients_422(self, session_a):
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": [f"user_{i}" for i in range(11)]}, timeout=15)
        assert r.status_code == 422

    def test_only_self_recipient_400(self, session_a):
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": [USER_A_ID]}, timeout=15)
        assert r.status_code == 400

    def test_invalid_recipient_400(self, session_a):
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": ["user_definitely_not_real_xyz"]}, timeout=15)
        assert r.status_code == 400

    def test_note_too_long_422(self, session_a):
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": [USER_B_ID], "note": "x" * 501}, timeout=15)
        assert r.status_code == 422

    def test_share_success_and_message_persisted(self, session_a, session_b):
        note_text = "TEST_share integration note"
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": [USER_B_ID, USER_A_ID], "note": note_text},
                           timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["shared"] == 1  # self filtered
        assert data["results"][0]["recipient_id"] == USER_B_ID
        conv_id = data["results"][0]["conversation_id"]
        assert conv_id

        # Recipient fetches messages and sees post_share
        r2 = session_b.get(f"{API}/chat/conversations/{conv_id}/messages", timeout=15)
        assert r2.status_code == 200
        msgs = r2.json()["messages"]
        shares = [m for m in msgs if m.get("type") == "post_share"]
        assert shares, f"no post_share message in conversation: {msgs}"
        m = shares[-1]
        assert m["content"] == note_text
        sp = m.get("shared_post")
        assert sp and sp["post_id"] == EXISTING_POST
        assert sp["has_note"] is True
        assert "image_id" in sp and "author_id" in sp
        assert "_id" not in m

    def test_share_without_note_uses_placeholder(self, session_a, session_b):
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": [USER_B_ID]}, timeout=20)
        assert r.status_code == 200
        conv_id = r.json()["results"][0]["conversation_id"]
        r2 = session_b.get(f"{API}/chat/conversations/{conv_id}/messages", timeout=15)
        msgs = [m for m in r2.json()["messages"] if m.get("type") == "post_share"]
        latest = msgs[-1]
        assert latest["content"] == "Shared a post"
        assert latest["shared_post"]["has_note"] is False

    def test_notification_created_for_recipient(self, session_a, session_b):
        session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                       json={"recipient_ids": [USER_B_ID], "note": "TEST notif check"}, timeout=20)
        r = session_b.get(f"{API}/notifications", timeout=15)
        assert r.status_code == 200
        notifs = r.json().get("notifications", r.json()) if isinstance(r.json(), dict) else r.json()
        # Normalize
        if isinstance(notifs, dict) and "items" in notifs:
            notifs = notifs["items"]
        msg_notifs = [n for n in notifs if n.get("type") == "message"]
        assert msg_notifs, f"no message-type notifications: {notifs[:3]}"
        assert any("shared a post" in (n.get("preview") or n.get("message") or "") for n in msg_notifs)


# ---- Regression: text messages still work ----

class TestChatRegression:
    def test_text_message_still_works(self, session_a, session_b):
        # Reuse a conversation by sharing (gives us conv_id)
        r = session_a.post(f"{API}/posts/{EXISTING_POST}/share",
                           json={"recipient_ids": [USER_B_ID]}, timeout=20)
        conv_id = r.json()["results"][0]["conversation_id"]
        r2 = session_a.post(f"{API}/chat/conversations/{conv_id}/messages",
                            json={"content": "TEST plain text", "type": "text"}, timeout=15)
        assert r2.status_code in (200, 201)
        body = r2.json()
        assert body.get("type") == "text"
        assert body.get("content") == "TEST plain text"
        assert "shared_post" not in body
