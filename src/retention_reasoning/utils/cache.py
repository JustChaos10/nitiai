"""Caching utilities for test results, feature stats, and hypothesis results."""

from __future__ import annotations

import hashlib
import json
import pickle
from datetime import timedelta
from typing import Any, Optional

from loguru import logger


class CacheBackend:
    """Base cache backend interface."""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """Simple in-memory cache with TTL support."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[Any, Optional[float]]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None

        value, expires_at = self._cache[key]
        if expires_at is not None:
            import time
            if time.time() > expires_at:
                del self._cache[key]
                return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = None
        if ttl is not None:
            import time
            expires_at = time.time() + ttl

        self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()


class RedisCache(CacheBackend):
    """Redis-backed cache with automatic serialization."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0", **kwargs) -> None:
        try:
            import redis
        except ImportError as exc:
            raise ImportError(
                "redis package required for RedisCache. Install with: pip install redis"
            ) from exc

        self.client = redis.from_url(redis_url, **kwargs)

    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.client.get(key)
            if data is None:
                return None
            return pickle.loads(data)
        except Exception as exc:
            logger.warning(f"Redis get failed for key {key}: {exc}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        try:
            data = pickle.dumps(value)
            if ttl is not None:
                self.client.setex(key, ttl, data)
            else:
                self.client.set(key, data)
        except Exception as exc:
            logger.warning(f"Redis set failed for key {key}: {exc}")

    def delete(self, key: str) -> None:
        try:
            self.client.delete(key)
        except Exception as exc:
            logger.warning(f"Redis delete failed for key {key}: {exc}")

    def clear(self) -> None:
        try:
            self.client.flushdb()
        except Exception as exc:
            logger.warning(f"Redis clear failed: {exc}")


class ReasoningCache:
    """High-level cache for retention reasoning results."""

    # Default TTLs (in seconds)
    FEATURE_STATS_TTL = 86400  # 1 day
    HYPOTHESIS_TEST_TTL = 604800  # 1 week
    CAUSAL_GRAPH_TTL = 604800  # 1 week
    OPPORTUNITY_PATTERN_TTL = 2592000  # 30 days

    def __init__(self, backend: Optional[CacheBackend] = None) -> None:
        self.backend = backend or InMemoryCache()

    @staticmethod
    def _make_key(prefix: str, *args: Any) -> str:
        """Generate cache key from prefix and arguments."""
        # Create deterministic hash from arguments
        arg_str = json.dumps(args, sort_keys=True, default=str)
        arg_hash = hashlib.md5(arg_str.encode()).hexdigest()[:12]
        return f"retention:{prefix}:{arg_hash}"

    def get_feature_stats(self, feature_name: str, cohort_filter: Optional[str] = None) -> Optional[dict]:
        """Get cached feature statistics."""
        key = self._make_key("feature_stats", feature_name, cohort_filter)
        result = self.backend.get(key)
        if result is not None:
            logger.debug(f"Cache HIT: feature_stats for {feature_name}")
        return result

    def set_feature_stats(
        self,
        feature_name: str,
        stats: dict,
        cohort_filter: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache feature statistics."""
        key = self._make_key("feature_stats", feature_name, cohort_filter)
        self.backend.set(key, stats, ttl or self.FEATURE_STATS_TTL)
        logger.debug(f"Cache SET: feature_stats for {feature_name}")

    def get_hypothesis_test(
        self,
        cause: str,
        effect: str,
        method: str,
        confounders: Optional[list[str]] = None,
    ) -> Optional[dict]:
        """Get cached hypothesis test result."""
        key = self._make_key("hypothesis_test", cause, effect, method, confounders or [])
        result = self.backend.get(key)
        if result is not None:
            logger.debug(f"Cache HIT: hypothesis_test {cause} → {effect} ({method})")
        return result

    def set_hypothesis_test(
        self,
        cause: str,
        effect: str,
        method: str,
        test_result: dict,
        confounders: Optional[list[str]] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache hypothesis test result."""
        key = self._make_key("hypothesis_test", cause, effect, method, confounders or [])
        self.backend.set(key, test_result, ttl or self.HYPOTHESIS_TEST_TTL)
        logger.debug(f"Cache SET: hypothesis_test {cause} → {effect} ({method})")

    def get_causal_graph(self, opportunity_id: str) -> Optional[dict]:
        """Get cached causal graph."""
        key = self._make_key("causal_graph", opportunity_id)
        result = self.backend.get(key)
        if result is not None:
            logger.debug(f"Cache HIT: causal_graph for {opportunity_id}")
        return result

    def set_causal_graph(
        self,
        opportunity_id: str,
        graph: dict,
        ttl: Optional[int] = None,
    ) -> None:
        """Cache causal graph."""
        key = self._make_key("causal_graph", opportunity_id)
        self.backend.set(key, graph, ttl or self.CAUSAL_GRAPH_TTL)
        logger.debug(f"Cache SET: causal_graph for {opportunity_id}")

    def get_opportunity_pattern(
        self,
        opportunity_type: str,
        cohort_desc: str,
    ) -> Optional[list[dict]]:
        """Get cached similar opportunity patterns."""
        key = self._make_key("opportunity_pattern", opportunity_type, cohort_desc)
        result = self.backend.get(key)
        if result is not None:
            logger.debug(f"Cache HIT: opportunity_pattern {opportunity_type}")
        return result

    def set_opportunity_pattern(
        self,
        opportunity_type: str,
        cohort_desc: str,
        patterns: list[dict],
        ttl: Optional[int] = None,
    ) -> None:
        """Cache opportunity patterns."""
        key = self._make_key("opportunity_pattern", opportunity_type, cohort_desc)
        self.backend.set(key, patterns, ttl or self.OPPORTUNITY_PATTERN_TTL)
        logger.debug(f"Cache SET: opportunity_pattern {opportunity_type}")

    def clear_all(self) -> None:
        """Clear all cached data."""
        self.backend.clear()
        logger.info("Cache cleared")


# Global cache instance
_default_cache: Optional[ReasoningCache] = None


def get_cache(backend: Optional[CacheBackend] = None) -> ReasoningCache:
    """Get or create default cache instance."""
    global _default_cache
    if _default_cache is None:
        _default_cache = ReasoningCache(backend)
    return _default_cache


def configure_cache(backend: CacheBackend) -> None:
    """Configure global cache backend."""
    global _default_cache
    _default_cache = ReasoningCache(backend)
