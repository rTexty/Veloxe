import redis.asyncio as redis
from typing import Optional
import json
from .settings import settings

redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.from_url(
        settings.redis_url,
        decode_responses=True
    )
    
    # Test connection
    try:
        await redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        redis_client = None


async def get_redis() -> Optional[redis.Redis]:
    """Get Redis client instance"""
    return redis_client


class RedisCache:
    """Redis cache helper class"""
    
    def __init__(self):
        self.redis = redis_client
    
    async def set_conversation_cache(self, user_id: int, conversation_data: dict, ttl: int = 3600):
        """Cache conversation data for 1 hour by default"""
        if not self.redis:
            return
        
        key = f"conversation:{user_id}"
        await self.redis.setex(
            key,
            ttl,
            json.dumps(conversation_data, default=str)
        )
    
    async def get_conversation_cache(self, user_id: int) -> Optional[dict]:
        """Get cached conversation data"""
        if not self.redis:
            return None
        
        key = f"conversation:{user_id}"
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def clear_conversation_cache(self, user_id: int):
        """Clear conversation cache"""
        if not self.redis:
            return
        
        key = f"conversation:{user_id}"
        await self.redis.delete(key)
    
    async def set_memory_anchor(self, user_id: int, anchor_id: str, anchor_data: dict, ttl: int = 7776000):  # 90 days
        """Store long-term memory anchor"""
        if not self.redis:
            return
        
        key = f"memory_anchor:{user_id}:{anchor_id}"
        await self.redis.setex(
            key,
            ttl,
            json.dumps(anchor_data, default=str)
        )
    
    async def get_memory_anchors(self, user_id: int) -> dict:
        """Get all memory anchors for user"""
        if not self.redis:
            return {}
        
        pattern = f"memory_anchor:{user_id}:*"
        keys = await self.redis.keys(pattern)
        
        anchors = {}
        for key in keys:
            anchor_id = key.split(':')[-1]
            data = await self.redis.get(key)
            if data:
                anchors[anchor_id] = json.loads(data)
        
        return anchors
    
    async def delete_memory_anchor(self, user_id: int, anchor_id: str):
        """Delete specific memory anchor"""
        if not self.redis:
            return
        
        key = f"memory_anchor:{user_id}:{anchor_id}"
        await self.redis.delete(key)
    
    async def set_user_session(self, user_id: int, session_data: dict, ttl: int = 86400):  # 24 hours
        """Cache user session data"""
        if not self.redis:
            return
        
        key = f"session:{user_id}"
        await self.redis.setex(
            key,
            ttl,
            json.dumps(session_data, default=str)
        )
    
    async def get_user_session(self, user_id: int) -> Optional[dict]:
        """Get user session data"""
        if not self.redis:
            return None
        
        key = f"session:{user_id}"
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None