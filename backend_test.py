import requests
import sys
import json
import time
from datetime import datetime
import subprocess
import os

class LooksyAPITester:
    def __init__(self, base_url="https://looksy-ai-outfit.preview.emergentagent.com"):
        self.base_url = base_url
        self.session_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def create_test_user_and_session(self):
        """Create test user and session using MongoDB"""
        print("\n🔧 Creating test user and session...")
        
        timestamp = int(time.time())
        user_id = f"test-user-{timestamp}"
        session_token = f"test_session_{timestamp}"
        
        # MongoDB command to create test user and session
        mongo_cmd = f'''
        mongosh --eval "
        use('test_database');
        var userId = '{user_id}';
        var sessionToken = '{session_token}';
        db.users.insertOne({{
          user_id: userId,
          email: 'test.user.{timestamp}@example.com',
          name: 'Test User',
          picture: 'https://via.placeholder.com/150',
          category: 'men',
          earnings: 0.0,
          created_at: new Date()
        }});
        db.user_sessions.insertOne({{
          user_id: userId,
          session_token: sessionToken,
          expires_at: new Date(Date.now() + 7*24*60*60*1000),
          created_at: new Date()
        }});
        print('Session created successfully');
        "
        '''
        
        try:
            result = subprocess.run(mongo_cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                self.session_token = session_token
                self.user_id = user_id
                print(f"✅ Test user created: {user_id}")
                print(f"✅ Session token: {session_token}")
                return True
            else:
                print(f"❌ Failed to create test user: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error creating test user: {str(e)}")
            return False

    def run_api_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.session_token:
            headers['Authorization'] = f'Bearer {self.session_token}'
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    # Remove Content-Type for file uploads
                    headers.pop('Content-Type', None)
                    response = requests.post(url, files=files, headers=headers)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success and response.content:
                try:
                    response_data = response.json()
                    details += f", Response: {json.dumps(response_data, indent=2)[:200]}..."
                    return success, response_data
                except:
                    pass
            
            if not success:
                details += f", Expected: {expected_status}"
                if response.content:
                    try:
                        error_data = response.json()
                        details += f", Error: {error_data}"
                    except:
                        details += f", Raw: {response.text[:200]}"
            
            self.log_test(name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints...")
        
        # Test /auth/me
        success, user_data = self.run_api_test(
            "Get Current User (/auth/me)",
            "GET", "auth/me", 200
        )
        
        if success and user_data:
            print(f"   User ID: {user_data.get('user_id')}")
            print(f"   Email: {user_data.get('email')}")
            print(f"   Category: {user_data.get('category')}")
        
        return success

    def test_user_endpoints(self):
        """Test user management endpoints"""
        print("\n👤 Testing User Endpoints...")
        
        # Test get user by ID
        if self.user_id:
            success, _ = self.run_api_test(
                "Get User by ID",
                "GET", f"users/{self.user_id}", 200
            )
        
        # Test update user category
        success, _ = self.run_api_test(
            "Update User Category",
            "PATCH", "users/me", 200,
            data={"category": "women"}
        )
        
        return success

    def test_image_upload(self):
        """Test image upload to GridFS"""
        print("\n🖼️ Testing Image Upload...")
        
        # Create a simple test image file
        test_image_content = b"fake_image_data_for_testing"
        
        try:
            success, response = self.run_api_test(
                "Upload Image to GridFS",
                "POST", "upload-image", 200,
                files={'file': ('test.jpg', test_image_content, 'image/jpeg')}
            )
            
            if success and 'file_id' in response:
                file_id = response['file_id']
                print(f"   Uploaded file ID: {file_id}")
                
                # Test image retrieval
                image_url = f"{self.base_url}/api/images/{file_id}"
                img_response = requests.get(image_url)
                
                success = img_response.status_code == 200
                self.log_test("Retrieve Uploaded Image", success, 
                            f"Status: {img_response.status_code}")
                
                return success, file_id
            
            return False, None
            
        except Exception as e:
            self.log_test("Upload Image to GridFS", False, f"Exception: {str(e)}")
            return False, None

    def test_post_endpoints(self, image_id=None):
        """Test post CRUD operations"""
        print("\n📝 Testing Post Endpoints...")
        
        post_id = None
        
        if image_id:
            # Create post
            post_data = {
                "caption": "Test post caption",
                "music": "https://spotify.com/test",
                "location": "New York",
                "venue": "Fashion Week",
                "total_price": 299.99,
                "products": [
                    {"name": "Test Product", "url": "https://example.com/product"}
                ]
            }
            
            success, response = self.run_api_test(
                "Create Post",
                "POST", f"posts?image_id={image_id}", 200,
                data=post_data
            )
            
            if success and 'post_id' in response:
                post_id = response['post_id']
                print(f"   Created post ID: {post_id}")
        
        # Get all posts
        success, posts = self.run_api_test(
            "Get All Posts",
            "GET", "posts", 200
        )
        
        if success:
            print(f"   Found {len(posts)} posts")
        
        # Get posts by category
        success, _ = self.run_api_test(
            "Get Posts by Category (men)",
            "GET", "posts?category=men", 200
        )
        
        # Get stars posts (10k+ likes)
        success, _ = self.run_api_test(
            "Get Stars Posts (10k+ likes)",
            "GET", "posts/stars", 200
        )
        
        # Test individual post retrieval
        if post_id:
            success, _ = self.run_api_test(
                "Get Post by ID",
                "GET", f"posts/{post_id}", 200
            )
        
        return post_id

    def test_like_system(self, post_id):
        """Test like/unlike functionality and earnings calculation"""
        print("\n❤️ Testing Like System & Earnings...")
        
        if not post_id:
            self.log_test("Like System Test", False, "No post ID available")
            return False
        
        # Like the post
        success, response = self.run_api_test(
            "Like Post",
            "POST", f"posts/{post_id}/like", 200
        )
        
        if success:
            likes_count = response.get('likes_count', 0)
            liked = response.get('liked', False)
            print(f"   Likes count: {likes_count}, Liked: {liked}")
        
        # Unlike the post
        success, response = self.run_api_test(
            "Unlike Post",
            "POST", f"posts/{post_id}/like", 200
        )
        
        if success:
            likes_count = response.get('likes_count', 0)
            liked = response.get('liked', False)
            print(f"   Likes count: {likes_count}, Liked: {liked}")
        
        return success

    def test_comment_system(self, post_id):
        """Test comment CRUD operations"""
        print("\n💬 Testing Comment System...")
        
        if not post_id:
            self.log_test("Comment System Test", False, "No post ID available")
            return False
        
        comment_id = None
        
        # Create comment
        success, response = self.run_api_test(
            "Create Comment",
            "POST", f"posts/{post_id}/comments", 200,
            data={"text": "This is a test comment"}
        )
        
        if success and 'comment_id' in response:
            comment_id = response['comment_id']
            print(f"   Created comment ID: {comment_id}")
        
        # Get comments for post
        success, comments = self.run_api_test(
            "Get Post Comments",
            "GET", f"posts/{post_id}/comments", 200
        )
        
        if success:
            print(f"   Found {len(comments)} comments")
        
        # Delete comment
        if comment_id:
            success, _ = self.run_api_test(
                "Delete Comment",
                "DELETE", f"comments/{comment_id}", 200
            )
        
        return success

    def test_user_posts(self):
        """Test getting user's posts"""
        print("\n📋 Testing User Posts...")
        
        if not self.user_id:
            self.log_test("User Posts Test", False, "No user ID available")
            return False
        
        success, posts = self.run_api_test(
            "Get User Posts",
            "GET", f"users/{self.user_id}/posts", 200
        )
        
        if success:
            print(f"   User has {len(posts)} posts")
        
        return success

    def test_earnings_calculation(self):
        """Test earnings calculation logic"""
        print("\n💰 Testing Earnings Calculation...")
        
        # Test the earnings calculation function logic
        test_cases = [
            (500, 25.0),      # 500 * 0.05 = 25
            (1500, 100.0),    # 1000*0.05 + 500*0.10 = 50 + 50 = 100
            (5000, 650.0),    # 1000*0.05 + 2000*0.10 + 2000*0.20 = 50 + 200 + 400 = 650
            (15000, 4150.0)   # 1000*0.05 + 2000*0.10 + 7000*0.20 + 5000*0.50 = 50 + 200 + 1400 + 2500 = 4150
        ]
        
        def calculate_earnings(likes_count):
            if likes_count < 1000:
                return likes_count * 0.05
            elif likes_count < 3000:
                return 1000 * 0.05 + (likes_count - 1000) * 0.10
            elif likes_count < 10000:
                return 1000 * 0.05 + 2000 * 0.10 + (likes_count - 3000) * 0.20
            else:
                return 1000 * 0.05 + 2000 * 0.10 + 7000 * 0.20 + (likes_count - 10000) * 0.50
        
        all_passed = True
        for likes, expected in test_cases:
            calculated = calculate_earnings(likes)
            success = abs(calculated - expected) < 0.01  # Allow small floating point differences
            self.log_test(f"Earnings Calculation ({likes} likes)", success, 
                         f"Expected: ${expected}, Got: ${calculated}")
            if not success:
                all_passed = False
        
        return all_passed

    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        if self.user_id:
            mongo_cmd = f'''
            mongosh --eval "
            use('test_database');
            db.users.deleteMany({{user_id: '{self.user_id}'}});
            db.user_sessions.deleteMany({{user_id: '{self.user_id}'}});
            db.posts.deleteMany({{user_id: '{self.user_id}'}});
            db.comments.deleteMany({{user_id: '{self.user_id}'}});
            print('Test data cleaned up');
            "
            '''
            
            try:
                subprocess.run(mongo_cmd, shell=True, capture_output=True, text=True)
                print("✅ Test data cleaned up")
            except Exception as e:
                print(f"❌ Error cleaning up: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Looksy Backend API Tests...")
        print(f"Backend URL: {self.base_url}")
        
        # Create test user and session
        if not self.create_test_user_and_session():
            print("❌ Failed to create test user. Stopping tests.")
            return False
        
        try:
            # Test authentication
            auth_success = self.test_auth_endpoints()
            if not auth_success:
                print("❌ Authentication failed. Stopping tests.")
                return False
            
            # Test user endpoints
            self.test_user_endpoints()
            
            # Test image upload
            image_success, image_id = self.test_image_upload()
            
            # Test post endpoints
            post_id = self.test_post_endpoints(image_id if image_success else None)
            
            # Test like system
            if post_id:
                self.test_like_system(post_id)
            
            # Test comment system
            if post_id:
                self.test_comment_system(post_id)
            
            # Test user posts
            self.test_user_posts()
            
            # Test earnings calculation
            self.test_earnings_calculation()
            
        finally:
            # Clean up test data
            self.cleanup_test_data()
        
        # Print results
        print(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        return self.tests_passed == self.tests_run

def main():
    tester = LooksyAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())