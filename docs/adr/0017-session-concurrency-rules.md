# ADR 0017: Session concurrency rules

- Status: Accepted
- Date: 2026-11-12

## Context

ADR 0016 fixed the frontend session's shape before any code. The refresh token lives in an httpOnly cookie that the backend rotates on every refresh and blacklists on logout (ADR 0014). The session keeps the access token in memory, counts logouts with a generation number, runs one refresh at a time, and makes logout wait for a refresh in flight.

Building it, and Codex's reviews of #45, #46 and #48, showed that this wasn't enough. These cases weren't covered:
- A login still in flight when the user logs out. Its answer brought the token back. It also set a fresh refresh cookie after logout had cleared the old one, so a reload would sign the user back in.
- A refresh that starts after logout has begun. It captures the generation logout already bumped, so the stale check passes. Its answer could bring the token back, and the rotation could leave a valid cookie behind.
- Several requests that get a 401, with some of the 401s arriving after another request's refresh has already finished. Each late one started another refresh, and each refresh rotates the cookie.
- Which query failures are worth retrying. TanStack Query retries every failure three times by default.

These rules now live in code and tests only. They bind iteration 6 (every mutation and query goes through the same client) and any later change to auth.

## Decision

- **A login that started before a logout is discarded.**
  - `login()` notes the generation it started in. If a logout has bumped it by the time the answer comes back, the token is dropped and the status stays `anonymous`. `login()` resolves without signing in.
  - The late answer has also set a new refresh cookie, so the session calls logout again to revoke it. Otherwise a reload would sign the user back in.
- **No refresh is sent while a logout is in progress.**
  - From the moment logout drops the token until its request is done, `refresh()` answers `rejected` without sending a request.
  - A refresh already in flight when logout starts is still awaited (ADR 0016), so the cookie logout revokes is the newest one.
  - Refreshing works again once logout has finished: a `finally` clears the flag.
- **A 401 for a token that's already been replaced skips the refresh.**
  - The fetch wrapper notes the token it sent. On a 401, if the session's token has changed since, another request has already refreshed. The wrapper retries once with the current token, without starting a refresh.
  - Only a 401 for the current token waits for the single-flight refresh, as in ADR 0016. So requests that fail together cause one rotation, even when their 401s arrive after that refresh has finished.
  - Everything else from ADR 0016 stands: one retry at most, nothing for `/api/auth/`, and a request from before a logout never refreshes.
- **Queries retry only when asking again can help.**
  - A 4xx is never retried: it answers the same every time. A 429 retried at once only adds to the throttling. A 401 has already had its refresh and retry in the fetch wrapper.
  - A 5xx, or a request that got no answer, is retried up to twice.
  - This is the query client's default. A hook can override it when it has a reason, and says why.

## Alternatives considered

- **Cancelling the login request at logout** with an AbortSignal. The server may already have processed it and set the cookie, so the revoke is needed either way.
- **Waiting for an in-flight login inside logout,** as logout waits for a refresh. Logout would then depend on a request that can take as long as the server likes, and the login form isn't on screen while signed in anyway.
- **Letting a refresh during logout run and discarding its answer.** The answer can't be told apart by generation, and on the server the rotation leaves a valid cookie that logout may not revoke.
- **Always refreshing on a 401.** Simpler, but every late 401 rotates the cookie again, and every rotation is another chance for two tabs to race (ADR 0014).
- **Comparing the token after the 401 against the token before the refresh,** inside the session. The wrapper already knows which token it sent, which is the simpler check.
- **TanStack Query's default retries.** Three retries of a 404 or a 403 waste requests and delay the error state, and retrying a 429 makes it worse.
- **No retries at all.** A deploy or a dropped connection would show an error that a second try would have avoided.

## Consequences

- Logging out can't be undone by any request, login or refresh that was in flight, or that starts while logout runs. Tests cover each case, with the answers held back until after logout.
- A login that loses to a logout ends without signing in and without an error. The login form isn't shown while signed in, so a user can't normally get there.
- Requests that fail together cause one cookie rotation.
- Iteration 6's hooks inherit the retry rule. An error state for a 4xx shows at once; a 5xx shows after up to two more tries.
- A new way for the session to start a refresh or a login must respect both the generation and the logout-in-progress flag.
