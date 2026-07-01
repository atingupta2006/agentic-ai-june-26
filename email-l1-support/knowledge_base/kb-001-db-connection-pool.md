# KB-001: Database connection pool exhaustion

## Symptoms
- Application becomes slow or unresponsive under load.
- Users see "500 Internal Server Error" or "service unavailable".
- Requests time out after ~30 seconds.

## Key error signatures
- `HikariPool-1 - Connection is not available, request timed out after 30000ms`
- `org.postgresql.util.PSQLException: FATAL: sorry, too many clients already`
- `TimeoutError: QueuePool limit of size 10 overflow 10 reached`

## Root cause
The connection pool is exhausted: the application opens more concurrent
database connections than the pool (or the database `max_connections`) allows.
Usually caused by connections not being released (leaks) or a traffic spike.

## Resolution steps
1. Confirm current connections: `SELECT count(*) FROM pg_stat_activity;`
2. Check for idle-in-transaction sessions and terminate stuck ones.
3. Increase the pool size **only** after confirming the DB `max_connections`
   can support it (pool size x app instances must be <= max_connections).
4. Fix connection leaks: ensure every borrowed connection is returned in a
   `finally` block / context manager.
5. Add a connection-pool metric + alert so this is caught earlier next time.

## Prevention
- Set sensible pool min/max and a connection `maxLifetime`.
- Load-test before major releases.
