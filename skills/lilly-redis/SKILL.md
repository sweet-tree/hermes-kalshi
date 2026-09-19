---
name: lilly-redis
description: "Use when Lilly reads Redis health, windows, or BBO."
version: 0.3.0
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
- Executable yes bid/ask on the current 15m market or hourly ATM

Don't use for: writes, `KEYS *`, DuckLake, placing orders, dumping `requirepass`, dumping all 11 hourly books.

## How

Only these (this skill's `scripts/`, cwd does not matter):

```bash
$HOME/.hermes/skills/devops/lilly-redis/scripts/health.py
$HOME/.hermes/skills/devops/lilly-redis/scripts/windows.py
$HOME/.hermes/skills/devops/lilly-redis/scripts/quotes.py
```

`health.py`: process-level ingest/ping/ticker/book ages, `is_stale`, `connected_public`, `io_queue_depth`.

`windows.py`: **current** = lifecycle `open<=now<close` **and** quote keys exist. Do not SCAN every lifecycle key — unused overlapping `KXBTCD` windows exist.

`quotes.py`: GET `kalshi:state:quote:v1:{ticker}` for the current 15m market(s) and the hourly ATM only. ATM = `select_nearest_market_tickers(k=1)` with live spot (`price:live:rust:BTC/USDT`, same parse as `kalshi_state` `spot.rs`). No spot → no ATM (no median). Print `yes_bid_dollars` / `yes_ask_dollars` / `integrity` / book age. Not the 10-level book.

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
