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

### Session: Oct 14, 2026 — Story product tags + DM inbox
- **Shop the look on stories**: up to 5 products (name, link, optional € price) per story, edited in StoryComposer; adding a post to story opens the composer pre-filled with the post's product links (editable). Viewer shows product chips; tap pauses the story and opens a product card (name, price, store) with "Buy now" → `/api/affiliate/track/{link_id}` (click tracked in `affiliate_links` with `story_id`). Owner sees per-product click counts in the "Seen by" sheet.
- **DM inbox**: header Messages button with unread badge → /chat. After sharing a post via DM the user is taken to that conversation (or /chat for multiple recipients).
- Testing: iteration_13 — backend 12/12, frontend 6/6 phases passed.
- Brand hidden on story links: product card shows "Product Link" instead of store/domain; composer shows filled links as a "Product Link" pill (Change to edit). API no longer returns `retailer` for story products (kept internally in affiliate_links).
- Same on posts: PostDetail product rows show name + "PRODUCT LINK"; links go through `GET /api/posts/{post_id}/products/{index}/go` (302, http/https only, store URL never shown on hover). Non-owner clicks are logged in `post_product_clicks`; the owner sees "N clicks" per product (`GET /api/posts/{post_id}/product-clicks`, owner-only). Upload screen product list shows "Product Link" instead of the URL.

