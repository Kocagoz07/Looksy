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

### Session: Jun 17, 2026 — Live currency rate + modular routes

- **Live USD→EUR rate** via `open.er-api.com` (free, no API key). New `/app/backend/currency.py` with in-memory 1-hour TTL cache and a background refresh loop. The sync `usd_to_eur()` helper used by post pricing, earnings, and payout endpoints reads the cached value (no behavioural change for callers). At session time the live rate was **0.8613** (vs the old hardcoded 0.92).
  - `GET /api/currency/rate` (public): returns `{rate, source, fetched_at, ttl_hours}`
  - `POST /api/currency/refresh` (auth): force a rate refresh
- **Refactor**: extracted 4 route modules from `server.py` (3553 → 3211 lines, -342):
  - `/app/backend/routes/outfits.py`
  - `/app/backend/routes/affiliate.py`
  - `/app/backend/routes/payouts_live.py`
  - `/app/backend/routes/currency.py`
  - Shared singletons live in `/app/backend/deps.py`; `server.py` populates them in the startup event, route modules read from there.
- **Stripe webhook polish**: unconfigured provider now returns **503** (with the env-var hint) instead of misleading 400 "Invalid signature".
- **Tested**: 60/60 backend tests pass (`/app/test_reports/iteration_9.json`). Currency live, modular routes verified end-to-end, request-payout regression validates EUR→USD division now uses the live 0.8613 rate.

### Session: Jun 17, 2026 — AI Outfit Studio UX fixes

- **Recent generations are now clickable**: tapping reopens the outfit and restores Occasion/Style/Season/Budget/Colors/Notes form values so users can tweak & regenerate. Backend `GET /api/outfits/{outfit_id}` added (includes original `request` + `affiliate_links`, ownership-checked).
- **Save button**: optimistic UI — toggles to **Saved** instantly with filled bookmark icon, disabled when already saved. Rolls back on failure.
- **Trending pills**: hover state + toast confirmation when style is set; no longer feels inert.
- **Auto-scroll**: after Generate or Reopen, the result card scrolls into view (mobile-friendly).
- **Route ordering bugfix**: moved `GET /api/outfits/{outfit_id}` AFTER literal routes (`/style-profile`, `/trending`, `/options`) so they no longer get shadowed by the parameterized one.
- **Chat list loading bug** (separate session fix): `ChatPage.js` was gating `fetchConversations` on a `user` prop that App never passed → list stuck on "Loading…". Switched to internal `currentUser` populated by `/api/auth/me`.

## What's Been Implemented

### Session: May 22, 2026 (cont.)

**Live Payouts Scaffolded (Stripe Connect Express + PayPal Payouts API):**
- `/app/backend/payouts_providers.py`: `StripeConnectProvider` + `PayPalPayoutsProvider`
  - Both auto-detect configured vs placeholder keys; unconfigured calls return 503 with actionable error
  - Stripe: `create_express_account`, hosted onboarding `AccountLink`, account status (charges/payouts/details + currently_due requirements), EUR `Transfer` to creator account, webhook signature verification
  - PayPal: OAuth2 client-credentials token flow, payout batch creation (`/v1/payments/payouts`), batch status polling, webhook signature verification via `/v1/notifications/verify-webhook-signature`
- `/api/users/me/request-payout` now attempts live transfer when method matches a configured provider; rolls back `payout_points` deduction on failure
- Frontend `PayoutsPage.js`: live providers banner + conditional **Connect Stripe** card
- New endpoints:
  - `GET /api/payouts/providers/status` (public)
  - `POST /api/payouts/stripe/connect` (auth)
  - `POST /api/payouts/stripe/onboarding-link` (auth)
  - `GET /api/payouts/stripe/status` (auth)
  - `POST /api/payouts/stripe/webhook` (Stripe-signed)
  - `POST /api/payouts/paypal/webhook` (PayPal-signed)
- **Required env vars** (paste into `/app/backend/.env` to go live):
  - `STRIPE_API_KEY=sk_live_...` (or `sk_test_...`)
  - `STRIPE_WEBHOOK_SECRET=whsec_...`
  - `STRIPE_RETURN_URL`, `STRIPE_REFRESH_URL` (default uses `FRONTEND_URL`)
  - `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`
  - `PAYPAL_MODE=live` (or `sandbox`)
  - `PAYPAL_WEBHOOK_ID=...`
- **Tested**: 14/14 backend tests pass (`/app/test_reports/iteration_8.json`, `/app/backend/tests/test_live_payouts.py`)

### Session: May 22, 2026

**Completed Features:**

1. **AI Outfit Generator** (`/app/backend/outfit_generator.py`)
   - GPT-4o-mini via emergentintegrations (Emergent LLM Key)
   - Personalized outfits based on occasion / style / season / budget / colors / notes
   - User style profile (favorite_styles, favorite_colors, body_type, avoid, sizes, budget_preference)
   - Outfit history, save-to-collection, trending styles aggregation
   - `/outfit-studio` page (`OutfitGeneratorPage.js`) accessible from Dashboard via `Wand2` icon

