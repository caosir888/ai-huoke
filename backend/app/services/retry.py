"""
Retry logic with exponential backoff for publish failures.
"""
import asyncio
from typing import Callable, Any


async def retry_with_backoff(
    fn: Callable,
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
) -> Any:
    """Execute fn with exponential backoff on failure."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                await asyncio.sleep(delay)
    raise last_error


class PublishRetryManager:
    """Manages publish retry with circuit breaker pattern."""

    def __init__(self):
        self.failure_counts: dict[str, int] = {}  # account_id -> consecutive failures
        self.circuit_open: dict[str, float] = {}  # account_id -> cooldown_until (timestamp)

    def should_retry(self, account_id: str) -> bool:
        """Check if we should retry for this account."""
        import time
        if account_id in self.circuit_open:
            if time.time() < self.circuit_open[account_id]:
                return False
            # Cooldown expired, reset circuit
            del self.circuit_open[account_id]
            self.failure_counts[account_id] = 0
        return True

    def record_success(self, account_id: str):
        self.failure_counts[account_id] = 0

    def record_failure(self, account_id: str):
        import time
        self.failure_counts[account_id] = self.failure_counts.get(account_id, 0) + 1
        if self.failure_counts[account_id] >= 3:
            # Open circuit: pause account for 1 hour
            self.circuit_open[account_id] = time.time() + 3600

    def get_status(self, account_id: str) -> dict:
        import time
        is_open = account_id in self.circuit_open
        remaining = 0
        if is_open:
            remaining = max(0, int(self.circuit_open[account_id] - time.time()))
        return {
            "consecutive_failures": self.failure_counts.get(account_id, 0),
            "circuit_open": is_open,
            "cooldown_remaining_seconds": remaining,
        }
