# Looksy - Fashion Social Media App PRD

## Original Problem Statement
Build a fashion social media application named "Looksy" similar to Instagram with specialized features for fashion content creators.

## Target Audience
- Fashion influencers and content creators
- Fashion enthusiasts looking for style inspiration
- Brands seeking collaboration opportunities with fashion creators

## Core Requirements

### UI/UX Design
- Interface similar to Instagram with white main color
- Font: "Italiana" from Google Fonts
- **Login Page:** Split-screen design
  - Men: Black background with "Spade" icon
  - Women: Dark red (#800020) background with "Ace of Hearts" icon
  - Both sides display "Looksy" and "Fashion Redefined"
- **Profile Pages:** Background color based on gender (black for men, dark red for women)

### Authentication
- **Dual Login System:**
  - Email Magic Link authentication
  - Traditional email/password registration/login
- **SMS OTP Verification** (anti-bot protection):
  - Phone verification required during registration
  - 6-digit OTP sent via Twilio SMS
  - Test mode available for development
- Session-based authentication with secure cookies

### User Profiles
- Create accounts with name and profile picture
- Editable bio section
- Followers/Following counts with follow functionality
- Private "Total Earnings" box (visible only to profile owner)
- **Rewards section** with Stars, Payout Balance, KYC status
- **Minimalist Collaboration Hub** with accept/decline functionality
- **Brand Verified Badge** - Metallic gold "B" with checkmark for verified brand partners

### Posts & Engagement
- Upload high-quality photos (1080x1080)
- Posts can include: music links, location, product information with links and total price
- Engagement: Comments (with delete for post owner), Likes, Stars, **Favorites (Bookmark)**
- Delete button with confirmation for post owner

### Monetization Features
- "Star" category tab for posts with 10,000+ likes
- Earnings based on stars (per post, max 10,000) - **FLAT RATE PER TIER IN EUR**:
  - 0-1000 stars: €0.05 per star (e.g., 500 stars = €25)
  - 1001-5000 stars: €0.10 per star (e.g., 3000 stars = €300)
  - 5001-10000 stars: €0.25 per star (e.g., 10000 stars = €2500)
- Payout system with KYC verification, minimum €20 threshold (Stripe + PayPal)

---

## What's Been Implemented

### Session: March 21, 2026

**Completed Features:**
1. **Security Module Implementation** - Comprehensive security measures against hacker attacks
   - **Rate Limiting**: 100 requests/min general, 10 requests/min for login
   - **Login Attempt Tracking**: Max 5 failed attempts before 15-minute lockout
   - **IP Blocking**: Auto-block after 20 suspicious requests, 24-hour block duration
   - **Security Headers**: X-Frame-Options, X-XSS-Protection, CSP, HSTS, etc.
   - **Input Sanitization**: SQL injection and XSS pattern detection
   - **CAPTCHA Support**: hCaptcha/reCAPTCHA integration ready
   - **Security Logging**: All events logged to database with severity levels

**New Files Created:**
- `/app/backend/security.py` - Complete security module with SecurityManager class

**API Endpoints Added:**
- `GET /api/security/events` - View recent security events
- `GET /api/security/status` - Check security status (blocked IPs, locked accounts)
- `POST /api/security/unblock-ip` - Unblock an IP address
- `POST /api/security/unlock-account` - Unlock a locked account

**Security Features:**
- Progressive lockout warnings (shows remaining attempts)
- Suspicious user agent detection (blocks security scanners)
- Security middleware on all requests
- HTTPS enforced via Strict-Transport-Security

### Session: March 5, 2026

**Completed Features:**
1. **Instagram-Style Mobile Profile Redesign** - Complete UI overhaul to replicate Instagram's profile screen
   - Mobile-first layout with proper spacing and proportions
   - Profile picture with gradient ring, stats row (posts, followers, following)
   - Story Highlights with gradient ring borders (yellow-red-purple)
   - 3-column post grid with square images and 1px spacing
   - Tab navigation (Grid, Reels, Tagged)
   - Post detail modal with image, caption, likes, comments
   - Lazy loading images with IntersectionObserver
   - Empty state for profiles without posts
   - Follow/Following toggle, Message (collaborate) button
   - Edit profile dialog, Rewards button

**Components:**
- `StoryHighlight` - Circular highlight with gradient border
- `AddHighlightButton` - "New" button to create highlights
- `PostGridItem` - Square image with lazy loading and hover overlay
- `PostDetailModal` - Full post view with comments and actions

### Session: March 4, 2026

**Completed Features:**
1. **Brand Verified Badge** - Implemented metallic gold "B" with checkmark SVG badge
   - Displays next to username on profile pages
   - Shows in user search results
   - Visible on post detail page
   - Requires at least one accepted collaboration to activate
   - Backend endpoint: POST `/api/users/{user_id}/brand-verify`
   - Status endpoint: GET `/api/users/{user_id}/brand-status`

**New Files Created:**
- `/app/frontend/src/components/BrandVerifiedBadge.js` - SVG badge component with metallic gold gradient

**Modified Files:**
- `/app/backend/server.py` - Added brand_verified field to User model + brand verification endpoints
- `/app/frontend/src/pages/UserProfile.js` - Badge next to username + "Get Verified" button
- `/app/frontend/src/pages/Dashboard.js` - Badge in search results
- `/app/frontend/src/pages/PostDetail.js` - Badge next to post owner name

### Session: February 21, 2026

**Completed UI/UX Updates:**
1. **Dashboard "Discover" Tab** - Renamed from "All" with compass icon
2. **User Search** - Search dialog to find other users by name/email
3. **Profile Favorites Button** - Moved to header next to Add Post button
4. **Simplified Profile** - Removed payout button, integrated rewards section
5. **Minimalist Collaboration Section** - Collapsible with accept/decline buttons
6. **Accepted Collaborations on Profile** - Shows as badges when accepted
7. **Owner-only Earnings** - Total Earnings only visible to profile owner

**Backend Endpoints Added:**
- `/api/auth/send-otp` - Send OTP to phone number
- `/api/auth/verify-otp` - Verify OTP code
- `/api/auth/register-with-phone` - Register with verified phone
- `/api/users/search` - Search users by name or email
- `/api/collaborations/{id}/accept` - Accept collaboration request
- `/api/collaborations/{id}/decline` - Decline collaboration request
- `/api/collaborations/accepted` - Get accepted collaborations

### Previous Sessions

**Completed Features:**
1. **Dual Authentication System**
2. **SMS OTP Verification** (Twilio) - Anti-bot protection
3. **AI-Powered Collaboration Hub** (GPT-4o-mini)
4. **User Profile Features** (bio, picture, follow system)
5. **Rewards System** (Stars → Payout Points conversion)
6. **KYC Verification**
7. **Payout Integration** (Stripe + PayPal - MOCKED)
8. **Favorites Feature**
9. **Celebrity Stars Page**
10. **User Search**

---

## Prioritized Backlog

### P0 - Completed ✅
- [x] Dual authentication
- [x] AI Collaboration Hub
- [x] Rewards system
- [x] Favorites feature
- [x] Celebrity page
- [x] User search
- [x] Minimalist collaboration UI
- [x] Brand Verified Badge

### P1 - Medium Priority
- [ ] Real Stripe/PayPal integration (currently mocked)
- [ ] Real currency conversion API (currently hardcoded)
- [ ] Email sending for magic links (currently dev mode)
- [ ] Verify star calculation logic

### P2 - Lower Priority
- [ ] Real-time notifications
- [ ] Post scheduling
- [ ] Analytics dashboard

### P3 - Future/Technical Debt
- [ ] Refactor server.py into modular routers
- [ ] Refactor UserProfile.js into smaller components

---

## Technical Architecture

### Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React with TailwindCSS
- **Database:** MongoDB
- **File Storage:** GridFS
- **AI Integration:** GPT-4o-mini via Emergent LLM Key

### Key Files
- `/app/backend/server.py` - Main API server
- `/app/frontend/src/pages/Dashboard.js` - Discover feed, search
- `/app/frontend/src/pages/UserProfile.js` - Profile with rewards section
- `/app/frontend/src/components/CollaborationHub.js` - Minimalist collaboration UI
- `/app/frontend/src/components/BrandVerifiedBadge.js` - Brand verification badge

### Third-Party Integrations
- **Emergent LLM Key:** Universal key for GPT-4o-mini AI features
- **Google Fonts:** Italiana font family
- **bcrypt:** Password hashing

### Test Credentials
- User 1: testuser@looksy.com / test1234 / men / user_899a61a17955 (Brand Verified)
- User 2: newuser456@looksy.com / test1234 / women / user_2e79eca385b6

---

## Mocked/Placeholder Features
- **Stripe/PayPal payouts:** Deducts points but no real transfer
- **KYC verification:** Auto-approves without real identity check
- **Currency conversion:** Uses hardcoded rate (0.92)
- **Email sending:** Magic links returned in response (dev mode)
- **Twilio SMS:** In test mode (returns OTP in response)
