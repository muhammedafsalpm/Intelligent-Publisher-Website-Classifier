import redis.asyncio as redis
import json
import logging
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger(__name__)

class RedisCache:
    def __init__(self):
        self.client = None
        self._connected = False
    
    async def connect(self):
        """Establish Redis connection"""
        try:
            self.client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5
            )
            await self.client.ping()
            self._connected = True
            logger.info("Redis connected successfully")
        except Exception:
            logger.debug("Redis unavailable — running without cache (no action required)")
            self._connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._connected:
            return None
        
        try:
            data = await self.client.get(f"classify:{key}")
            if data:
                logger.info(f"Cache hit for {key}")
                return json.loads(data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
        
        return None
    
    async def set(self, key: str, value: dict, ttl: int = None):
        """Set value in cache"""
        if not self._connected:
            return
        
        try:
            ttl = ttl or settings.cache_ttl
            await self.client.setex(
                f"classify:{key}",
                ttl,
                json.dumps(value)
            )
            logger.info(f"Cached {key} for {ttl}s")
        except Exception as e:
            logger.error(f"Cache set error: {e}")
    
    async def invalidate(self, key: str):
        """Invalidate cache for a URL"""
        if not self._connected:
            return
        
        try:
            await self.client.delete(f"classify:{key}")
            logger.info(f"Invalidated cache for {key}")
        except Exception as e:
            logger.error(f"Cache invalidate error: {e}")
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

# Global cache instance
cache = RedisCache()
