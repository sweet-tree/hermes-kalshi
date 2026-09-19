"""Current Kalshi events: quote keys exist AND lifecycle open<=now<close.

Do not SCAN every lifecycle key — overlapping KXBTCD windows exist that are
not the live subscribed hour.
"""
from __future__ import annotations

import json
import time

from redis_ro import RedisRO
from strike import event_ticker_of

QUOTE_PREFIX = "kalshi:state:quote:v1:"
LIFECYCLE_PREFIX = "kalshi:state:lifecycle:v1:"


def series_of(event: str) -> str:
    if event.startswith("KXBTC15M"):
        return "btc_15m"
    if event.startswith("KXBTCD"):
        return "btc_hourly"
    if event.startswith("KXETH15M"):
        return "eth_15m"
    if event.startswith("KXETHD"):
        return "eth_hourly"
    return "other"


def as_unix_s(ts) -> int | None:
    if not isinstance(ts, (int, float)) or ts <= 0:
        return None
    v = int(ts)
    if v > 10_000_000_000:
        return v // 1000
    return v


def current_windows(r: RedisRO) -> tuple[int, int, list[dict]]:
    keys = r.scan_keys(QUOTE_PREFIX + "*")
    groups: dict[str, list[str]] = {}
    for key in keys:
        mt = key[len(QUOTE_PREFIX) :]
        groups.setdefault(event_ticker_of(mt), []).append(mt)

    now_s = int(time.time())
    current: list[dict] = []
    for ev, markets in groups.items():
        raw = r.get(LIFECYCLE_PREFIX + ev)
        if not raw:
            continue
        try:
            lc = json.loads(raw)
        except json.JSONDecodeError:
            continue
        open_s = as_unix_s(lc.get("open_ts"))
        close_s = as_unix_s(lc.get("close_ts"))
        if open_s is None or close_s is None or not (open_s <= now_s < close_s):
            continue
        current.append(
            {
                "event": ev,
                "series": series_of(ev),
                "markets": sorted(markets),
                "open_s": open_s,
                "close_s": close_s,
                "close_in_s": close_s - now_s,
            }
        )
    current.sort(key=lambda w: (w["series"], w["event"]))
    return now_s, len(keys), len(groups), current
