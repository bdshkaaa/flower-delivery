"""Кэш котировок в памяти с TTL. Без Redis: данных мало, а при перезапуске
нас выручает таблица delivery_quotes."""
import time
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._data: dict[tuple, tuple[float, T]] = {}

    def get(self, key: tuple) -> Optional[T]:
        item = self._data.get(key)
        if item is None:
            return None
        stored_at, value = item
        if self._clock() - stored_at >= self.ttl_seconds:
            del self._data[key]
            return None
        return value

    def set(self, key: tuple, value: T) -> None:
        self._data[key] = (self._clock(), value)
