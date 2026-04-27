# Day 3 Auth Verification

Date: 2026-04-24

Scope: Layer 5 auth endpoints from `Full plan.md` and Day 3 of `7-day-catchup-sprint.md`.

Backend status:

```text
fastapi: Up, port 8000
n8n: Up, port 5678
```

Verification results:

| Case | Expected | Actual |
|---|---:|---:|
| `POST /auth/register` | 201 | 201 |
| `POST /auth/login` | 200 + `Set-Cookie: auth-token=...; HttpOnly` | 200 + cookie set |
| `GET /auth/me` with cookie | 200 | 200 |
| `PUT /auth/me` with cookie | 200 | 200 |
| Duplicate `POST /auth/register` | 409 `EMAIL_EXISTS` | 409 `EMAIL_EXISTS` |
| Wrong password `POST /auth/login` | 401 `INVALID_CREDENTIALS` | 401 `INVALID_CREDENTIALS` |
| `POST /auth/logout` | 200 + cleared cookie | 200 + cleared cookie |
| `GET /auth/me` after logout | 401 `INVALID_TOKEN` | 401 `INVALID_TOKEN` |

Cookie proof:

```text
set-cookie: auth-token=<redacted>; HttpOnly; Max-Age=604800; Path=/; SameSite=lax
set-cookie: auth-token=""; expires=Fri, 24 Apr 2026 13:06:56 GMT; Max-Age=0; Path=/; SameSite=lax
```

Result: Day 3 passes with no observed 500s on auth failure paths.
