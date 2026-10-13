"""Iter10: Email/password auth hardening + Claude captions + Notifications regression."""
import json
import os
import time
import uuid
import requests
import pytest

def _read_frontend_env():
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", _read_frontend_env()).rstrip("/")
API = f"{BASE_URL}/api"

SEED = {"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
SEED2 = {"email": "newuser456@looksy.com", "password": "test1234", "category": "women"}


# ---------- helpers ----------

def _new_qa_email():
    return f"qa_{uuid.uuid4().hex[:10]}@looksy.com"


def _login(session, creds):
    r = session.post(f"{API}/auth/login", json=creds, timeout=15)
    return r


@pytest.fixture(scope="session")
def seed_session():
    s = requests.Session()
    r = _login(s, SEED)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="session")
def seed2_session():
    s = requests.Session()
    r = _login(s, SEED2)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture
def qa_user():
    """Register a fresh unverified qa_ user."""
    s = requests.Session()
    email = _new_qa_email()
    r = s.post(f"{API}/auth/register", json={
        "email": email, "password": "test1234", "name": "QA User", "category": "men"
    }, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    return {"session": s, "email": email, "password": "test1234", "user_id": data["user_id"], "data": data}


# ---------- AUTH: register / email verification ----------

class TestRegister:
    def test_register_rejects_short_password(self):
        r = requests.post(f"{API}/auth/register", json={
            "email": _new_qa_email(), "password": "short1", "name": "x", "category": "men"
        }, timeout=15)
        assert r.status_code == 422, r.text

    def test_register_sets_email_verified_false(self, qa_user):
        assert qa_user["data"].get("email_verified") is False
        assert "password_hash" not in qa_user["data"]


class TestVerifyEmail:
    def test_verify_email_with_token(self, qa_user):
        # Grab token from backend log
        time.sleep(0.3)
        with open("/var/log/supervisor/backend.err.log", "r") as f:
            log = f.read()
        import re
        # Find most recent token for this email
        matches = re.findall(
            rf"Verify email for {re.escape(qa_user['email'])}:.*?token=([A-Za-z0-9_\-]+)", log
        )
        assert matches, "No verify-email token found in backend.err.log"
        token = matches[-1]
        r = requests.post(f"{API}/auth/verify-email", json={"token": token}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["verified"] is True
        assert body["email"] == qa_user["email"]

        # /me should now show email_verified true
        me = qa_user["session"].get(f"{API}/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json().get("email_verified") is True

    def test_verify_email_invalid_token(self):
        r = requests.post(f"{API}/auth/verify-email",
                          json={"token": "invalid_token_abcdef1234567890"}, timeout=15)
        assert r.status_code == 400


# ---------- AUTH: forgot/reset ----------

class TestForgotReset:
    def test_forgot_unknown_email_generic(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"nobody_{uuid.uuid4().hex[:6]}@looksy.com"}, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "message" in body
        assert "reset_link" not in body

    def test_full_reset_flow_and_cooldown(self, qa_user):
        # Request reset link
        r1 = requests.post(f"{API}/auth/forgot-password",
                           json={"email": qa_user["email"]}, timeout=15)
        assert r1.status_code == 200, r1.text
        body = r1.json()
        assert "reset_link" in body, f"AUTH_DEV_MODE should expose reset_link: {body}"
        link = body["reset_link"]
        token = link.split("token=")[-1]
        assert len(token) > 10

        # Second request within 60s -> should NOT issue new link
        r2 = requests.post(f"{API}/auth/forgot-password",
                           json={"email": qa_user["email"]}, timeout=15)
        assert r2.status_code == 200
        assert "reset_link" not in r2.json(), "Rate-limited response should not issue a new link"

        # Short password -> 422
        r_short = requests.post(f"{API}/auth/reset-password",
                                json={"token": token, "new_password": "abc"}, timeout=15)
        assert r_short.status_code == 422

        # Old session cookie should work BEFORE reset
        me_before = qa_user["session"].get(f"{API}/auth/me", timeout=15)
        assert me_before.status_code == 200

        # Reset password
        new_pw = "new_strongpw_123"
        r3 = requests.post(f"{API}/auth/reset-password",
                           json={"token": token, "new_password": new_pw}, timeout=15)
        assert r3.status_code == 200, r3.text

        # Token single-use
        r4 = requests.post(f"{API}/auth/reset-password",
                           json={"token": token, "new_password": "another_pw_456"}, timeout=15)
        assert r4.status_code == 400

        # Old session invalidated
        me_after = qa_user["session"].get(f"{API}/auth/me", timeout=15)
        assert me_after.status_code == 401, f"Expected 401 after reset, got {me_after.status_code}"

        # Login with new password works
        s = requests.Session()
        r5 = _login(s, {"email": qa_user["email"], "password": new_pw, "category": "men"})
        assert r5.status_code == 200, r5.text


class TestResendVerification:
    def test_requires_auth(self):
        r = requests.post(f"{API}/auth/resend-verification", timeout=15)
        assert r.status_code == 401

    def test_cooldown_and_already_verified(self, qa_user, seed_session):
        # qa_user already got a verification email at registration -> immediate resend hits 60s cooldown
        r = qa_user["session"].post(f"{API}/auth/resend-verification", timeout=15)
        assert r.status_code == 429, r.text

        # Seeded user (no email_verified field => treated as verified, is not False)
        r2 = seed_session.post(f"{API}/auth/resend-verification", timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("already_verified") is True


class TestLoginMe:
    def test_login_me_logout(self, seed_session):
        me = seed_session.get(f"{API}/auth/me", timeout=15)
        assert me.status_code == 200
        assert me.json()["email"] == SEED["email"]


# ---------- Claude captions ----------

class TestCaptions:
    def test_requires_auth(self):
        r = requests.post(f"{API}/ai/captions/generate",
                          json={"draft": "sunset vibes", "tone": "chic"}, timeout=20)
        assert r.status_code == 401

    def test_invalid_tone(self, seed_session):
        r = seed_session.post(f"{API}/ai/captions/generate",
                              json={"draft": "x", "tone": "sassy"}, timeout=20)
        assert r.status_code == 422

    def test_stream_and_persist(self, seed_session):
        with seed_session.post(
            f"{API}/ai/captions/generate",
            json={"draft": "golden hour rooftop fit", "tone": "chic",
                  "products": ["black blazer", "white tee"], "total_price": 180.0},
            stream=True, timeout=60,
        ) as r:
            assert r.status_code == 200, r.text
            assert "text/event-stream" in r.headers.get("content-type", "")
            saw_delta = False
            done = None
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                event = json.loads(line[len("data:"):].strip())
                if event["type"] == "delta":
                    saw_delta = True
                elif event["type"] == "done":
                    done = event
                    break
                elif event["type"] == "error":
                    pytest.fail(f"stream error: {event}")

            assert saw_delta, "Expected at least one delta event"
            assert done is not None, "Expected a done event"
            assert isinstance(done.get("captions"), list) and len(done["captions"]) == 3
            assert isinstance(done.get("hashtags"), list) and len(done["hashtags"]) > 0
            assert done.get("generation_id", "").startswith("cap_")


# ---------- Notifications ----------

def _create_post(session):
    """Upload an image + create a post, return (post_id, user_id)."""
    # 1x1 jpeg bytes
    jpeg = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909"
        "080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c231c1c2837292c30"
        "31343434341f27393d38323c2e333432ffdb0043010909090c0b0c180d0d1832211c213232"
        "32323232323232323232323232323232323232323232323232323232323232323232323232"
        "32323232323232323232323232ffc00011080001000103012200021101031101ffc4001f00"
        "00010501010101010100000000000000000102030405060708090a0bffc400b51000020103"
        "03020403050504040000017d01020300041105122131410613516107227114328191a1082342"
        "b1c11552d1f02433627282090a161718191a25262728292a3435363738393a434445464748"
        "494a535455565758595a636465666768696a737475767778797a838485868788898a92939495"
        "969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6"
        "d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda000c03010002110311003f00"
        "fbfcffd9"
    )
    files = {"file": ("tiny.jpg", jpeg, "image/jpeg")}
    r = session.post(f"{API}/upload-image", files=files, timeout=30)
    assert r.status_code == 200, r.text
    image_id = r.json()["file_id"]
    r2 = session.post(f"{API}/posts", params={"image_id": image_id},
                      json={"caption": "TEST_NOTIF_POST"}, timeout=30)
    assert r2.status_code == 200, r2.text
    return r2.json()["post_id"]


class TestNotifications:
    @pytest.fixture(scope="class")
    def post_by_seed(self):
        s = requests.Session()
        assert _login(s, SEED).status_code == 200
        pid = _create_post(s)
        yield {"session": s, "post_id": pid, "owner_id": "user_899a61a17955"}
        # cleanup
        s.delete(f"{API}/posts/{pid}", timeout=15)

    def _get_unread(self, session):
        r = session.get(f"{API}/notifications/unread-count", timeout=15)
        assert r.status_code == 200
        return r.json()["unread_count"]

    def test_requires_auth(self):
        r = requests.get(f"{API}/notifications", timeout=15)
        assert r.status_code == 401

    def test_like_creates_notification(self, post_by_seed, seed2_session):
        before = self._get_unread(post_by_seed["session"])
        r = seed2_session.post(f"{API}/posts/{post_by_seed['post_id']}/like", timeout=15)
        assert r.status_code == 200
        time.sleep(0.3)
        after = self._get_unread(post_by_seed["session"])
        assert after == before + 1, f"like did not create notification ({before}->{after})"

        # Unlike -> no new notification
        r2 = seed2_session.post(f"{API}/posts/{post_by_seed['post_id']}/like", timeout=15)
        assert r2.status_code == 200
        time.sleep(0.3)
        assert self._get_unread(post_by_seed["session"]) == after

    def test_star_creates_notification(self, post_by_seed, seed2_session):
        before = self._get_unread(post_by_seed["session"])
        r = seed2_session.post(f"{API}/posts/{post_by_seed['post_id']}/star", timeout=15)
        assert r.status_code == 200
        time.sleep(0.3)
        after = self._get_unread(post_by_seed["session"])
        assert after == before + 1
        seed2_session.post(f"{API}/posts/{post_by_seed['post_id']}/star", timeout=15)  # unstar
        time.sleep(0.3)
        assert self._get_unread(post_by_seed["session"]) == after

    def test_comment_creates_notification(self, post_by_seed, seed2_session):
        before = self._get_unread(post_by_seed["session"])
        r = seed2_session.post(f"{API}/posts/{post_by_seed['post_id']}/comments",
                               json={"text": "TEST_NOTIF cute fit"}, timeout=15)
        assert r.status_code == 200
        time.sleep(0.3)
        assert self._get_unread(post_by_seed["session"]) == before + 1

    def test_comment_on_missing_post_404(self, seed2_session):
        r = seed2_session.post(f"{API}/posts/does_not_exist_xyz/comments",
                               json={"text": "nope"}, timeout=15)
        assert r.status_code == 404

    def test_no_self_notification_on_like(self, post_by_seed):
        before = self._get_unread(post_by_seed["session"])
        # owner likes own post
        post_by_seed["session"].post(f"{API}/posts/{post_by_seed['post_id']}/like", timeout=15)
        time.sleep(0.3)
        assert self._get_unread(post_by_seed["session"]) == before
        # cleanup
        post_by_seed["session"].post(f"{API}/posts/{post_by_seed['post_id']}/like", timeout=15)

    def test_follow_creates_notification_no_self(self, seed_session, seed2_session):
        # seed2 follows seed -> seed gets a notification
        before = seed_session.get(f"{API}/notifications/unread-count", timeout=15).json()["unread_count"]
        r = seed2_session.post(f"{API}/users/user_899a61a17955/follow", timeout=15)
        assert r.status_code == 200
        time.sleep(0.3)
        after = seed_session.get(f"{API}/notifications/unread-count", timeout=15).json()["unread_count"]
        # follow may toggle, so account for either +1 or 0 depending on prior state
        # at minimum, a follow (not unfollow) should produce +1 vs the "after unfollow" baseline
        # Easiest: check +1 OR do a double-follow approach
        if after == before:
            # was already following, so this toggle was an unfollow. Do another to follow again.
            r2 = seed2_session.post(f"{API}/users/user_899a61a17955/follow", timeout=15)
            assert r2.status_code == 200
            time.sleep(0.3)
            after = seed_session.get(f"{API}/notifications/unread-count", timeout=15).json()["unread_count"]
        assert after >= before + 1, f"follow did not produce a notification ({before}->{after})"

    def test_mark_all_read(self, post_by_seed):
        r = post_by_seed["session"].post(f"{API}/notifications/mark-read",
                                         json={}, timeout=15)
        assert r.status_code == 200
        assert r.json()["unread_count"] == 0

    def test_list_notifications_has_items(self, post_by_seed):
        r = post_by_seed["session"].get(f"{API}/notifications", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert "notifications" in body
        assert isinstance(body["notifications"], list)
        # should have at least the ones created above
        assert len(body["notifications"]) >= 1
        for n in body["notifications"]:
            assert "notification_id" in n
            assert "_id" not in n
