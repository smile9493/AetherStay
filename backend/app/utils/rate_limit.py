import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """内存版滑动窗口限流器，按 key 独立计数，无需外部依赖（Redis）。"""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        dq = self._hits[key]
        while dq and now - dq[0] >= self.window_seconds:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True