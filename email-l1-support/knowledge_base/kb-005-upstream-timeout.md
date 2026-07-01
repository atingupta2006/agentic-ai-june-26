# KB-005: Upstream/gateway timeouts (502/504)

## Symptoms
- Intermittent "502 Bad Gateway" or "504 Gateway Timeout".
- Some requests succeed; slow endpoints fail.

## Key error signatures
- `504 Gateway Time-out`
- `upstream timed out (110: Connection timed out) while reading response header`
- `requests.exceptions.ReadTimeout`

## Root cause
A downstream/upstream service is slower than the proxy/gateway timeout, or is
overloaded/unavailable, so the gateway gives up waiting.

## Resolution steps
1. Identify the slow upstream from gateway logs (which route/host times out).
2. Check the upstream service health, CPU, and its own dependencies (DB, cache).
3. Right-size the gateway `proxy_read_timeout` only if the upstream is
   legitimately slow; otherwise fix the upstream latency.
4. Add retries with backoff for idempotent calls.
5. Add a circuit breaker to fail fast when the upstream is down.

## Prevention
- Track p95/p99 latency per upstream and alert on regressions.
