"""Circuit Breaker: после серии сбоев внешний API на время «отключается»,
чтобы не ждать таймаут на каждый запрос (README, «Отказоустойчивость»)."""
import logging
import time
from typing import Callable

logger = logging.getLogger("app.delivery.breaker")

CLOSED, OPEN, HALF_OPEN = "closed", "open", "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        reset_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at = 0.0
        self._state = CLOSED

    @property
    def state(self) -> str:
        # Open -> Half-open по истечении паузы: пропускаем один пробный запрос
        if self._state == OPEN and self._clock() - self._opened_at >= self.reset_seconds:
            self._state = HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        return self.state != OPEN

    def record_success(self) -> None:
        if self._state != CLOSED:
            logger.info("circuit breaker closed")
        self._failures = 0
        self._state = CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        if self.state == HALF_OPEN or self._failures >= self.failure_threshold:
            if self._state != OPEN:
                logger.warning("circuit breaker opened after %s failures", self._failures)
            self._state = OPEN
            self._opened_at = self._clock()