2. **Smart Affiliate Engine** (`/app/backend/affiliate_engine.py`)
   - AI-recommended retailers + search queries per outfit item (gpt-4o-mini)
   - Fallback to 5 default retailers (Amazon / ASOS / Zalando / Farfetch / Nordstrom)
   - Trackable affiliate links with click tracking, suspicious-click flagging (reuses fraud_service)
   - Per-user stats: total_links, total_clicks, total_conversions, total_earnings_eur
   - Endpoints auth-gated; outfit/post link lookups filter by ownership to prevent data leaks

**New API Endpoints:**
- Outfits: `POST /api/outfits/generate`, `GET /api/outfits/mine`, `POST /api/outfits/{id}/save`, `GET/PUT /api/outfits/style-profile`, `GET /api/outfits/options`, `GET /api/outfits/trending`
- Affiliate: `POST /api/affiliate/suggest`, `GET /api/affiliate/track/{link_id}` (302 redirect), `GET /api/affiliate/my-links`, `GET /api/affiliate/my-stats`, `GET /api/affiliate/outfit/{outfit_id}`, `GET /api/affiliate/post/{post_id}` (both ownership-filtered)

**Testing:**
- 26/26 backend tests passed (`/app/test_reports/iteration_7.json`, `/app/backend/tests/test_outfit_affiliate.py`)
- Frontend smoke-tested at `/outfit-studio`

---

### Session: April 5, 2026

**Completed Features:**

1. **Real-Time Chat System** - WebSocket-based messaging between users
   - WebSocket endpoint at `/ws/chat` with authentication
   - Direct messaging between users
   - Real-time message delivery and typing indicators
   - Message read receipts and unread count
   - Chat page with conversation list and message thread
   - **In-profile messaging dialog** - Send messages directly from user profile without navigating away

2. **Photo Location Feature** - Location tagging for posts
   - Create custom locations with name and city
   - Search existing locations
   - Trending locations based on post count
   - Add/remove location from posts
   - Location picker component integrated in upload page
   - User location privacy settings
   - Privacy zones support

**New Files Created:**
- `/app/backend/chat.py` - ChatManager class with WebSocket and conversation management
- `/app/backend/location.py` - LocationService class with location CRUD and privacy
- `/app/frontend/src/pages/ChatPage.js` - Full chat page UI
- `/app/frontend/src/components/LocationPicker.js` - Location picker dialog
- `/app/frontend/src/components/MessageDialog.js` - In-profile message dialog
- `/app/frontend/src/contexts/ChatContext.js` - Chat context provider
- `/app/backend/tests/test_chat_location.py` - Comprehensive test suite

**API Endpoints Added:**
- Chat: `POST /api/chat/conversations/direct`, `GET /api/chat/conversations`, `GET/POST /api/chat/conversations/{id}/messages`, `POST /api/chat/conversations/{id}/read`, `DELETE /api/chat/messages/{id}`, `GET /api/chat/unread-count`
- Location: `GET /api/locations/search`, `GET /api/locations/trending`, `GET /api/locations/nearby`, `POST /api/locations`, `GET /api/locations/{id}`, `GET /api/locations/{id}/posts`
- Post Location: `POST /api/posts/{id}/location`, `GET /api/posts/{id}/location`, `DELETE /api/posts/{id}/location`
- User Settings: `GET/PATCH /api/users/me/location-settings`, `POST/DELETE /api/users/me/location-settings/privacy-zones`

**Testing:**
- All 30 backend API tests pass (100% success rate)
- Frontend UI tested: Messages button, Chat page, Location picker
- Test report: `/app/test_reports/iteration_6.json`

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
- [x] Real-Time Chat System
- [x] Photo Location Feature
- [x] In-Profile Message Dialog
- [x] AI Outfit Generator (gpt-4o-mini)
- [x] Smart Affiliate Engine (AI retailer matching + click tracking)

### P1 - Medium Priority
- [ ] Real Stripe/PayPal integration (currently mocked)
- [ ] Real currency conversion API (currently hardcoded)
- [ ] Email sending for magic links (currently dev mode)
- [ ] Verify star calculation logic
- [ ] Photo+Music to Video Feature (design doc ready: `/app/docs/PHOTO_MUSIC_VIDEO_DESIGN.md`)

### P2 - Lower Priority
- [ ] Real-time notifications via WebSockets
- [ ] Post scheduling
- [ ] Analytics dashboard

### P3 - Future/Technical Debt
- [ ] Refactor server.py into modular routers (2600+ lines)
- [ ] Refactor UserProfile.js into smaller components (950+ lines)

---

## Technical Architecture

### Stack
- **Backend:** FastAPI (Python)
- **Frontend:** React with TailwindCSS
- **Database:** MongoDB
- **File Storage:** GridFS
- **AI Integration:** GPT-4o-mini via Emergent LLM Key

### Key Files
- `/app/backend/server.py` - Main API server (2600+ lines)
- `/app/backend/chat.py` - Real-time chat system
- `/app/backend/location.py` - Location tagging service
- `/app/frontend/src/pages/Dashboard.js` - Discover feed, search
- `/app/frontend/src/pages/UserProfile.js` - Profile with rewards section
- `/app/frontend/src/pages/ChatPage.js` - Full chat interface
- `/app/frontend/src/components/CollaborationHub.js` - Minimalist collaboration UI
- `/app/frontend/src/components/BrandVerifiedBadge.js` - Brand verification badge
- `/app/frontend/src/components/LocationPicker.js` - Location picker dialog
- `/app/frontend/src/components/MessageDialog.js` - In-profile messaging

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
