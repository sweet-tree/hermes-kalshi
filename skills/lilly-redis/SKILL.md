---
name: lilly-redis
description: "Use when Lilly reads live Redis health or quote ages."
version: 0.1.0
author: Dmitry, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [lilly, redis, kalshi, box]
---

# Lilly Redis (read-only)

Live Kalshi state in Redis on this box. This package: SKILL.md + scripts/. Never print the password.

## When to Use

- Book/ticker stale, health, `connected_public`, queue depth
- "Is the ladder live?"

Don't use for: writes, `KEYS *`, DuckLake, placing orders, dumping `requirepass`.

## How

Only these two (this skill's scripts/):

```bash
$HOME/.hermes/skills/devops/lilly-redis/scripts/health.py     # process-level
$HOME/.hermes/skills/devops/lilly-redis/scripts/windows.py    # current events (lifecycle clock)
```

`health.py`: ingest/ping/ticker/book ages, `is_stale`, `connected_public`, `io_queue_depth`.

`windows.py`: **current** windows only — lifecycle `open_ts`/`close_ts` (unix seconds, REST; WS null must not wipe). Event ticker = last `-<suffix>` stripped. Then min book/ticker source age.

Do not treat process-level `last_ticker_ts_ms` or quote SCAN freshness alone as "current event."

AUTH is inside the script (`/home/dmitry/.bogachka/redis/redis.conf`). Do not `cat` that file. Do not pass the password on a command line.

## Read the ages

- `ingest_ts_ms` ~1s = process timer, not quotes
- `last_book_ts_ms` / `last_ticker_ts_ms` ~1s = feed live
- `is_stale` true = book (or ticker if never had a book) past threshold
- `last_ping_ts_ms` may be `None` even when healthy

## Forbidden

- `SET`, `DEL`, `FLUSH*`, `CONFIG`, `SHUTDOWN`
- `KEYS *` or SCAN of the whole quote namespace into chat
- Printing Redis URL or requirepass

## Verification

`health.py` and `windows.py` exit 0 and print ages/event ids, not a password.
