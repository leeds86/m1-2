from collections import deque
from threading import Lock
from time import monotonic

from app.errors import AppError


class RateLimiter:
    """Single-process sliding window; Render runs one worker."""

    def __init__(self):
        self._entries = {}
        self._lock = Lock()

    def check(self, key, limit):
        now = monotonic()
        with self._lock:
            # Prune idle keys so random client IDs cannot grow memory indefinitely.
            if len(self._entries) > 1000:
                self._entries = {k: q for k, q in self._entries.items() if q and q[-1] > now - 60}
            queue = self._entries.setdefault(key, deque())
            while queue and queue[0] <= now - 60:
                queue.popleft()
            if len(queue) >= limit:
                raise AppError(429, "요청이 많습니다. 1분 후 다시 시도하세요.")
            queue.append(now)
