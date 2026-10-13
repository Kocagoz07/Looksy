# Looksy - Test Credentials

These credentials are used by the testing agent and for E2E validation.

## Active Test Users

| Field | Value |
|---|---|
| Email | testuser@looksy.com |
| Password | test1234 |
| Category | men (also works for women — required field on login) |
| User ID | user_899a61a17955 |
| Notes | Brand-verified. Has 1+ AI-generated outfits + affiliate links. |

| Field | Value |
|---|---|
| Email | newuser456@looksy.com |
| Password | test1234 |
| Category | women |
| User ID | user_2e79eca385b6 |

## Auth notes
- Passwords must be >= 8 chars for new registrations / resets.
- Both seeded users have no `email_verified` field (legacy = treated as verified, no banner). New registrations start with email_verified=false.
- Emails are MOCKED: reset/verify links are logged in backend.err.log ("[MOCK EMAIL]") and returned in API responses because AUTH_DEV_MODE=true.
- Do NOT reset the passwords of the two seeded users above; register fresh qa_*@looksy.com users for reset-flow tests.
- See /app/auth_testing.md for all auth endpoints.

## Login Endpoint

```bash
POST /api/auth/login
Content-Type: application/json

{
  "email": "testuser@looksy.com",
  "password": "test1234",
  "category": "men"
}
```

Session cookie is returned and must be reused for authenticated endpoints (use `withCredentials: true` in axios or `-c/-b` cookie jar with curl).
