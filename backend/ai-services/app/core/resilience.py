"""
Resilience utilities: Circuit Breakers, Rate Limiters, and Exponential Backoff Retries.
Protects external open-data APIs and internal services against cascading failures.
"""
import sys
from pathlib import Path
import asyncio
import time
import random
from typing import Callable, Any, Optional, Dict
from enum import Enum

# Ensure backend/ai-services is in sys.path for standalone execution and IDE resolution
_pkg_root = str(Path(__file__).resolve().parents[2])
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

try:
    from app.observability.logger import logger
    from app.core.security import redact_secrets
except (ImportError, ValueError):
    from ..observability.logger import logger
    from .security import redact_secrets


class CircuitState(str, Enum):
    CLOSED = "CLOSED"      # Normal operation: traffic flows through
    OPEN = "OPEN"          # Failing: fast fail without calling external upstream
    HALF_OPEN = "HALF_OPEN"# Trial state: testing if provider has recovered


class CircuitBreakerOpenException(Exception):
    def __init__(self, provider_name: str, retry_after_seconds: float):
        super().__init__(f"Circuit breaker for provider '{provider_name}' is OPEN. Retry in {retry_after_seconds:.1f}s.")
        self.provider_name = provider_name
        self.retry_after_seconds = retry_after_seconds


class CircuitBreaker:
    """
    In-memory Circuit Breaker to prevent hammering upstream APIs during outages.
    """
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_time_seconds: float = 30.0,
        half_open_success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.half_open_success_threshold = half_open_success_threshold

        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_state_change = time.time()

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            if self.consecutive_successes >= self.half_open_success_threshold:
                self.state = CircuitState.CLOSED
                self.consecutive_failures = 0
                self.consecutive_successes = 0
                self.last_state_change = time.time()
                logger.info(f"Circuit breaker for {self.name} reset to CLOSED.")
        elif self.state == CircuitState.CLOSED:
            self.consecutive_failures = 0

    def record_failure(self):
        self.consecutive_failures += 1
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(f"Circuit breaker for {self.name} tripped back to OPEN after probe failure.")
        elif self.state == CircuitState.CLOSED and self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            logger.warning(
                f"Circuit breaker for {self.name} tripped to OPEN after {self.consecutive_failures} consecutive failures."
            )

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.recovery_time_seconds:
                self.state = CircuitState.HALF_OPEN
                self.consecutive_successes = 0
                self.last_state_change = now
                logger.info(f"Circuit breaker for {self.name} moved to HALF_OPEN (probing upstream).")
                return True
            return False
        # HALF_OPEN
        return True


class RateLimiter:
    """
    Token-bucket rate limiter to enforce API usage policies (e.g. Nominatim 1 req/sec max).
    """
    def __init__(self, requests_per_second: float = 1.0):
        self.rate = requests_per_second
        self.capacity = max(1.0, requests_per_second)
        self.tokens = self.capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_update = time.time()
            else:
                self.tokens -= 1.0


async def retry_with_backoff(
    coroutine_func: Callable[[], Any],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    circuit_breaker: Optional[CircuitBreaker] = None,
    provider_name: str = "ExternalAPI",
) -> Any:
    """
    Executes an async callable with circuit breaker, timeout, and exponential backoff retry.
    """
    if circuit_breaker and not circuit_breaker.can_execute():
        retry_after = max(0.0, circuit_breaker.recovery_time_seconds - (time.time() - circuit_breaker.last_state_change))
        raise CircuitBreakerOpenException(provider_name, retry_after)

    last_exc = None
    delay = initial_delay

    for attempt in range(1, max_attempts + 1):
        try:
            result = await coroutine_func()
            if circuit_breaker:
                circuit_breaker.record_success()
            return result
        except Exception as e:
            last_exc = e
            clean_err = redact_secrets(str(e))
            logger.warning(
                f"[{provider_name}] Attempt {attempt}/{max_attempts} failed: {clean_err}"
            )
            if attempt < max_attempts:
                sleep_duration = delay + (random.uniform(0, 0.5) if jitter else 0)
                await asyncio.sleep(sleep_duration)
                delay *= backoff_factor

    if circuit_breaker:
        circuit_breaker.record_failure()
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"Operation failed for {provider_name} without an explicit exception")
