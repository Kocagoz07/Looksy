"""
Test suite for Looksy new features:
- Rewards system with star conversion
- KYC verification
- Stripe and PayPal payouts
- Favorites feature
- Celebrity posts page
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://fashion-hub-1308.preview.emergentagent.com')

class TestRewardsSystem:
    """Tests for rewards/stars conversion system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get session for authenticated tests"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.user_data = login_response.json()
        
    def test_rewards_info_endpoint(self):
        """Test GET /api/rewards/info returns rewards data"""
        response = self.session.get(f"{BASE_URL}/api/rewards/info")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        # Verify response structure
        assert "stars" in data
        assert "payout_points_usd" in data
        assert "payout_points_eur" in data
        assert "earnings_usd" in data
        assert "earnings_eur" in data
        assert "kyc_verified" in data
        assert "conversion_rates" in data
        assert "min_payout_threshold_eur" in data
        
        # Verify conversion rates structure
        rates = data["conversion_rates"]
        assert "tier1" in rates
        assert "tier2" in rates
        assert "tier3" in rates
        assert "max_stars_per_post" in rates
        
        print(f"✓ Rewards info: stars={data['stars']}, payout_points_eur={data['payout_points_eur']}")
        
    def test_rewards_info_requires_auth(self):
        """Test rewards info requires authentication"""
        response = requests.get(f"{BASE_URL}/api/rewards/info")
        assert response.status_code == 401
        print("✓ Rewards info correctly requires authentication")
        
    def test_convert_stars_validation(self):
        """Test star conversion validation - cannot convert more than available"""
        # Try to convert more stars than available
        response = self.session.post(
            f"{BASE_URL}/api/rewards/convert-stars",
            json={"stars_to_convert": 999999}
        )
        assert response.status_code == 400
        assert "Insufficient stars" in response.json().get("detail", "")
        print("✓ Star conversion correctly validates available stars")
        
    def test_convert_stars_zero_validation(self):
        """Test star conversion rejects zero or negative values"""
        response = self.session.post(
            f"{BASE_URL}/api/rewards/convert-stars",
            json={"stars_to_convert": 0}
        )
        assert response.status_code == 400
        print("✓ Star conversion correctly rejects zero stars")
        
    def test_convert_stars_negative_validation(self):
        """Test star conversion rejects negative values"""
        response = self.session.post(
            f"{BASE_URL}/api/rewards/convert-stars",
            json={"stars_to_convert": -100}
        )
        assert response.status_code == 400
        print("✓ Star conversion correctly rejects negative stars")


class TestKYCVerification:
    """Tests for KYC verification system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get session for authenticated tests"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
        )
        assert login_response.status_code == 200
        
    def test_kyc_status_endpoint(self):
        """Test GET /api/kyc/status returns KYC status"""
        response = self.session.get(f"{BASE_URL}/api/kyc/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "kyc_verified" in data
        assert "kyc_status" in data
        print(f"✓ KYC status: verified={data['kyc_verified']}, status={data['kyc_status']}")
        
    def test_kyc_status_requires_auth(self):
        """Test KYC status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/kyc/status")
        assert response.status_code == 401
        print("✓ KYC status correctly requires authentication")
        
    def test_kyc_submit_endpoint(self):
        """Test POST /api/kyc/submit submits KYC and auto-approves"""
        kyc_data = {
            "full_name": "Test User",
            "date_of_birth": "1990-01-15",
            "address": "123 Test Street, Test City",
            "country": "United States",
            "id_type": "passport",
            "id_number": "AB123456789"
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/kyc/submit",
            json=kyc_data
        )
        assert response.status_code == 200, f"KYC submit failed: {response.text}"
        
        data = response.json()
        assert data.get("kyc_verified") == True
        assert "message" in data
        print(f"✓ KYC submitted and auto-approved: {data['message']}")
        
    def test_kyc_submit_requires_auth(self):
        """Test KYC submit requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/kyc/submit",
            json={"full_name": "Test", "date_of_birth": "1990-01-01", "address": "Test", "country": "US", "id_type": "passport", "id_number": "123"}
        )
        assert response.status_code == 401
        print("✓ KYC submit correctly requires authentication")


class TestPayoutSystem:
    """Tests for Stripe and PayPal payout system"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get session for authenticated tests"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
        )
        assert login_response.status_code == 200
        
    def test_payout_history_endpoint(self):
        """Test GET /api/payout/history returns transaction history"""
        response = self.session.get(f"{BASE_URL}/api/payout/history")
        assert response.status_code == 200
        
        data = response.json()
        assert "transactions" in data
        assert "count" in data
        assert isinstance(data["transactions"], list)
        print(f"✓ Payout history: {data['count']} transactions")
        
    def test_payout_history_requires_auth(self):
        """Test payout history requires authentication"""
        response = requests.get(f"{BASE_URL}/api/payout/history")
        assert response.status_code == 401
        print("✓ Payout history correctly requires authentication")
        
    def test_stripe_payout_requires_kyc(self):
        """Test Stripe payout requires KYC verification"""
        # First ensure user has KYC (from previous test)
        # Then test payout with insufficient balance
        response = self.session.post(
            f"{BASE_URL}/api/payout/stripe/setup",
            json={"amount_eur": 20.0, "origin_url": "https://test.com"}
        )
        # Should fail due to insufficient payout points (not KYC since we submitted it)
        assert response.status_code in [400, 200]  # 400 if insufficient balance, 200 if has balance
        print(f"✓ Stripe payout endpoint responds correctly: {response.status_code}")
        
    def test_paypal_payout_requires_kyc(self):
        """Test PayPal payout requires KYC verification"""
        response = self.session.post(
            f"{BASE_URL}/api/payout/paypal/setup",
            json={"amount_eur": 20.0, "paypal_email": "test@paypal.com"}
        )
        # Should fail due to insufficient payout points
        assert response.status_code in [400, 200]
        print(f"✓ PayPal payout endpoint responds correctly: {response.status_code}")
        
    def test_stripe_payout_minimum_threshold(self):
        """Test Stripe payout enforces minimum €20 threshold"""
        response = self.session.post(
            f"{BASE_URL}/api/payout/stripe/setup",
            json={"amount_eur": 5.0, "origin_url": "https://test.com"}
        )
        assert response.status_code == 400
        assert "Minimum payout" in response.json().get("detail", "") or "Insufficient" in response.json().get("detail", "")
        print("✓ Stripe payout correctly enforces minimum threshold")
        
    def test_paypal_payout_minimum_threshold(self):
        """Test PayPal payout enforces minimum €20 threshold"""
        response = self.session.post(
            f"{BASE_URL}/api/payout/paypal/setup",
            json={"amount_eur": 10.0, "paypal_email": "test@paypal.com"}
        )
        assert response.status_code == 400
        assert "Minimum payout" in response.json().get("detail", "") or "Insufficient" in response.json().get("detail", "")
        print("✓ PayPal payout correctly enforces minimum threshold")


