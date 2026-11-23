import threading
import time
from typing import Any, Callable, Optional


class TTLCache:
    """Thread-safe in-memory TTL cache for read-only catalog data."""

    def __init__(self, default_ttl: int = 300):
        self.default_ttl = default_ttl
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if now >= expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> Any:
        ttl_sec = self.default_ttl if ttl is None else ttl
        expires_at = time.monotonic() + max(1, ttl_sec)
        with self._lock:
            self._store[key] = (expires_at, value)
        return value

    def get_or_set(self, key: str, loader: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = loader()
        return self.set(key, value, ttl=ttl)

    def invalidate(self, key: Optional[str] = None) -> None:
        with self._lock:
            if key is None:
                self._store.clear()
            else:
                self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        with self._lock:
            for k in [k for k in self._store if k.startswith(prefix)]:
                self._store.pop(k, None)


catalog_cache = TTLCache(default_ttl=300)
