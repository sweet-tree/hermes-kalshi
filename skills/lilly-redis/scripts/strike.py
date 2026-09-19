"""Port of kalshi_state strike_util.rs. Keep in lockstep with the crate tests."""
from __future__ import annotations

import os


def parse_strike(ticker: str) -> float | None:
    _, sep, strike = ticker.rpartition("-T")
    if not sep:
        return None
    try:
        return float(strike)
    except ValueError:
        return None


def event_ticker_of(market_ticker: str) -> str:
    if "-" in market_ticker:
        return market_ticker.rsplit("-", 1)[0]
    return market_ticker


def atm_count_for_event(event_ticker: str) -> int:
    is_eth = event_ticker.startswith("KXETHD")
    env = "KALSHI_ATM_STRIKES_ETH" if is_eth else "KALSHI_ATM_STRIKES_BTC"
    raw = os.environ.get(env)
    if raw:
        try:
            n = int(raw)
            if n >= 5:
                return n
        except ValueError:
            pass
    return 5 if is_eth else 11


def select_nearest_market_tickers(
    market_tickers: list[str], k: int, spot: float | None
) -> list[str]:
    if not market_tickers or k == 0:
        return list(market_tickers)
    with_strike = [(t, s) for t in market_tickers if (s := parse_strike(t)) is not None]
    if not with_strike:
        return []
    with_strike.sort(key=lambda x: x[1])
    if len(with_strike) <= k:
        return [t for t, _ in with_strike]
    if spot is None:
        return []
    center_idx = 0
    best = float("inf")
    for idx, (_, strike) in enumerate(with_strike):
        d = abs(strike - spot)
        if d < best:
            best = d
            center_idx = idx
    half = (k - 1) // 2
    start = max(0, center_idx - half)
    end = start + k
    if end > len(with_strike):
        end = len(with_strike)
        start = max(0, end - k)
    return [t for t, _ in with_strike[start:end]]


def distance_from_spot(market_ticker: str, spot: float | None) -> float:
    if spot is None:
        return float("inf")
    strike = parse_strike(market_ticker)
    if strike is None:
        return float("inf")
    return abs(strike - spot)


def parse_price_live(raw: bytes | None) -> float | None:
    """`{px}:{ts}` from price:live:rust:{SYM} — same split as spot.rs."""
    if not raw:
        return None
    text = raw.decode()
    last = text.rfind(":")
    if last <= 0:
        return None
    try:
        v = float(text[:last])
    except ValueError:
        return None
    return v if v > 0 else None


def spot_for_event_ticker(event_ticker: str, btc: float | None, eth: float | None) -> float | None:
    if event_ticker.startswith("KXETHD"):
        return eth
    if event_ticker.startswith("KXBTCD"):
        return btc
    return None


def requested_strike(token: str) -> float | None:
    t = token.strip()
    if t.startswith("KX") and parse_strike(t) is not None:
        return parse_strike(t)
    if t.upper().startswith("T"):
        t = t[1:]
    try:
        return float(t)
    except ValueError:
        return None


def market_for_strike(markets: list[str], token: str) -> str | None:
    """Exact ticker or exact strike among `markets`. No silent nearest-snap."""
    token = token.strip()
    if token in markets:
        return token
    want = requested_strike(token)
    if want is None:
        return None
    hits = [m for m in markets if parse_strike(m) == want]
    if len(hits) == 1:
        return hits[0]
    return None
