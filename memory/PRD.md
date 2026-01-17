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
- Session-based authentication with secure cookies

### User Profiles
- Create accounts with name and profile picture
- Editable bio section
- Followers/Following counts with follow functionality
- Private "Total Earnings" box (visible only to profile owner)
- **AI-powered Collaboration Hub** for managing collaboration requests

### Posts & Engagement
- Upload high-quality photos (1080x1080)
- Posts can include: music links, location, product information with links and total price
- Engagement: Comments (with delete for post owner), Likes, Stars
- Delete button with confirmation for post owner

### Monetization Features
- "Star" category tab for posts with 10,000+ likes
- Earnings based on likes:
  - 0-1000 likes: $0.05 per like
  - 1000-3000 likes: $0.10 per like
  - 3000-10000 likes: $0.20 per like
  - 10000+ likes: $0.50 per like
- Dual currency display (USD and EUR) with automatic conversion
- Payout system with KYC verification, minimum €20 threshold

---

## What's Been Implemented

### Session: January 17, 2026

**Completed:**
1. **Dual Authentication System (P0)**
   - Magic link authentication with email sending
   - Email/password registration and login
   - Session management with secure cookies
   - CORS properly configured for credentials

2. **AI-Powered Collaboration Hub (P0)**
   - Integrated into UserProfile.js
   - Features: AI-powered categorization, priority scoring
   - Search and filter functionality
   - Tabs for All/Unread/Read messages
   - Stats dashboard (Total, Unread, Priority counts)

3. **User Profile Features**
   - Gender-based profile styling (black for men, dark red for women)
   - Bio editing
   - Profile picture upload
   - Earnings display (USD and EUR)
   - Follow/Unfollow functionality

4. **Core Backend APIs**
   - All auth endpoints: `/api/auth/register`, `/api/auth/login`, `/api/auth/send-magic-link`, `/api/auth/verify-magic-link`
   - User endpoints: `/api/users/me`, `/api/users/{user_id}`, `/api/users/{user_id}/follow`
   - Post endpoints: `/api/posts`, `/api/posts/{post_id}`, `/api/posts/{post_id}/like`, `/api/posts/{post_id}/star`
   - Collaboration endpoints: `/api/collaborations/send`, `/api/collaborations/inbox`, `/api/collaborations/{message_id}/read`
   - Comment endpoints: `/api/posts/{post_id}/comments`

5. **Testing**
   - 21 backend API tests (100% pass rate)
   - Frontend UI flow tests (all passed)
   - Test file: `/app/tests/test_looksy_api.py`

**Bug Fixes:**
- Fixed ObjectId serialization in registration endpoint
- Fixed CORS configuration for credentials mode
- Fixed escaped quotes in CollaborationHub.js
- Fixed category filter query typo (" category" → "category")

---

## Prioritized Backlog

### P0 - High Priority (Next Steps)
- [ ] Affiliate/Rewards System: Stars → Payout Points conversion logic

### P1 - Medium Priority
- [ ] Full Payout Integration with Stripe/PayPal
- [ ] KYC verification workflow
- [ ] Real currency conversion API (currently hardcoded rate)

### P2 - Lower Priority
- [ ] Favorites Feature: Bookmark posts, view in profile
- [ ] "Star" Celebrity Tab: Dedicated page for posts with 10,000+ likes
- [ ] Real-time notifications for likes, comments, collaborations

### P3 - Future/Technical Debt
- [ ] Refactor server.py into modular routers (auth.py, users.py, posts.py)
- [ ] Refactor UserProfile.js into smaller components
- [ ] Add email sending for magic links (currently dev mode)

---

## Technical Architecture

### Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React with TailwindCSS
- **Database:** MongoDB
- **File Storage:** GridFS

### Key Files
- `/app/backend/server.py` - Main API server
- `/app/frontend/src/pages/LandingPage.js` - Dual auth login page
- `/app/frontend/src/pages/UserProfile.js` - Profile with CollaborationHub
- `/app/frontend/src/components/CollaborationHub.js` - AI-powered collaboration management

### Third-Party Integrations
- **Resend:** For sending magic link emails (placeholder key)
- **Google Fonts:** Italiana font family
- **bcrypt:** Password hashing

### Test Credentials
- User 1: testuser@looksy.com / test1234 / men / user_899a61a17955
- User 2: newuser456@looksy.com / test1234 / women / user_2e79eca385b6

---

## Mocked/Placeholder Features
- Currency conversion: Uses hardcoded rate (USD_TO_EUR_RATE=0.92)
- Payout system: Placeholder endpoints without real payment provider
- Email sending: Magic links returned in response (dev mode)
