# src/core/cache/cache_manager.py
"""Cache management system for Chocolate Factory."""

import time
from typing import Any, Optional, Dict, Callable
from functools import wraps
import hashlib
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    """In-memory cache manager with TTL support."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key in self._cache:
            entry = self._cache[key]
            if entry['expires_at'] > time.time():
                self.hits += 1
                logger.debug(f"Cache hit for key: {key}")
                return entry['value']
            else:
                # Expired, remove from cache
                del self._cache[key]
                self.evictions += 1
                logger.debug(f"Cache expired for key: {key}")
        
        self.misses += 1
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl
        
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
        logger.debug(f"Cached key: {key} with TTL: {ttl}s")
    
    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Deleted cache key: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self.evictions += count
        logger.info(f"Cleared {count} cache entries")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry['expires_at'] <= current_time
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self.evictions += 1
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'entries': len(self._cache),
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': round(hit_rate, 2),
            'total_requests': total_requests
        }
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching a pattern.
        
        Args:
            pattern: Pattern to match (simple substring match)
            
        Returns:
            Number of keys invalidated
        """
        matching_keys = [
            key for key in self._cache.keys()
            if pattern in key
        ]
        
        for key in matching_keys:
            del self._cache[key]
        
        self.evictions += len(matching_keys)
        
        if matching_keys:
            logger.debug(f"Invalidated {len(matching_keys)} keys matching pattern: {pattern}")
        
        return len(matching_keys)


# Global cache instance
cache_manager = CacheManager(default_ttl=300)


def cache_key_wrapper(
    prefix: str,
    ttl: int = 300,
    key_func: Optional[Callable] = None
):
    """
    Decorator for caching function results.
    
    Args:
        prefix: Cache key prefix
        ttl: Time-to-live in seconds
        key_func: Optional function to generate cache key
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = f"{prefix}:{key_func(*args, **kwargs)}"
            else:
                # Default key generation
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                key_hash = hashlib.md5(
                    json.dumps(key_parts, sort_keys=True).encode()
                ).hexdigest()[:8]
                cache_key = f"{prefix}:{key_hash}"
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = f"{prefix}:{key_func(*args, **kwargs)}"
            else:
                # Default key generation
                key_parts = [str(arg) for arg in args]
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
                key_hash = hashlib.md5(
                    json.dumps(key_parts, sort_keys=True).encode()
                ).hexdigest()[:8]
                cache_key = f"{prefix}:{key_hash}"
            
            # Try to get from cache
            cached_value = cache_manager.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class CacheMiddleware:
    """Middleware for cache management and cleanup."""
    
    def __init__(self, cleanup_interval: int = 60):
        """
        Initialize cache middleware.
        
        Args:
            cleanup_interval: Interval for cleanup in seconds
        """
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
    
    async def __call__(self, request, call_next):
        """Process request and perform cache maintenance."""
        # Periodic cleanup
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            cache_manager.cleanup_expired()
            self.last_cleanup = current_time
        
        # Process request
        response = await call_next(request)
        
        # Add cache stats header (for debugging)
        if request.url.path == "/api/cache/stats":
            stats = cache_manager.get_stats()
            response.headers["X-Cache-Hit-Rate"] = str(stats['hit_rate'])
        
        return response