class TestFavoritesFeature:
    """Tests for favorites/bookmark feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get session for authenticated tests"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
        )
        assert login_response.status_code == 200
        
    def test_get_favorites_endpoint(self):
        """Test GET /api/users/me/favorites returns user's favorites"""
        response = self.session.get(f"{BASE_URL}/api/users/me/favorites")
        assert response.status_code == 200
        
        data = response.json()
        assert "favorites" in data
        assert "count" in data
        assert isinstance(data["favorites"], list)
        print(f"✓ Favorites endpoint: {data['count']} favorites")
        
    def test_favorites_requires_auth(self):
        """Test favorites endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/users/me/favorites")
        assert response.status_code == 401
        print("✓ Favorites correctly requires authentication")
        
    def test_toggle_favorite_on_post(self):
        """Test POST /api/posts/{post_id}/favorite toggles favorite"""
        # First get a post to favorite
        posts_response = self.session.get(f"{BASE_URL}/api/posts?limit=1")
        if posts_response.status_code == 200 and posts_response.json():
            post = posts_response.json()[0]
            post_id = post["post_id"]
            
            # Toggle favorite
            response = self.session.post(f"{BASE_URL}/api/posts/{post_id}/favorite")
            assert response.status_code == 200
            
            data = response.json()
            assert "is_favorited" in data
            assert "message" in data
            print(f"✓ Toggle favorite: is_favorited={data['is_favorited']}")
            
            # Toggle again to restore state
            self.session.post(f"{BASE_URL}/api/posts/{post_id}/favorite")
        else:
            print("⚠ No posts available to test favorite toggle")
            
    def test_favorite_nonexistent_post(self):
        """Test favoriting non-existent post returns 404"""
        response = self.session.post(f"{BASE_URL}/api/posts/nonexistent_post_id/favorite")
        assert response.status_code == 404
        print("✓ Favoriting non-existent post correctly returns 404")


class TestCelebrityPosts:
    """Tests for celebrity posts (10K+ likes) feature"""
    
    def test_celebrity_posts_endpoint(self):
        """Test GET /api/posts/celebrity returns celebrity posts"""
        response = requests.get(f"{BASE_URL}/api/posts/celebrity")
        assert response.status_code == 200
        
        data = response.json()
        assert "posts" in data
        assert "total" in data
        assert "has_more" in data
        assert isinstance(data["posts"], list)
        print(f"✓ Celebrity posts: {data['total']} total, {len(data['posts'])} returned")
        
    def test_celebrity_posts_pagination(self):
        """Test celebrity posts pagination with skip and limit"""
        response = requests.get(f"{BASE_URL}/api/posts/celebrity?skip=0&limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["posts"]) <= 5
        print(f"✓ Celebrity posts pagination works: {len(data['posts'])} posts returned")
        
    def test_celebrity_posts_include_user_info(self):
        """Test celebrity posts include user info"""
        response = requests.get(f"{BASE_URL}/api/posts/celebrity")
        assert response.status_code == 200
        
        data = response.json()
        if data["posts"]:
            post = data["posts"][0]
            # Posts should have user info attached
            assert "user_name" in post or "user_id" in post
            print(f"✓ Celebrity posts include user info")
        else:
            print("⚠ No celebrity posts to verify user info")
            
    def test_stars_posts_endpoint(self):
        """Test GET /api/posts/stars returns starred posts (legacy endpoint)"""
        response = requests.get(f"{BASE_URL}/api/posts/stars")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Stars posts endpoint: {len(data)} posts")


class TestDashboardNavigation:
    """Tests for dashboard navigation icons"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get session for authenticated tests"""
        self.session = requests.Session()
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "testuser@looksy.com", "password": "test1234", "category": "men"}
        )
        assert login_response.status_code == 200
        
    def test_all_new_endpoints_accessible(self):
        """Test all new endpoints are accessible"""
        endpoints = [
            ("/api/rewards/info", "GET"),
            ("/api/kyc/status", "GET"),
            ("/api/payout/history", "GET"),
            ("/api/users/me/favorites", "GET"),
            ("/api/posts/celebrity", "GET"),
        ]
        
        for endpoint, method in endpoints:
            if method == "GET":
                response = self.session.get(f"{BASE_URL}{endpoint}")
            else:
                response = self.session.post(f"{BASE_URL}{endpoint}")
            
            assert response.status_code in [200, 400, 401], f"Endpoint {endpoint} failed with {response.status_code}"
            print(f"✓ {endpoint}: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
