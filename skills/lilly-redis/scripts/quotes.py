#!/usr/bin/env python3
"""Executable BBO for the current 15m market and hourly ATM. No password in output.

Hourly ATM = select_nearest_market_tickers(k=1) with live spot — same rule as
kalshi_state strike_util.rs. No spot → no ATM (no median fallback).
15m is strikeless: the one subscribed market, plus target_dollars.
"""
from __future__ import annotations

import json
import time

from clock import current_windows
from redis_ro import RedisRO
from strike import (
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


def _pick_markets(event: str, markets: list[str], btc: float | None, eth: float | None) -> list[str]:
    if any(parse_strike(t) is not None for t in markets):
        spot = spot_for_event_ticker(event, btc, eth)
        return select_nearest_market_tickers(markets, 1, spot)
    return list(markets)


def main() -> None:
    r = RedisRO()
    now_s, n_keys, n_events, windows = current_windows(r)
    btc = parse_price_live(r.get(SPOT_BTC)) or _lob_mid(r.get(LOB_BTC))
    eth = parse_price_live(r.get(SPOT_ETH)) or _lob_mid(r.get(LOB_ETH))
    now_ms = int(time.time() * 1000)

    print("now_s=%d quote_keys=%d events_with_quotes=%d" % (now_s, n_keys, n_events))
    print("spot_btc=%s spot_eth=%s" % (_px(btc), _px(eth)))
    print("QUOTE = current window, 15m all strikeless markets, hourly ATM k=1")
    print("")

    n = 0
    for w in windows:
        chosen = _pick_markets(w["event"], w["markets"], btc, eth)
        if not chosen:
            print(
                "ATM_SKIP  %s  %s  reason=no_spot_or_no_strike  markets=%d"
                % (w["series"].ljust(12), w["event"], len(w["markets"]))
            )
            continue
        for mt in chosen:
            raw = r.get(QUOTE_PREFIX + mt)
            if not raw:
                print("MISSING  %s  %s" % (w["series"].ljust(12), mt))
                continue
            d = json.loads(raw)
            strike = parse_strike(mt)
            extra = ""
            if strike is not None:
                extra = "  strike=%.2f" % strike
            elif d.get("target_dollars") is not None:
                extra = "  target=%s" % _px(d.get("target_dollars"))
            print(
                "QUOTE  %s  %s  yes_bid=%s yes_ask=%s integrity=%s book_age_s=%s%s"
                % (
                    w["series"].ljust(12),
                    mt,
                    _px(d.get("yes_bid_dollars")),
                    _px(d.get("yes_ask_dollars")),
                    d.get("integrity"),
                    _age_s(now_ms, d.get("book_source_ts_ms")),
                    extra,
                )
            )
            n += 1
    r.close()
    print("quotes=%d" % n)


if __name__ == "__main__":
    main()
