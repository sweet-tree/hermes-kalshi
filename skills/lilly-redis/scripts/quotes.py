#!/usr/bin/env python3
"""BBO for one series: 15m or hourly. Hourly is the ladder, or one named strike.

No password in output. Does not print both series. Does not default to ATM-only.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from clock import current_windows
from redis_ro import RedisRO
from strike import (
    market_for_strike,
    parse_price_live,
    parse_strike,
    select_nearest_market_tickers,
    spot_for_event_ticker,
)

QUOTE_PREFIX = "kalshi:state:quote:v1:"
SPOT_BTC = "price:live:rust:BTC/USDT"
SPOT_ETH = "price:live:rust:ETH/USDT"
LOB_BTC = "lob:btc:snapshot:rust"
LOB_ETH = "lob:eth:snapshot:rust"

SERIES = {
    "15m": "btc_15m",
    "hourly": "btc_hourly",
}


def _lob_mid(raw: bytes | None) -> float | None:
    if not raw:
        return None
    try:
        v = json.loads(raw).get("mid_now")
    except json.JSONDecodeError:
        return None
    if isinstance(v, (int, float)) and v > 0:
        return float(v)
    return None


def _age_s(now_ms: int, ts) -> str:
    if isinstance(ts, (int, float)) and ts > 0:
        return "%.2f" % ((now_ms - int(ts)) / 1000.0)
    return "None"


def _px(v) -> str:
    if isinstance(v, (int, float)):
        return "%.4f" % v
    return "None"


def _print_row(
    mt: str,
    d: dict,
    now_ms: int,
    spot: float | None,
    atm: str | None,
) -> None:
    strike = parse_strike(mt)
    bits = [
        mt,
        "yes_bid=%s" % _px(d.get("yes_bid_dollars")),
        "yes_ask=%s" % _px(d.get("yes_ask_dollars")),
        "integrity=%s" % d.get("integrity"),
        "book_age_s=%s" % _age_s(now_ms, d.get("book_source_ts_ms")),
    ]
    if strike is not None:
        bits.append("strike=%.2f" % strike)
        if spot is not None:
            bits.append("dist=%+.2f" % (strike - spot))
    elif d.get("target_dollars") is not None:
        bits.append("target=%s" % _px(d.get("target_dollars")))
    if atm and mt == atm:
        bits.append("ATM")
    print(" ".join(bits))


def main() -> None:
    p = argparse.ArgumentParser(
        description="Current-window BBO. Pass 15m or hourly; hourly may name a strike."
    )
    p.add_argument("series", choices=("15m", "hourly"))
    p.add_argument(
        "strike",
        nargs="?",
        help="hourly only: ticker, T81299.99, or 81299.99 (exact, no snap)",
    )
    args = p.parse_args()
    if args.series == "15m" and args.strike:
        print("15m is strikeless; do not pass a strike", file=sys.stderr)
        raise SystemExit(2)

    want = SERIES[args.series]
    r = RedisRO()
    now_s, _n_keys, _n_events, windows = current_windows(r)
    btc = parse_price_live(r.get(SPOT_BTC)) or _lob_mid(r.get(LOB_BTC))
    eth = parse_price_live(r.get(SPOT_ETH)) or _lob_mid(r.get(LOB_ETH))
    now_ms = int(time.time() * 1000)

    chosen = [w for w in windows if w["series"] == want]
    if not chosen:
        r.close()
        print("now_s=%d series=%s current=0" % (now_s, args.series))
        raise SystemExit(1)

    for w in chosen:
        markets = list(w["markets"])
        if any(parse_strike(t) is not None for t in markets):
            markets.sort(key=lambda t: parse_strike(t) or 0.0)
        spot = spot_for_event_ticker(w["event"], btc, eth)
        atm_list = select_nearest_market_tickers(markets, 1, spot) if spot is not None else []
        atm = atm_list[0] if atm_list else None

        if args.strike:
            mt = market_for_strike(markets, args.strike)
            if mt is None:
                print(
                    "MISSING series=%s event=%s strike=%s (not in Redis for this window)"
                    % (args.series, w["event"], args.strike)
                )
                print("have " + " ".join(markets))
                continue
            markets = [mt]

        print(
            "series=%s event=%s close_in_s=%s markets=%d spot=%s"
            % (args.series, w["event"], w["close_in_s"], len(w["markets"]), _px(spot))
        )
        n = 0
        for mt in markets:
            raw = r.get(QUOTE_PREFIX + mt)
            if not raw:
                print("MISSING %s" % mt)
                continue
            _print_row(mt, json.loads(raw), now_ms, spot, atm)
            n += 1
        print("quotes=%d" % n)
    r.close()


if __name__ == "__main__":
    main()
