# ADR 0006: JWT with an in-memory access token and an httpOnly refresh cookie, served from one origin

- Status: Accepted
- Date: 2026-11-10

## Context

The brief requires JWT. A browser app has to keep tokens somewhere: anything JavaScript can read is exposed to XSS, and anything sent automatically by the browser has to be protected against CSRF.

## Decision

- simplejwt with the `token_blacklist` app.
- Access token: 5 minutes, returned in the response body, kept only in memory.
- Refresh token: httpOnly, `SameSite=Strict` cookie scoped to `/api/auth/`, `Secure` outside local development, rotated on every refresh and blacklisted on logout.
- One origin: nginx serves the React build and proxies `/api` to Django; Vite's proxy does the same in development.

## Alternatives considered

- **Both tokens in localStorage.** Simple, but any injected script can read them.
- **Separate origins with CORS** and a `SameSite=None` refresh cookie. More configuration and a weaker cookie.
- **Session authentication.** The brief requires JWT.

## Consequences

- A page reload triggers a silent refresh before the first API call.
- CSRF exposure is limited to the refresh endpoint, where `SameSite=Strict` blocks cross-site sends and the response can't be read cross-origin.
- Any deployment needs same-origin routing (nginx or a load balancer path rule).
