# KB-003: Authentication failures (401) due to token expiry

## Symptoms
- Users are logged out unexpectedly or get "session expired".
- API calls that worked earlier now return 401 Unauthorized.
- Problem appears after a fixed period (e.g. exactly 60 minutes).

## Key error signatures
- `401 Unauthorized`
- `JWT expired at ...; current time: ...`
- `invalid_token: The access token expired`

## Root cause
The access token (e.g. JWT / OAuth bearer token) has expired and the client
is not refreshing it, or the system clock is skewed so tokens appear expired.

## Resolution steps
1. Confirm the token's `exp` claim vs current time (decode the JWT).
2. Implement / fix the refresh-token flow so clients renew before expiry.
3. Check server and client clock sync (NTP). Clock skew > token leeway causes
   valid tokens to be rejected.
4. If using SSO, confirm the identity provider session is still valid.

## Prevention
- Use refresh tokens with a small clock-skew tolerance.
- Monitor 401 rates and alert on spikes.
