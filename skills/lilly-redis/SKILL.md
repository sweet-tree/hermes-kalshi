---
name: lilly-redis
description: "Use when Lilly reads Redis health, windows, or BBO."
version: 0.4.0
author: Dmitry, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [lilly, redis, kalshi, box]
---

# Lilly Redis (read-only)

Live Kalshi state in Redis on this box. Package: SKILL.md + scripts/. Never print the password.

## When to Use

- Book/ticker stale, health, `connected_public`, queue depth
- Which 15m / hourly event is live
- Yes bid/ask for **one** series: current 15m, or the hourly ladder, or one hourly strike

Don't use for: writes, `KEYS *`, DuckLake, placing orders, dumping `requirepass`.

## How

```bash
$HOME/.hermes/skills/devops/lilly-redis/scripts/health.py
$HOME/.hermes/skills/devops/lilly-redis/scripts/windows.py
$HOME/.hermes/skills/devops/lilly-redis/scripts/quotes.py 15m
$HOME/.hermes/skills/devops/lilly-redis/scripts/quotes.py hourly
$HOME/.hermes/skills/devops/lilly-redis/scripts/quotes.py hourly 81299.99
```

`quotes.py` requires `15m` or `hourly`. It does not print both. Hourly without a strike prints every quote Redis has for that event (the subscribed ladder), sorted, and marks ATM. Hourly with a strike is **exact** (`81299.99`, `T81299.99`, or full ticker) — no snap to ATM. Missing strike → `MISSING` and the list we do have.

15m is strikeless; do not pass a strike.

Redis only contains strikes `kalshi_state` subscribed. A strike outside that window is not fetchable from this script.

AUTH is inside the client (`/home/dmitry/.bogachka/redis/redis.conf`). Do not `cat` that file. Do not pass the password on a command line.

## Read the ages

- `ingest_ts_ms` ~1s = process timer, not quotes
- `last_book_ts_ms` / `last_ticker_ts_ms` ~1s = feed live
- `is_stale` true = book (or ticker if never had a book) past threshold
- `last_ping_ts_ms` may be `None` even when healthy

## Forbidden

- `SET`, `DEL`, `FLUSH*`, `CONFIG`, `SHUTDOWN`
- `KEYS *` or pasting the whole quote SCAN into chat
- Printing Redis URL or requirepass

## Verification

Scripts exit 0 and print ages / event ids / BBO, not a password.
