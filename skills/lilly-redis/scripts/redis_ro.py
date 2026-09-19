"""Read-only Redis. Password never printed."""
from __future__ import annotations

from pathlib import Path
import socket

CONF = Path("/home/dmitry/.bogachka/redis/redis.conf")
HOST = "127.0.0.1"
PORT = 6379


def _password() -> str:
    for line in CONF.read_text().splitlines():
        if line.startswith("requirepass "):
            return line.split(" ", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no redis password")


class RedisRO:
    def __init__(self) -> None:
        self._buf = bytearray()
        self._sock = socket.create_connection((HOST, PORT), 5)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._command("AUTH", _password())
        reply = self._read()
        if reply != "OK":
            raise SystemExit("redis auth failed")

    def get(self, key: str) -> bytes | None:
        self._command("GET", key)
        v = self._read()
        if v is None:
            return None
        if isinstance(v, bytes):
            return v
        raise SystemExit("unexpected GET reply")

    def scan_keys(self, match: str, count: int = 200) -> list[str]:
        cursor = "0"
        out: list[str] = []
        while True:
            self._command("SCAN", cursor, "MATCH", match, "COUNT", str(count))
            reply = self._read()
            if not isinstance(reply, list) or len(reply) != 2:
                raise SystemExit("unexpected SCAN reply")
            cursor_b, keys = reply
            cursor = cursor_b.decode() if isinstance(cursor_b, bytes) else str(cursor_b)
            if not isinstance(keys, list):
                raise SystemExit("unexpected SCAN keys")
            for k in keys:
                if isinstance(k, bytes):
                    out.append(k.decode())
            if cursor == "0":
                return out

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass

    def _command(self, *parts: str) -> None:
        buf = ("*%d\r\n" % len(parts)).encode()
        for p in parts:
            b = p.encode()
            buf += ("$%d\r\n" % len(b)).encode() + b + b"\r\n"
        self._sock.sendall(buf)

    def _read(self):
        line = self._readline()
        if not line:
            raise SystemExit("redis eof")
        t, rest = line[:1], line[1:-2]
        if t == b"+":
            return rest.decode()
        if t == b"-":
            raise SystemExit(rest.decode())
        if t == b":":
            return int(rest)
        if t == b"$":
            n = int(rest)
            if n < 0:
                return None
            return self._read_exact(n)
        if t == b"*":
            n = int(rest)
            if n < 0:
                return None
            return [self._read() for _ in range(n)]
        raise SystemExit("bad redis reply")

    def _readline(self) -> bytes:
        while True:
            i = self._buf.find(b"\r\n")
            if i >= 0:
                line = bytes(self._buf[: i + 2])
                del self._buf[: i + 2]
                return line
            chunk = self._sock.recv(4096)
            if not chunk:
                return b""
            self._buf.extend(chunk)

    def _read_exact(self, n: int) -> bytes:
        need = n + 2
        while len(self._buf) < need:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise SystemExit("redis eof")
            self._buf.extend(chunk)
        body = bytes(self._buf[:n])
        del self._buf[:need]
        return body
