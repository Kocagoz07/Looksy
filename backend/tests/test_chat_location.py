"""
Test suite for Chat System and Location Feature
Tests: conversations, messages, location CRUD, post location tagging
Uses Bearer token authentication for API calls
"""

import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')

# Test data prefix for cleanup
TEST_PREFIX = "TEST_CHAT_LOC_"


# Global session and user data
_session1 = None
_session2 = None
_user1_id = None
_user2_id = None
_token1 = None
_token2 = None
_conversation_id = None
_message_id = None
_location_id = None
_post_id = None
_zone_id = None


def setup_module(module):
    """Setup test users before running tests"""
    global _session1, _session2, _user1_id, _user2_id, _token1, _token2
    
    unique_id = uuid.uuid4().hex[:8]
    
    # Create session 1 and register user 1
    _session1 = requests.Session()
    _session1.headers.update({"Content-Type": "application/json"})
    
    email1 = f"{TEST_PREFIX}user1_{unique_id}@test.com"
    
    response = _session1.post(f"{BASE_URL}/api/auth/register", json={
        "email": email1,
        "password": "testpass123",
        "name": f"{TEST_PREFIX}User1",
        "category": "men"
    })
    
    if response.status_code == 200:
        _user1_id = response.json()["user_id"]
        # Extract session token from Set-Cookie header
        cookies = response.cookies
        _token1 = cookies.get("session_token")
        if _token1:
            _session1.headers.update({"Authorization": f"Bearer {_token1}"})
        print(f"Created user1: {_user1_id}, token: {_token1[:20] if _token1 else 'None'}...")
    else:
        print(f"User1 registration failed: {response.text}")
    
    # Create session 2 and register user 2
    _session2 = requests.Session()
    _session2.headers.update({"Content-Type": "application/json"})
    
    email2 = f"{TEST_PREFIX}user2_{unique_id}@test.com"
    
    response = _session2.post(f"{BASE_URL}/api/auth/register", json={
        "email": email2,
        "password": "testpass123",
        "name": f"{TEST_PREFIX}User2",
        "category": "women"
    })
    
    if response.status_code == 200:
        _user2_id = response.json()["user_id"]
        cookies = response.cookies
        _token2 = cookies.get("session_token")
        if _token2:
            _session2.headers.update({"Authorization": f"Bearer {_token2}"})
        print(f"Created user2: {_user2_id}, token: {_token2[:20] if _token2 else 'None'}...")
    else:
        print(f"User2 registration failed: {response.text}")


# ==================== CHAT SYSTEM TESTS ====================

