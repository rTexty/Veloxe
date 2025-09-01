from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sys
import json
import redis.asyncio as redis
sys.path.append('../../../')

from shared.models.settings import Settings


class SettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache = {}
        self._redis = None
    
    async def get_setting(self, key: str, default_value=None):
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Query database
        result = await self.session.execute(
            select(Settings).where(Settings.key == key, Settings.is_active == True)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            value = default_value
        elif setting.string_value is not None:
            value = setting.string_value
        elif setting.integer_value is not None:
            value = setting.integer_value
        elif setting.boolean_value is not None:
            value = setting.boolean_value
        elif setting.json_value is not None:
            value = setting.json_value
        else:
            value = default_value
        
        # Cache the value
        self._cache[key] = value
        return value
    
    async def set_setting(self, key: str, value, category: str = "frequent", description: str = None):
        # Try to find existing setting
        result = await self.session.execute(
            select(Settings).where(Settings.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            setting = Settings(key=key, category=category, description=description)
            self.session.add(setting)
        
        # Set the appropriate value field based on type
        if isinstance(value, str):
            setting.string_value = value
        elif isinstance(value, int):
            setting.integer_value = value
        elif isinstance(value, bool):
            setting.boolean_value = value
        else:
            setting.json_value = value
        
        setting.is_active = True
        await self.session.commit()
        
        # Update cache and invalidate globally
        self._cache[key] = value
        await self.invalidate_global_cache(key, value)
    
    async def get_redis(self):
        if not self._redis:
            try:
                self._redis = redis.from_url("redis://localhost:6379", decode_responses=True)
            except:
                self._redis = None
        return self._redis
    
    async def invalidate_global_cache(self, key: str, value):
        try:
            redis_client = await self.get_redis()
            if redis_client:
                await redis_client.publish("settings_update", json.dumps({"key": key, "value": value}))
        except:
            pass
    
    async def invalidate_cache_key(self, key: str):
        if key in self._cache:
            del self._cache[key]
    
    def clear_cache(self):
        self._cache.clear()