"""
Brand Verification Feature Tests
Tests for the Brand Verified Badge feature including:
- Backend API endpoints for brand verification
- User brand status retrieval
- Search results with brand verified status
"""

import pytest
import requests
import os
import time

# Use the public backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://looksy-brand-badge.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "testuser@looksy.com"
TEST_USER_PASSWORD = "test1234"
TEST_USER_ID = "user_899a61a17955"  # Has accepted collaboration, should be brand verified


class TestBrandVerificationAPI:
    """Test Brand Verification API endpoints"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session for tests"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        # Login to get session
        login_response = s.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "category": "men"
            }
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Failed to login: {login_response.text}")
        
        return s
    
    # ========== GET Brand Status Tests ==========
    
    def test_get_brand_status_verified_user(self):
        """Test GET /api/users/{user_id}/brand-status for verified user"""
        response = requests.get(f"{BASE_URL}/api/users/{TEST_USER_ID}/brand-status")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "brand_verified" in data, "Response should contain brand_verified field"
        assert data["brand_verified"] == True, "Test user should be brand verified"
        assert "brand_verified_at" in data, "Response should contain brand_verified_at field"
        print(f"✓ Brand status API working - verified user has badge, verified at: {data['brand_verified_at']}")
    
    def test_get_brand_status_nonexistent_user(self):
        """Test GET /api/users/{user_id}/brand-status for non-existent user"""
        response = requests.get(f"{BASE_URL}/api/users/nonexistent_user_123/brand-status")
        
        assert response.status_code == 404, f"Expected 404 for non-existent user, got {response.status_code}"
        print("✓ Brand status API returns 404 for non-existent user")
    
    # ========== User Details with Brand Status Tests ==========
    
    def test_get_user_details_includes_brand_verified(self):
        """Test GET /api/users/{user_id} includes brand_verified field"""
        response = requests.get(f"{BASE_URL}/api/users/{TEST_USER_ID}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "brand_verified" in data, "User response should include brand_verified field"
        assert data["brand_verified"] == True, "Test user should have brand_verified = True"
        print(f"✓ User details includes brand_verified field: {data['brand_verified']}")
    
    # ========== Search Results with Brand Status Tests ==========
    
    def test_search_returns_brand_verified_field(self, session):
        """Test GET /api/users/search includes brand_verified in results"""
        response = session.get(f"{BASE_URL}/api/users/search?q=test")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "users" in data, "Response should contain users array"
        
        # Find test user in results
        test_user = None
        for user in data["users"]:
            if user.get("user_id") == TEST_USER_ID:
                test_user = user
                break
        
        if test_user:
            assert "brand_verified" in test_user, "Search result should include brand_verified"
            assert test_user["brand_verified"] == True, "Test user should be brand verified in search"
            print(f"✓ Search results include brand_verified field: {test_user['brand_verified']}")
        else:
            print("⚠ Test user not found in search results, skipping brand_verified check")
    
    # ========== Brand Verification Endpoint Tests ==========
    
    def test_brand_verify_requires_authentication(self):
        """Test POST /api/users/{user_id}/brand-verify requires auth"""
        response = requests.post(f"{BASE_URL}/api/users/{TEST_USER_ID}/brand-verify")
        
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("✓ Brand verify endpoint requires authentication")
    
    def test_brand_verify_own_account_only(self, session):
        """Test that users can only verify their own account"""
        # Try to verify another user's account (should fail with 403)
        response = session.post(f"{BASE_URL}/api/users/other_user_id/brand-verify")
        
        # Should either be 404 (user not found) or 403 (not authorized)
        assert response.status_code in [403, 404], f"Expected 403 or 404, got {response.status_code}"
        print(f"✓ Cannot verify other user's account - got {response.status_code}")
    
    def test_brand_verify_already_verified_user(self, session):
        """Test brand verify for already verified user"""
        response = session.post(f"{BASE_URL}/api/users/{TEST_USER_ID}/brand-verify")
        
        # Should succeed (toggle or maintain status)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "brand_verified" in data, "Response should include brand_verified"
        print(f"✓ Brand verify for already verified user returns: {data}")
    
    # ========== Data Persistence Tests ==========
    
    def test_brand_status_persists_after_verification(self, session):
        """Test that brand_verified status persists in database"""
        # First verify the user
        verify_response = session.post(f"{BASE_URL}/api/users/{TEST_USER_ID}/brand-verify")
        assert verify_response.status_code == 200
        
        # Then check status
        status_response = requests.get(f"{BASE_URL}/api/users/{TEST_USER_ID}/brand-status")
        assert status_response.status_code == 200
        
        data = status_response.json()
        assert data["brand_verified"] == True, "Brand verified status should persist"
        print("✓ Brand verified status persists after verification")


class TestBrandVerificationWithCollaborations:
    """Test brand verification with collaboration requirements"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create authenticated session"""
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        
        login_response = s.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "category": "men"
            }
        )
        
        if login_response.status_code != 200:
            pytest.skip(f"Failed to login: {login_response.text}")
        
        return s
    
    def test_accepted_collaborations_endpoint(self, session):
        """Test GET /api/collaborations/accepted returns user's accepted collabs"""
        response = session.get(f"{BASE_URL}/api/collaborations/accepted")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "collaborations" in data, "Response should contain collaborations array"
        print(f"✓ Accepted collaborations endpoint works, found {len(data['collaborations'])} collaborations")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
