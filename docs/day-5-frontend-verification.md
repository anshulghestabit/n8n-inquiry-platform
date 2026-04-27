# Day 5 Frontend Verification (Layer 6)

Date: 2026-04-27

Environment:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`

Test account:
- `day5_1777291591@example.com`

## Command checks and results

1. Register user via backend auth API

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"day5_1777291591@example.com","password":"Pass1234!","full_name":"Day Five"}'
```

- Result: `201`
- Body: `{"message":"User created"}`

2. Login user and confirm auth cookie is set

```bash
curl -D /tmp/day5_login_headers.txt -c /tmp/day5_cookies.txt \
  -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"day5_1777291591@example.com","password":"Pass1234!"}'
```

- Result: `200`
- `Set-Cookie` includes `auth-token=...; HttpOnly; Path=/; SameSite=lax`

3. Verify protected dashboard redirect for unauthenticated request

```bash
curl -I http://localhost:3000/dashboard
```

- Result: `307 Temporary Redirect`
- `location: /login`

4. Verify protected dashboard access with valid auth cookie

```bash
curl -I http://localhost:3000/dashboard -H "Cookie: auth-token=<token>"
```

- Result: `200 OK`

5. Verify authenticated backend profile retrieval

```bash
curl http://localhost:8000/auth/me -b /tmp/day5_cookies.txt
```

- Initial check returned `404` (`NOT_FOUND`) immediately after login.
- Retry after short delay returned `200` with profile payload.

## Day 5 acceptance criteria mapping

- Unauthenticated user redirected from dashboard routes: verified (`307` -> `/login`).
- Authenticated user can login and land in dashboard shell: verified (`/auth/login` `200` + cookie, `/dashboard` `200` with cookie).
- API client and cookie-based auth context path exercised against live backend/Supabase.
