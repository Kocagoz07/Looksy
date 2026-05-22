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
