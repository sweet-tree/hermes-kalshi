#!/usr/bin/env python3
"""Current windows: lifecycle clock + quote ages. No password in output."""
from __future__ import annotations

import json
import time

from clock import current_windows
from redis_ro import RedisRO

QUOTE_PREFIX = "kalshi:state:quote:v1:"


def main() -> None:
    r = RedisRO()
    now_s, n_keys, n_events, windows = current_windows(r)
    now_ms = int(time.time() * 1000)
    print("now_s=%d quote_keys=%d events_with_quotes=%d" % (now_s, n_keys, n_events))
    print("CURRENT = lifecycle open<=now<close AND quote keys exist")
    print("(do not SCAN all lifecycle keys — overlapping KXBTCD windows exist)")
    print("")

    for w in windows:
        books = []
        ticks = []
        for mt in w["markets"]:
            raw = r.get(QUOTE_PREFIX + mt)
            if not raw:
                continue
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            book = d.get("book_source_ts_ms")
            tick = d.get("ticker_source_ts_ms")
            if isinstance(book, (int, float)) and book > 0:
                books.append((now_ms - int(book)) / 1000.0)
            if isinstance(tick, (int, float)) and tick > 0:
                ticks.append((now_ms - int(tick)) / 1000.0)
        mb = min(books) if books else None
        mtick = min(ticks) if ticks else None
        print(
            "CURRENT  %s  %s  markets=%d  close_in_s=%s  book_age_s=%s ticker_age_s=%s"
            % (
                w["series"].ljust(12),
                w["event"],
                len(w["markets"]),
                w["close_in_s"],
                "%.2f" % mb if mb is not None else "None",
                "%.2f" % mtick if mtick is not None else "None",
            )
        )
    r.close()
    print("current_events=%d" % len(windows))


if __name__ == "__main__":
    main()
