# Looksy Auth Testing Playbook

Auth is session-cookie based (`session_token` httpOnly cookie, 7 days, stored in `user_sessions`). Passwords hashed with bcrypt (`$2b$`). Emails are MOCKED: links are logged to `/var/log/supervisor/backend.err.log` with prefix `[MOCK EMAIL]`. `AUTH_DEV_MODE=true` also returns links in API responses.

## MongoDB checks (DB: test_database)
- `db.users.getIndexes()` -> unique `email`
- `db.password_reset_tokens.getIndexes()` / `db.email_verification_tokens.getIndexes()` -> TTL on `expires_at`, unique `token_hash`
- Tokens are stored as SHA-256 hashes, never raw.

## Endpoints
- POST /api/auth/register {email,password(>=8),name,category} -> user with email_verified=false, verification link logged
- POST /api/auth/register-with-phone (OTP flow)
- POST /api/auth/login {email,password,category}
- GET /api/auth/me, POST /api/auth/logout
- POST /api/auth/forgot-password {email} -> generic message (+ reset_link in dev mode, only for existing users); 60s cooldown per user
- POST /api/auth/reset-password {token,new_password} -> single-use, 1h expiry, invalidates all sessions, marks email verified
- POST /api/auth/verify-email {token} -> email_verified=true
- POST /api/auth/resend-verification (auth) -> 60s cooldown; verification_link in dev mode

## Frontend
- Landing page > "Email & Password" tab > "Forgot password?" (data-testid forgot-password-link)
- /reset-password?token=..., /verify-email?token=...
- Dashboard banner `email-verify-banner` shown only when email_verified === false
