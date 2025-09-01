import json
import asyncio
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from shared.config.redis import RedisCache
from shared.models.settings import Settings


class SettingsCache:
    """Cached settings service for fast bot configuration access"""
    
    def __init__(self):
        self.redis = RedisCache()
        self.cache_key = "bot_settings_cache"
        self.cache_ttl = 300  # 5 minutes
        
    async def get_bot_settings(self) -> Dict[str, Any]:
        """Get all bot settings with Redis caching"""
        
        # Try Redis cache first
        try:
            cached_data = await self.redis.get_value(self.cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception:
            pass  # Cache miss or Redis error, continue to DB
        
        # Load from database
        settings = await self._load_from_database()
        
        # Cache the result
        try:
            await self.redis.set_value(
                self.cache_key, 
                json.dumps(settings), 
                ttl=self.cache_ttl
            )
        except Exception:
            pass  # Redis error, but we have the data
            
        return settings
    
    async def _load_from_database(self) -> Dict[str, Any]:
        """Load settings from database with single optimized query"""
        
        setting_keys = [
            'memory_window_size',
            'max_blocks_per_reply', 
            'min_block_length',
            'delay_between_blocks_min',
            'delay_between_blocks_max',
            'long_memory_enabled'
        ]
        
        defaults = {
            'memory_window_size': 11,
            'max_blocks_per_reply': 3,
            'min_block_length': 30,
            'delay_between_blocks_min': 1500,
            'delay_between_blocks_max': 2500,
            'long_memory_enabled': True
        }
        
        try:
            async with async_session() as session:
                # Single batch query instead of 6 separate queries
                result = await session.execute(
                    select(Settings.key, Settings.string_value, Settings.integer_value, Settings.boolean_value)
                    .where(Settings.key.in_(setting_keys))
                )
                
                settings_map = {}
                for row in result:
                    key = row.key
                    # Get the correct value based on type
                    if row.boolean_value is not None:
                        settings_map[key] = row.boolean_value
                    elif row.integer_value is not None:
                        settings_map[key] = row.integer_value
                    elif row.string_value is not None:
                        settings_map[key] = row.string_value
                
                # Merge with defaults for missing keys
                final_settings = {}
                for key, default_value in defaults.items():
                    final_settings[key] = settings_map.get(key, default_value)
                
                return final_settings
                
        except Exception as e:
            print(f"Settings cache DB error: {e}")
            # Return defaults on database error
            return defaults
    
    async def invalidate_cache(self):
        """Invalidate the settings cache (for admin panel integration)"""
        try:
            await self.redis.delete(self.cache_key)
        except Exception:
            pass
    
    async def refresh_cache(self):
        """Force refresh the cache from database"""
        await self.invalidate_cache()
        return await self.get_bot_settings()


# Global instance
settings_cache = SettingsCache()