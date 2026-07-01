# KB-004: Disk space full / no space left on device

## Symptoms
- Writes fail; the application crashes or refuses new requests.
- Log rotation stops; database refuses to accept writes.

## Key error signatures
- `OSError: [Errno 28] No space left on device`
- `could not extend file ...: No space left on device`
- `write: no space left on device`

## Root cause
The filesystem hosting the app/data/logs is full. Common causes: unrotated
logs, runaway temp files, large core dumps, or an undersized volume.

## Resolution steps
1. Identify usage: `df -h` then `du -sh /var/log/* | sort -h`.
2. Safely remove or compress old logs; enable/repair log rotation.
3. Clear orphaned temp files and old build artifacts.
4. If data legitimately grew, expand the volume.
5. Restart affected services once space is recovered.

## Prevention
- Alert at 80% disk usage.
- Enforce log rotation and retention.
