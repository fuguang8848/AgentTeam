"""
Simple caching utilities for ClawTeam
"""
import functools
import hashlib
import json
import time
from typing import Any, Callable, Optional


class Cache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, ttl: int = 60):
        """
        Args:
            ttl: Time to live in seconds (default: 60)
        """
        self._cache = {}
        self._ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with TTL"""
        expiry = time.time() + (ttl if ttl is not None else self._ttl)
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """Delete key from cache"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
    
    def cleanup(self) -> int:
        """Remove expired entries, return count of removed items"""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for k in expired:
            del self._cache[k]
        return len(expired)
    
    def size(self) -> int:
        """Get number of cached items"""
        return len(self._cache)


def make_cache_key(*args, **kwargs) -> str:
    """Create a cache key from function arguments"""
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(ttl: int = 60, max_size: int = 128):
    """
    Decorator to cache function results in memory.
    
    Args:
        ttl: Time to live in seconds (default: 60)
        max_size: Maximum number of entries (default: 128)
    
    Example:
        @cached(ttl=120)
        def expensive_function(arg):
            # Result will be cached for 2 minutes
            return compute(arg)
    """
    _cache = Cache(ttl=ttl)
    _max_size = max_size
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Make cache key from function name and arguments
            key = f"{func.__module__}.{func.__name__}:{make_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = _cache.get(key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            _cache.set(key, result)
            
            # Cleanup if cache is too large
            if _cache.size() > _max_size:
                _cache.cleanup()
            
            return result
        return wrapper
    return decorator


def lru_cache(max_size: int = 128):
    """
    Simple LRU (Least Recently Used) cache decorator.
    
    Args:
        max_size: Maximum number of entries (default: 128)
    
    Example:
        @lru_cache(max_size=256)
        def lookup(key):
            return database.get(key)
    """
    _cache = {}
    _access_order = []
    _max_size = max_size
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__module__}.{func.__name__}:{make_cache_key(*args, **kwargs)}"
            
            if key in _cache:
                # Move to end (most recently used)
                _access_order.remove(key)
                _access_order.append(key)
                return _cache[key]
            
            # Call function
            result = func(*args, **kwargs)
            
            # Add to cache
            _cache[key] = result
            _access_order.append(key)
            
            # Evict oldest if over max size
            if len(_cache) > _max_size:
                oldest = _access_order.pop(0)
                del _cache[oldest]
            
            return result
        return wrapper
    return decorator


# Global cache instance for shared use
_global_cache = Cache(ttl=300)  # 5 minutes default


def get_cache() -> Cache:
    """Get the global cache instance"""
    return _global_cache


def clear_global_cache() -> None:
    """Clear the global cache"""
    _global_cache.clear()
