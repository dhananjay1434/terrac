# Portal Session — httpOnly Cookie Migration (V7 P5)

## Why this is documented, not shipped-now

The portal keeps its bearer token in `localStorage` (`portal/src/auth.ts`) —
XSS-readable. The proper fix is an httpOnly cookie (JS literally cannot read
it). BUT the verified deployment topology makes the correct fix the *fragile*
variant, and it can break portal login if mis-timed:

- **Portal and API are separate origins** (render.yaml `dmrv-api` + a separate
  portal deploy) → a session cookie is **cross-site**.
- Backend CORS is `allow_credentials=False` (`app_factory.py:43`) and reads the
  token from `Authorization: Bearer` (`portal/auth.py:103,138`).

A cross-site httpOnly cookie therefore needs `SameSite=None; Secure`, **both
sides on HTTPS**, `allow_credentials=True`, and an exact origin echo. If a demo
runs the portal or API over plain HTTP/LAN, `Secure` cookies won't set and
login breaks. So this is a **post-demo** change, executed when the deploy
topology (HTTPS origins) is pinned. Severity is low (internal verifier tool,
React auto-escapes, opaque token, 401 self-clears), so deferring is safe.

Rejected half-measures: `sessionStorage`/in-memory are still JS-readable by an
active XSS (only marginal), and in-memory adds a refresh=re-login wart. Not
worth shipping — go straight to httpOnly when topology allows.

## Preconditions before executing

1. Portal is served over **HTTPS** at a known origin (e.g.
   `https://dmrv-portal.onrender.com`).
2. API is over **HTTPS** (e.g. `https://dmrv-api.onrender.com`).
3. `DMRV_ALLOWED_ORIGIN` on the backend == the exact portal origin.

## The change (backend + portal), all test-gated

### Backend
1. **Login sets the cookie** (`backend/portal/routes.py` `login`): in addition
   to (or instead of) returning the token in the body, set:
   ```
   response.set_cookie(
       key="dmrv_portal_session", value=<token>,
       httponly=True, secure=True, samesite="none",
       max_age=<session ttl seconds>, path="/",
   )
   ```
2. **Read the cookie** (`backend/portal/auth.py` `get_current_user` /
   `require_role`): resolve the token from the `dmrv_portal_session` cookie
   FIRST, then fall back to the `Authorization: Bearer` header (keeps device/
   test callers and a transition window working). Same hashed-token lookup.
3. **Logout clears it** (`/logout`): `response.delete_cookie("dmrv_portal_session", path="/")`.
4. **CORS** (`backend/app_factory.py`): `allow_credentials=True` and keep
   `allow_origins=[allowed_origin]` (NEVER `*` with credentials). Confirm
   `DMRV_ALLOWED_ORIGIN` is set.

### Portal
5. **Stop storing the token** (`portal/src/auth.ts`): drop
   `localStorage.setItem(TOKEN_KEY, ...)`. Keep only the role (non-sensitive)
   for UI gating, or fetch role from a `/me` endpoint.
6. **Send credentials** (`portal/src/api.ts`): add `credentials: "include"` to
   every fetch; stop attaching the `Authorization` header (the cookie rides
   automatically). Keep the 401 → clearSession → redirect behavior.

### Tests
- Backend: `/login` sets an `HttpOnly; Secure; SameSite=None` cookie; an authed
  request works via the cookie alone (no Authorization header); `/logout`
  clears it; a request with neither cookie nor header → 401.
- Portal: after login the token is NOT in `localStorage`; API calls send
  `credentials: "include"`; a 401 still redirects to login.

### Gate
`python -m pytest backend/tests/test_portal_auth.py` + full backend suite;
portal `npm test -- --run` + `npm run typecheck` + `npm run build`.

**Commit:** `fix(portal): move portal session to an httpOnly cookie (XSS token theft)`

## Interim state (until executed)
localStorage token stays. Compensating controls already in place: React output
escaping (no known injection sink in the portal), an opaque non-JWT token, and
401-clears-session. Acceptable for an internal verifier tool short-term.
