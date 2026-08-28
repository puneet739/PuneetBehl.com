from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """Fixed-window, in-process rate limiter.

    Deliberately not thread-safe or shared: the site runs as a single worker and
    the limiter only has to blunt a burst, not be exact.
    """

    def __init__(self, max_hits: int, window_seconds: int, *, clock=time.monotonic):
        self.max_hits = max_hits
        self.window = window_seconds
        self.clock = clock
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        now = self.clock()
        cutoff = now - self.window
        hits = [t for t in self._hits[key] if t > cutoff]
        if len(hits) >= self.max_hits:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


def client_key(request, endpoint: str) -> str:
    host = getattr(getattr(request, "client", None), "host", None) or "unknown"
    return f"{host}:{endpoint}"