class TestChatSystem:
    """Test Chat System endpoints"""
    
    def test_01_create_direct_conversation(self):
        """Test creating a direct conversation between two users"""
        global _conversation_id
        
        response = _session1.post(f"{BASE_URL}/api/chat/conversations/direct", json={
            "user_id": _user2_id
        })
        
        assert response.status_code == 200, f"Failed to create conversation: {response.text}"
        data = response.json()
        
        assert "conversation_id" in data
        assert data["type"] == "direct"
        assert "participants" in data
        assert len(data["participants"]) == 2
        
        _conversation_id = data["conversation_id"]
        print(f"Created conversation: {_conversation_id}")
    
    def test_02_cannot_chat_with_self(self):
        """Test that user cannot create conversation with themselves"""
        response = _session1.post(f"{BASE_URL}/api/chat/conversations/direct", json={
            "user_id": _user1_id
        })
        
        assert response.status_code == 400
        assert "yourself" in response.json().get("detail", "").lower()
    
    def test_03_get_conversations_list(self):
        """Test getting user's conversations list"""
        response = _session1.get(f"{BASE_URL}/api/chat/conversations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conversations" in data
        assert isinstance(data["conversations"], list)
        assert len(data["conversations"]) >= 1
        
        conv = data["conversations"][0]
        assert "conversation_id" in conv
        assert "participants" in conv
        print(f"User has {len(data['conversations'])} conversations")
    
    def test_04_send_message(self):
        """Test sending a message in a conversation"""
        global _message_id
        
        message_content = f"{TEST_PREFIX}Hello from test at {time.time()}"
        
        response = _session1.post(
            f"{BASE_URL}/api/chat/conversations/{_conversation_id}/messages",
            json={"content": message_content}
        )
        
        assert response.status_code == 200, f"Failed to send message: {response.text}"
        data = response.json()
        
        assert "message_id" in data
        assert data["content"] == message_content
        assert data["sender_id"] == _user1_id
        assert data["conversation_id"] == _conversation_id
        
        _message_id = data["message_id"]
        print(f"Sent message: {_message_id}")
    
    def test_05_get_messages(self):
        """Test getting messages in a conversation"""
        response = _session1.get(
            f"{BASE_URL}/api/chat/conversations/{_conversation_id}/messages"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "messages" in data
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) >= 1
        
        msg = data["messages"][-1]
        assert "message_id" in msg
        assert "content" in msg
        assert "sender_id" in msg
        assert "created_at" in msg
        print(f"Conversation has {len(data['messages'])} messages")
    
    def test_06_mark_messages_read(self):
        """Test marking messages as read"""
        response = _session2.post(
            f"{BASE_URL}/api/chat/conversations/{_conversation_id}/read"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("marked_read") == True
    
    def test_07_get_unread_count(self):
        """Test getting unread message count"""
        response = _session1.get(f"{BASE_URL}/api/chat/unread-count")
        
        assert response.status_code == 200
        data = response.json()
        assert "unread_count" in data
        assert isinstance(data["unread_count"], int)
        print(f"Unread count: {data['unread_count']}")
    
    def test_08_get_specific_conversation(self):
        """Test getting a specific conversation by ID"""
        response = _session1.get(
            f"{BASE_URL}/api/chat/conversations/{_conversation_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["conversation_id"] == _conversation_id
        assert "other_user" in data
        assert data["other_user"]["user_id"] == _user2_id
    
    def test_09_conversation_not_found(self):
        """Test accessing non-existent conversation"""
        response = _session1.get(
            f"{BASE_URL}/api/chat/conversations/conv_nonexistent123"
        )
        
        assert response.status_code == 404
    
    def test_10_unauthenticated_access(self):
        """Test that unauthenticated requests are rejected"""
        s = requests.Session()
        response = s.get(f"{BASE_URL}/api/chat/conversations")
        
        assert response.status_code == 401
    
    def test_11_user2_can_see_conversation(self):
        """Test that user2 can also see the conversation"""
        response = _session2.get(f"{BASE_URL}/api/chat/conversations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conversations" in data
        assert len(data["conversations"]) >= 1
        
        # Find our conversation
        conv_ids = [c["conversation_id"] for c in data["conversations"]]
        assert _conversation_id in conv_ids
    
    def test_12_user2_can_send_message(self):
        """Test that user2 can send a message in the conversation"""
        message_content = f"{TEST_PREFIX}Reply from user2 at {time.time()}"
        
        response = _session2.post(
            f"{BASE_URL}/api/chat/conversations/{_conversation_id}/messages",
            json={"content": message_content}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["sender_id"] == _user2_id
        assert data["content"] == message_content


# ==================== LOCATION SYSTEM TESTS ====================

class TestLocationSystem:
    """Test Location Feature endpoints"""
    
    def test_01_get_trending_locations(self):
        """Test getting trending locations"""
        response = _session1.get(f"{BASE_URL}/api/locations/trending", params={
            "limit": 10
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        assert isinstance(data["locations"], list)
        print(f"Trending locations: {len(data['locations'])}")
    
    def test_02_search_locations_empty(self):
        """Test searching locations with no results"""
        response = _session1.get(f"{BASE_URL}/api/locations/search", params={
            "q": "nonexistentlocation12345"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        assert isinstance(data["locations"], list)
    
    def test_03_create_custom_location(self):
        """Test creating a custom location"""
        global _location_id
        
        location_name = f"{TEST_PREFIX}Test Location {uuid.uuid4().hex[:6]}"
        
        response = _session1.post(f"{BASE_URL}/api/locations", json={
            "name": location_name,
            "city": "Test City",
            "country": "Test Country"
        })
        
        assert response.status_code == 200, f"Failed to create location: {response.text}"
        data = response.json()
        
        assert "location_id" in data
        assert data["name"] == location_name
        assert data["address"]["city"] == "Test City"
        assert data["category"] == "custom"
        
        _location_id = data["location_id"]
        print(f"Created location: {_location_id}")
    
    def test_04_create_location_with_coordinates(self):
        """Test creating a location with coordinates"""
        location_name = f"{TEST_PREFIX}Geo Location {uuid.uuid4().hex[:6]}"
        
        response = _session1.post(f"{BASE_URL}/api/locations", json={
            "name": location_name,
            "city": "New York",
            "country": "USA",
            "latitude": 40.7128,
            "longitude": -74.0060
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert "location_id" in data
        assert data["coordinates"] is not None
        assert data["coordinates"]["type"] == "Point"
    
    def test_05_get_location_by_id(self):
        """Test getting a location by ID"""
        response = _session1.get(f"{BASE_URL}/api/locations/{_location_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["location_id"] == _location_id
        assert "name" in data
        assert "address" in data
    
    def test_06_location_not_found(self):
        """Test getting non-existent location"""
        response = _session1.get(f"{BASE_URL}/api/locations/loc_nonexistent123")
        
        assert response.status_code == 404
    
    def test_07_search_locations_with_query(self):
        """Test searching locations with a query"""
        response = _session1.get(f"{BASE_URL}/api/locations/search", params={
            "q": TEST_PREFIX
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data
        print(f"Found {len(data['locations'])} locations matching query")
    
    def test_08_get_user_location_settings(self):
        """Test getting user's location settings"""
        response = _session1.get(f"{BASE_URL}/api/users/me/location-settings")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user_id" in data
        assert "default_privacy" in data
        assert "privacy_zones" in data
        assert "saved_locations" in data
        
        assert data["default_privacy"]["precision_level"] == "neighborhood"
    
    def test_09_update_location_settings(self):
        """Test updating user's location settings"""
        response = _session1.patch(f"{BASE_URL}/api/users/me/location-settings", json={
            "default_privacy": {
                "precision_level": "city",
                "show_on_map": False,
                "show_in_location_feed": True
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["default_privacy"]["precision_level"] == "city"
        assert data["default_privacy"]["show_on_map"] == False
    
    def test_10_save_location(self):
        """Test saving a location to favorites"""
        response = _session1.post(
            f"{BASE_URL}/api/users/me/saved-locations/{_location_id}",
            params={"nickname": "My Test Place"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["location_id"] == _location_id
        assert data["nickname"] == "My Test Place"
    
    def test_11_unsave_location(self):
        """Test removing a location from favorites"""
        response = _session1.delete(
            f"{BASE_URL}/api/users/me/saved-locations/{_location_id}"
        )
        
        assert response.status_code == 200


# ==================== PRIVACY ZONES TESTS ====================

class TestPrivacyZones:
    """Test privacy zone functionality"""
    
    def test_01_add_privacy_zone(self):
        """Test adding a privacy zone"""
        global _zone_id
        
        response = _session1.post(
            f"{BASE_URL}/api/users/me/location-settings/privacy-zones",
            json={
                "name": f"{TEST_PREFIX}Home Zone",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "radius_meters": 500,
                "action": "fuzz_to_city"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "zone_id" in data
        assert data["name"] == f"{TEST_PREFIX}Home Zone"
        assert data["radius_meters"] == 500
        
        _zone_id = data["zone_id"]
    
    def test_02_remove_privacy_zone(self):
        """Test removing a privacy zone"""
        response = _session1.delete(
            f"{BASE_URL}/api/users/me/location-settings/privacy-zones/{_zone_id}"
        )
        
        assert response.status_code == 200


# ==================== POST LOCATION INTEGRATION TESTS ====================

class TestPostLocationIntegration:
    """Test adding/removing locations from posts"""
    
    def test_01_create_post_for_location_test(self):
        """Create a test post for location testing"""
        global _post_id
        
        # Create a minimal test image
        import io
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_bytes.seek(0)
            
            # Upload image - need to remove Content-Type for multipart
            headers = {"Authorization": f"Bearer {_token1}"}
            
            upload_response = requests.post(
                f"{BASE_URL}/api/upload-image",
                files={"file": ("test.jpg", img_bytes, "image/jpeg")},
                headers=headers
            )
            
            if upload_response.status_code == 200:
                file_id = upload_response.json()["file_id"]
                
                # Create a post
                post_response = _session1.post(
                    f"{BASE_URL}/api/posts",
                    params={"image_id": file_id},
                    json={
                        "caption": f"{TEST_PREFIX}Test post for location"
                    }
                )
                
                if post_response.status_code == 200:
                    _post_id = post_response.json()["post_id"]
                    print(f"Created test post: {_post_id}")
                else:
                    print(f"Failed to create post: {post_response.text}")
            else:
                print(f"Failed to upload image: {upload_response.text}")
        except ImportError:
            pytest.skip("PIL not available for image creation")
    
    def test_02_add_location_to_post_by_id(self):
        """Test adding a location to a post using location_id"""
        if not _post_id:
            pytest.skip("No test post available")
        
        # First create a location
        loc_response = _session1.post(f"{BASE_URL}/api/locations", json={
            "name": f"{TEST_PREFIX}Post Location {uuid.uuid4().hex[:6]}",
            "city": "Fashion City"
        })
        
        if loc_response.status_code != 200:
            pytest.skip("Could not create location")
        
        location_id = loc_response.json()["location_id"]
        
        # Add location to post
        response = _session1.post(
            f"{BASE_URL}/api/posts/{_post_id}/location",
            json={
                "location_id": location_id,
                "privacy_level": "neighborhood"
            }
        )
        
        assert response.status_code == 200, f"Failed to add location: {response.text}"
        data = response.json()
        
        assert data["post_id"] == _post_id
        assert "location" in data
        assert data["location"]["location_id"] == location_id
    
    def test_03_get_post_location(self):
        """Test getting location info for a post"""
        if not _post_id:
            pytest.skip("No test post available")
        
        response = _session1.get(
            f"{BASE_URL}/api/posts/{_post_id}/location"
        )
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "post_id" in data
            assert "location_id" in data
    
    def test_04_remove_location_from_post(self):
        """Test removing location from a post"""
        if not _post_id:
            pytest.skip("No test post available")
        
        response = _session1.delete(
            f"{BASE_URL}/api/posts/{_post_id}/location"
        )
        
        assert response.status_code in [200, 404]
    
    def test_05_add_location_by_name(self):
        """Test adding a location to a post using location_name"""
        if not _post_id:
            pytest.skip("No test post available")
        
        # Add by name
        response = _session1.post(
            f"{BASE_URL}/api/posts/{_post_id}/location",
            json={
                "location_name": f"{TEST_PREFIX}New Place {uuid.uuid4().hex[:6]}",
                "city": "New City",
                "privacy_level": "city"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "location" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
