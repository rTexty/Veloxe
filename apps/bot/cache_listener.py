import asyncio
import json
import redis.asyncio as redis
import logging
from services.settings_service import SettingsService

logger = logging.getLogger(__name__)

class CacheInvalidationListener:
    def __init__(self):
        self.redis_client = None
        self.settings_services = []
    
    async def start(self):
        try:
            self.redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
            pubsub = self.redis_client.pubsub()
            await pubsub.subscribe("settings_update")
            
            logger.info("Cache invalidation listener started")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        key = data.get("key")
                        
                        # Invalidate cache in all registered settings services
                        for service in self.settings_services:
                            await service.invalidate_cache_key(key)
                        
                        logger.info(f"Invalidated cache for setting: {key}")
                    except Exception as e:
                        logger.error(f"Error processing cache invalidation: {e}")
        except Exception as e:
            logger.error(f"Cache listener error: {e}")
    
    def register_settings_service(self, service: SettingsService):
        self.settings_services.append(service)
    
    async def stop(self):
        if self.redis_client:
            await self.redis_client.close()

# Global cache listener instance
cache_listener = CacheInvalidationListener()