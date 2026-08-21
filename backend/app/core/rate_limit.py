"""In-process rate limiting.

Deliberately dependency-free: a fixed-window counter held in memory, which is
correct for a single Railway instance. The interface is intentionally narrow so
it can be swapped for a Redis-backed limiter when the app is scaled out
horizontally, without touching any call site.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.core.config import settings
from app.core.errors import RateLimited


@dataclass(frozen=True)
class Rule:
    limit: int
    window_seconds: int


#: Endpoint-specific budgets. Auth surfaces are the ones worth protecting.
RULES: dict[str, Rule] = {
    "login": Rule(limit=10, window_seconds=300),
    "register": Rule(limit=5, window_seconds=3600),
    "password_reset": Rule(limit=5, window_seconds=3600),
    "pin_verify": Rule(limit=15, window_seconds=300),
    "phone_otp": Rule(limit=8, window_seconds=600),
    "upload": Rule(limit=60, window_seconds=300),
    "default": Rule(limit=300, window_seconds=60),
}


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def check(self, scope: str, identifier: str) -> None:
        """Raise RateLimited when the caller is over budget for this scope."""
        if not settings.RATE_LIMIT_ENABLED:
            return
        rule = RULES.get(scope, RULES["default"])
        key = f"{scope}:{identifier}"
        now = time.monotonic()

        with self._lock:
            count, window_start = self._hits.get(key, (0, now))
            if now - window_start >= rule.window_seconds:
                count, window_start = 0, now
            count += 1
            self._hits[key] = (count, window_start)
            over = count > rule.limit
            retry_after = int(rule.window_seconds - (now - window_start))

        if over:
            raise RateLimited(
                f"Too many attempts. Please try again in {max(retry_after, 1)} seconds.",
                details={"retry_after": max(retry_after, 1)},
            )

    def reset(self, scope: str, identifier: str) -> None:
        """Clear the counter after a successful attempt."""
        with self._lock:
            self._hits.pop(f"{scope}:{identifier}", None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()
