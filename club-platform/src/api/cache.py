import time
from typing import Any, Optional

_cache: dict[str, tuple[Any, float]] = {}
TTL = 120  # 2 minutes


def get(key: str) -> Optional[Any]:
    if key in _cache:
        value, ts = _cache[key]
        if time.time() - ts < TTL:
            return value
        del _cache[key]
    return None


def set(key: str, value: Any) -> None:
    _cache[key] = (value, time.time())
