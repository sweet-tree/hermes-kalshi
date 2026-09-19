#!/usr/bin/env python3
from pathlib import Path
import json, socket, time

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

s = socket.create_connection(("127.0.0.1", 6379), 5)
send(s, "AUTH", pw)
auth = read_line(s)
if not auth.startswith(b"+OK"):
    raise SystemExit("redis auth failed")
send(s, "GET", "kalshi:state:health:v1")
hdr = read_line(s)
if hdr.startswith(b"-"):
    raise SystemExit(hdr.decode())
n = int(hdr[1:-2])
if n < 0:
    raise SystemExit("no health key")
body = b""
while len(body) < n + 2:
    body += s.recv(n + 2 - len(body))
d = json.loads(body[:-2])
now = int(time.time() * 1000)
for k in ("ingest_ts_ms", "last_ping_ts_ms", "last_ticker_ts_ms", "last_book_ts_ms", "is_stale", "connected_public", "io_queue_depth"):
    v = d.get(k)
    if isinstance(v, (int, float)) and str(k).endswith("_ms"):
        print("%s  age_s=%.2f" % (k, (now - int(v)) / 1000.0))
    else:
        print("%s  %s" % (k, v))
