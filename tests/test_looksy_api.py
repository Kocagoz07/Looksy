"""
Looksy Fashion Social Media App - Backend API Tests
Tests: Authentication, User Management, Collaborations, Posts
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://looksy-ai-outfit.preview.emergentagent.com')

# Test credentials from review request
TEST_USER = {
    "email": "testuser@looksy.com",
    "password": "test1234",
    "category": "men",
    "user_id": "user_899a61a17955"
}

SECOND_TEST_USER = {
    "email": "newuser456@looksy.com",
    "password": "test1234",
    "category": "women",
    "user_id": "user_2e79eca385b6"
}


class TestHealthAndBasicEndpoints:
    """Basic API health and accessibility tests"""
    
    def test_api_accessible(self):
        """Test that API is accessible"""
        response = requests.get(f"{BASE_URL}/api/posts")
        assert response.status_code == 200, f"API not accessible: {response.status_code}"
        print("SUCCESS: API is accessible")


class TestAuthenticationFlow:
    """Authentication endpoint tests - Login, Register, Magic Link"""
    
    def test_login_with_valid_credentials(self):
        """Test login with email/password for test user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"],
                "category": TEST_USER["category"]
            }
        )
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "user_id" in data, "Response missing user_id"
        assert data["email"] == TEST_USER["email"], "Email mismatch"
        print(f"SUCCESS: Login successful for {TEST_USER['email']}")
        return response.cookies.get("session_token")
    
    def test_login_with_invalid_credentials(self):
        """Test login with wrong password"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": "wrongpassword",
                "category": "men"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Invalid credentials correctly rejected")
    
    def test_login_with_nonexistent_user(self):
        """Test login with non-existent email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "nonexistent@looksy.com",
                "password": "test1234",
                "category": "men"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Non-existent user correctly rejected")
    
    def test_send_magic_link(self):
        """Test magic link generation"""
        response = requests.post(
            f"{BASE_URL}/api/auth/send-magic-link",
            json={
                "email": "magictest@looksy.com",
                "category": "women"
            }
        )
        assert response.status_code == 200, f"Magic link failed: {response.status_code}"
        
        data = response.json()
        assert "magic_link" in data, "Response missing magic_link"
        assert "message" in data, "Response missing message"
        print("SUCCESS: Magic link generated")
    
    def test_register_duplicate_email(self):
        """Test registration with existing email"""
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": TEST_USER["email"],
                "password": "newpassword123",
                "name": "Duplicate User",
                "category": "men"
            }
        )
        assert response.status_code == 400, f"Expected 400 for duplicate, got {response.status_code}"
        print("SUCCESS: Duplicate email registration correctly rejected")
    
    def test_register_new_user(self):
        """Test registration with new email"""
        unique_email = f"test_{uuid.uuid4().hex[:8]}@looksy.com"
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": unique_email,
                "password": "testpass123",
                "name": "Test New User",
                "category": "women"
            }
        )
        assert response.status_code == 200, f"Registration failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "user_id" in data, "Response missing user_id"
        assert data["email"] == unique_email, "Email mismatch"
        print(f"SUCCESS: New user registered: {unique_email}")


class TestAuthenticatedEndpoints:
    """Tests requiring authentication"""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Login and get session for authenticated tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"],
                "category": TEST_USER["category"]
            }
        )
        if response.status_code != 200:
            pytest.skip("Could not authenticate test user")
        
        self.session = requests.Session()
        self.session.cookies.update(response.cookies)
        self.user_id = TEST_USER["user_id"]
    
    def test_get_current_user(self):
        """Test /api/auth/me endpoint"""
        response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Get me failed: {response.status_code}"
        
        data = response.json()
        assert "user_id" in data, "Response missing user_id"
        assert "email" in data, "Response missing email"
        assert "name" in data, "Response missing name"
        print(f"SUCCESS: Got current user: {data['name']}")
    
    def test_get_user_profile(self):
        """Test getting user profile by ID"""
        response = self.session.get(f"{BASE_URL}/api/users/{self.user_id}")
        assert response.status_code == 200, f"Get user failed: {response.status_code}"
        
        data = response.json()
        assert data["user_id"] == self.user_id, "User ID mismatch"
        assert "name" in data, "Response missing name"
        assert "category" in data, "Response missing category"
        print(f"SUCCESS: Got user profile for {self.user_id}")
    
    def test_get_user_posts(self):
        """Test getting user's posts"""
        response = self.session.get(f"{BASE_URL}/api/users/{self.user_id}/posts")
        assert response.status_code == 200, f"Get user posts failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} posts for user")
    
    def test_update_user_bio(self):
        """Test updating user bio"""
        new_bio = f"Test bio updated at {uuid.uuid4().hex[:8]}"
        response = self.session.patch(
            f"{BASE_URL}/api/users/me?bio={new_bio}"
        )
        assert response.status_code == 200, f"Update bio failed: {response.status_code}"
        
        data = response.json()
        assert data.get("bio") == new_bio, "Bio not updated"
        print("SUCCESS: User bio updated")


