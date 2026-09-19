#!/usr/bin/env python3
"""Process-level kalshi_state health. No password in output."""
from __future__ import annotations

import json
import time

from redis_ro import RedisRO

FIELDS = (
    "ingest_ts_ms",
    "last_ping_ts_ms",
    "last_ticker_ts_ms",
    "last_book_ts_ms",
    "is_stale",
    "connected_public",
    "io_queue_depth",
)


def main() -> None:
    r = RedisRO()
    raw = r.get("kalshi:state:health:v1")
    r.close()
    if not raw:
        raise SystemExit("no health key")
    d = json.loads(raw)
    now = int(time.time() * 1000)
    for k in FIELDS:
        v = d.get(k)
        if isinstance(v, (int, float)) and k.endswith("_ms"):
            print("%s  age_s=%.2f" % (k, (now - int(v)) / 1000.0))
        else:
            print("%s  %s" % (k, v))


if __name__ == "__main__":
    main()
