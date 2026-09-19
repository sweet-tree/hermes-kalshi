#!/usr/bin/env python3
"""Current Kalshi windows from Redis. No password in output.

Current event = lifecycle open/close (unix seconds, REST-seeded; WS nulls must
not wipe them). Feed age = quote book/ticker source ts. Event ticker = last
'-' stripped (kalshi_state event_ticker_of).
"""
from pathlib import Path
import json
import socket
import time

pw = None
for line in Path("/home/dmitry/.bogachka/redis/redis.conf").read_text().splitlines():
    if line.startswith("requirepass "):
        pw = line.split(" ", 1)[1].strip().strip('"').strip("'")
        break
if not pw:
    raise SystemExit("no redis password")


def send(s, *parts):
    buf = ("*%d\r\n" % len(parts)).encode()
    for p in parts:
        b = p.encode()
        buf += ("$%d\r\n" % len(b)).encode() + b + b"\r\n"
    s.sendall(buf)


def read_line(s):
    data = b""
    while not data.endswith(b"\r\n"):
        chunk = s.recv(1)
        if not chunk:
            break
        data += chunk
    return data


def read_bulk(s):
    hdr = read_line(s)
    if hdr.startswith(b"-"):
        raise SystemExit(hdr.decode())
    if hdr.startswith(b"$-1"):
        return None
    n = int(hdr[1:-2])
    body = b""
    while len(body) < n + 2:
        body += s.recv(n + 2 - len(body))
    return body[:-2]


def event_ticker_of(market: str) -> str:
    if "-" in market:
        return market.rsplit("-", 1)[0]
    return market


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


def as_unix_s(ts):
    if not isinstance(ts, (int, float)) or ts <= 0:
        return None
    v = int(ts)
    if v > 10_000_000_000:
        return v // 1000
    return v


s = socket.create_connection(("127.0.0.1", 6379), 5)
send(s, "AUTH", pw)
if not read_line(s).startswith(b"+OK"):
    raise SystemExit("redis auth failed")

cursor = "0"
keys = []
while True:
    send(s, "SCAN", cursor, "MATCH", "kalshi:state:quote:v1:*", "COUNT", "200")
    hdr = read_line(s)
    int(hdr[1:-2])
    cursor = read_bulk(s).decode()
    arr = read_line(s)
    nkeys = int(arr[1:-2])
    for _ in range(nkeys):
        k = read_bulk(s)
        if k:
            keys.append(k.decode())
    if cursor == "0":
        break

now_ms = int(time.time() * 1000)
now_s = now_ms // 1000
groups = {}
for key in keys:
    send(s, "GET", key)
    raw = read_bulk(s)
    if not raw:
        continue
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        continue
    mt = d.get("market_ticker") or key.split(":")[-1]
    ev = event_ticker_of(mt)
    g = groups.setdefault(ev, {"n": 0, "book": [], "tick": []})
    g["n"] += 1
    book = d.get("book_source_ts_ms")
    tick = d.get("ticker_source_ts_ms")
    if isinstance(book, (int, float)) and book > 0:
        g["book"].append((now_ms - int(book)) / 1000.0)
    if isinstance(tick, (int, float)) and tick > 0:
        g["tick"].append((now_ms - int(tick)) / 1000.0)

print("now_s=%d quote_keys=%d events_with_quotes=%d" % (now_s, len(keys), len(groups)))
print("CURRENT = lifecycle open<=now<close (REST seconds; WS null does not wipe)")
print("")

current = 0
for ev in sorted(groups, key=lambda e: (series_of(e), e)):
    send(s, "GET", "kalshi:state:lifecycle:v1:" + ev)
    raw = read_bulk(s)
    open_s = close_s = None
    if raw:
        try:
            lc = json.loads(raw)
        except json.JSONDecodeError:
            lc = {}
        open_s = as_unix_s(lc.get("open_ts"))
        close_s = as_unix_s(lc.get("close_ts"))
    is_current = (
        open_s is not None
        and close_s is not None
        and open_s <= now_s < close_s
    )
    if not is_current:
        continue
    current += 1
    g = groups[ev]
    mb = min(g["book"]) if g["book"] else None
    mtick = min(g["tick"]) if g["tick"] else None
    mb_s = "%.2f" % mb if mb is not None else "None"
    mt_s = "%.2f" % mtick if mtick is not None else "None"
    print(
        "CURRENT  %s  %s  markets=%d  close_in_s=%s  book_age_s=%s ticker_age_s=%s"
        % (
            series_of(ev).ljust(12),
            ev,
            g["n"],
            str(close_s - now_s) if close_s else "?",
            mb_s,
            mt_s,
        )
    )

print("current_events=%d" % current)