class TestCollaborationHub:
    """Tests for Collaboration Hub feature"""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Login and get session"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"],
                "category": TEST_USER["category"]
            }
        )
        if response.status_code != 200:
            pytest.skip("Could not authenticate test user")
        
        self.session = requests.Session()
        self.session.cookies.update(response.cookies)
    
    def test_get_collaboration_inbox(self):
        """Test getting collaboration inbox"""
        response = self.session.get(f"{BASE_URL}/api/collaborations/inbox")
        assert response.status_code == 200, f"Get inbox failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} collaboration messages")
    
    def test_send_collaboration_request(self):
        """Test sending collaboration request to another user"""
        response = self.session.post(
            f"{BASE_URL}/api/collaborations/send",
            json={
                "to_user_id": SECOND_TEST_USER["user_id"],
                "subject": "Brand Partnership Test",
                "message": "Hi! I'd love to collaborate with you on a test project."
            }
        )
        assert response.status_code == 200, f"Send collab failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "message_id" in data, "Response missing message_id"
        print(f"SUCCESS: Collaboration request sent, ID: {data['message_id']}")
        return data["message_id"]


class TestFollowSystem:
    """Tests for follow/unfollow functionality"""
    
    @pytest.fixture(autouse=True)
    def setup_session(self):
        """Login and get session"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"],
                "category": TEST_USER["category"]
            }
        )
        if response.status_code != 200:
            pytest.skip("Could not authenticate test user")
        
        self.session = requests.Session()
        self.session.cookies.update(response.cookies)
    
    def test_toggle_follow(self):
        """Test follow/unfollow another user"""
        response = self.session.post(
            f"{BASE_URL}/api/users/{SECOND_TEST_USER['user_id']}/follow"
        )
        assert response.status_code == 200, f"Follow failed: {response.status_code}"
        
        data = response.json()
        assert "following" in data, "Response missing following status"
        print(f"SUCCESS: Follow toggled, now following: {data['following']}")
    
    def test_cannot_follow_self(self):
        """Test that user cannot follow themselves"""
        response = self.session.post(
            f"{BASE_URL}/api/users/{TEST_USER['user_id']}/follow"
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("SUCCESS: Self-follow correctly rejected")


class TestPostsEndpoints:
    """Tests for posts functionality"""
    
    def test_get_all_posts(self):
        """Test getting all posts"""
        response = requests.get(f"{BASE_URL}/api/posts")
        assert response.status_code == 200, f"Get posts failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} posts")
    
    def test_get_posts_by_category(self):
        """Test getting posts filtered by category"""
        response = requests.get(f"{BASE_URL}/api/posts?category=men")
        assert response.status_code == 200, f"Get posts by category failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} posts for men category")
    
    def test_get_stars_posts(self):
        """Test getting starred posts (10k+ likes)"""
        response = requests.get(f"{BASE_URL}/api/posts/stars")
        assert response.status_code == 200, f"Get stars posts failed: {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be a list"
        print(f"SUCCESS: Got {len(data)} starred posts")


class TestUnauthenticatedAccess:
    """Tests for endpoints that should reject unauthenticated requests"""
    
    def test_auth_me_requires_auth(self):
        """Test that /api/auth/me requires authentication"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: /api/auth/me correctly requires auth")
    
    def test_collaboration_inbox_requires_auth(self):
        """Test that collaboration inbox requires authentication"""
        response = requests.get(f"{BASE_URL}/api/collaborations/inbox")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Collaboration inbox correctly requires auth")
    
    def test_send_collaboration_requires_auth(self):
        """Test that sending collaboration requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/collaborations/send",
            json={
                "to_user_id": "some_user",
                "subject": "Test",
                "message": "Test message"
            }
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Send collaboration correctly requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