### Session: Oct 13, 2026 (cont. 2) — Stories, chat reactions, Discover feed
- **Stories** (`routes/stories.py`, `components/stories/*`): 24h TTL stories (gallery upload with caption, or "Add to your story" from Share dialog). Story rings above the home feed (own + followed, gradient = unseen, grey = seen), fullscreen viewer (5s auto-advance, tap left/right, hold to pause, Esc), owner "Seen by N" viewer list + delete.
- **Chat quick reactions** on shared-post cards: double tap = ❤️ (burst animation), long press = 6-emoji picker; one reaction per user (toggle/replace), real-time WS `message:reaction`, notification type `reaction` to sender.
- **Home feed** (`routes/feed.py`, `HomeFeed.js`): Following / Discover tabs; Following = followed + own posts, with "Popular for you" section when < 6 posts; Discover = popular (likes + 2×stars, last 14 days, user's category first, then filled from all-time/other categories). Men/Women/Stars tabs unchanged.
- Testing: iteration_12 — backend 28/28, frontend 10/10 flows passed.

### Session: Oct 13, 2026 (cont.) — Share post via DM
- Share (paper-plane) button on feed PostCard and PostDetail opens `SharePostDialog`: followers/following list + name search, multi-select (max 10), optional note, sends post into each recipient's direct chat.
- Backend `routes/share.py`: `GET /api/share/recipients`, `POST /api/posts/{post_id}/share`; messages type `post_share` with `shared_post` payload; real-time WS broadcast + recipient notification "shared a post with you".
- Chat (ChatPage + MessageDialog) renders shared posts as tappable preview cards → /post/{id}.
- No share counter (per user choice). Pruned leftover TEST_* posts. Testing: iteration_11 — 15/15 backend + all UI flows passed.

### Session: Oct 13, 2026 — Auth hardening, Claude caption writer, Notifications
- **Auth hardening** (`routes/auth_extras.py`): Forgot password → reset link (1h, single-use, SHA-256 hashed tokens, TTL index, 60s cooldown, invalidates all sessions on reset). Email verification on sign-up (`email_verified=false` on register, `/verify-email` page, resend with cooldown, dashboard banner). Password min 8 chars, unique `users.email` index, 422 error formatting on frontend. Emails are **MOCKED** (logged as `[MOCK EMAIL]`; links returned when `AUTH_DEV_MODE=true`).
- **AI Caption Writer (Claude Sonnet 4.5)** (`routes/captions.py`, `AICaptionWriter.js`): on /upload, 5 tones, optional photo vision, streams via SSE, returns 3 captions + toggleable hashtags, saved to `caption_generations`. Upgraded emergentintegrations to 0.2.2 (streaming).
- **Notifications**: emitted for like, star, comment, follow, chat message (dedupe for unread like/star/follow, no self-notify). `NotificationBell` in Dashboard header (30s polling badge, popover feed, mark-all-read on open, click-through navigation).
- Testing: iteration_10 — 21/21 backend + 12/12 UI flows passed.

### Session: Jul 3, 2026 — Error sweep + PayPal live in sandbox

- **PayPal Payouts wired up in sandbox** end-to-end. Real OAuth token flow works, first sandbox payout produced batch `XY6JK5EHQ75U2` (20 EUR, PROCESSING). `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE=sandbox`, `PAYPAL_WEBHOOK_ID=WDXYJTUMR9LWQ` set in `/app/backend/.env`. Webhook endpoint pre-flighted (reachable, signature-verified via PayPal's verify-webhook-signature API). Stripe Connect still awaiting `sk_test_...` / `sk_live_...`.
- **bcrypt log-noise fix**: passlib was crashing on `bcrypt.__about__` (removed in bcrypt 4.1). Pinned `bcrypt==4.0.1` — login logs are now warning-free. `requirements.txt` frozen.
- **Frontend audio-fingerprint fix**: removed the AudioContext-based fingerprint (blocked by browsers without user gesture + `ScriptProcessorNode` deprecated). Canvas + WebGL + hardware + screen dimensions still provide fraud-detection uniqueness. Frontend console is now clean.
- **Test state-agnosticism**: 5 stale assertions in `test_live_payouts.py` + `test_currency_refactor.py` hard-coded "both providers unconfigured". Refactored to auto-skip / branch on `/api/payouts/providers/status` output so the suite stays green regardless of which providers are configured.
- **Broad endpoint sweep**: 18/18 core endpoints return non-5xx (auth, posts, celebrity, payouts, favorites, outfits, affiliate, currency, chat, locations, users search).
- **Code quality**: fixed 2 F541 f-string-without-placeholder issues in `outfit_generator.py`; removed unused `seeded` var.
- **All 113 backend tests pass**.

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
- [x] Forgot/Reset password + email verification
- [x] AI Caption + Hashtag Writer (Claude Sonnet 4.5)
- [x] Notifications (bell + feed)
- [x] Share post via DM
- [x] Stories (24h) + viewer list
- [x] Chat quick reactions on shared posts
- [x] Following / Discover feed + Popular for you
- [x] Story product tags (Shop the look) + click tracking
- [x] DM inbox button
- [x] Live currency rate + PayPal Payouts (sandbox)

### P0 - Next

### P1 - Medium Priority
- [ ] Stripe Connect payouts (awaiting live keys)
- [ ] Real email delivery (magic links, password reset, verification) — set AUTH_DEV_MODE=false once wired
- [ ] Verify star calculation logic
- [ ] Photo+Music to Video Feature (design doc ready: `/app/docs/PHOTO_MUSIC_VIDEO_DESIGN.md`)

### P2 - Lower Priority
- [ ] Push notifications over WebSockets (currently 30s polling)
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
- **Emergent LLM Key:** GPT-4o-mini (collab/outfits) + Claude Sonnet 4.5 (captions)
- **Google Fonts:** Italiana font family
- **bcrypt:** Password hashing

### Test Credentials
- User 1: testuser@looksy.com / test1234 / men / user_899a61a17955 (Brand Verified)
- User 2: newuser456@looksy.com / test1234 / women / user_2e79eca385b6

---

## Mocked/Placeholder Features
- **Stripe/PayPal payouts:** Deducts points but no real transfer
- **KYC verification:** Auto-approves without real identity check
- **Email sending:** MOCKED — magic links, reset & verification links logged / returned in response (AUTH_DEV_MODE=true)
- **Twilio SMS:** In test mode (returns OTP in response)
