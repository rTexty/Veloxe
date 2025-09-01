import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

sys.path.append('../../')

from shared.config.settings import settings
from shared.config.database import init_db
from shared.config.redis import init_redis
from handlers import register_handlers
from middlewares import ConsentMiddleware, CrisisMiddleware
from services.admin_settings_service import AdminSettingsService
from services.ping_service import PingService
from services.subscription_reminder_service import SubscriptionReminderService
from services.cryptocloud_polling_service import CryptoCloudPollingService
from services.settings_cache import settings_cache
from shared.config.database import async_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ping_scheduler(bot_instance):
    """Background task for periodic ping checks"""
    ping_service = PingService()
    while True:
        try:
            await ping_service.schedule_ping_check(bot_instance)
        except Exception as e:
            logger.error(f"Error in ping scheduler: {e}")
        
        # Check every 30 minutes
        await asyncio.sleep(1800)

async def subscription_reminder_scheduler(bot_instance):
    """Background task for subscription reminder checks"""
    reminder_service = SubscriptionReminderService()
    while True:
        try:
            await reminder_service.check_and_send_reminders(bot_instance)
        except Exception as e:
            logger.error(f"Error in subscription reminder scheduler: {e}")
        
        # Check every 30 minutes
        await asyncio.sleep(1800)


async def settings_cache_refresh_scheduler():
    """Background scheduler for settings cache refresh"""
    # Initial cache warm-up
    try:
        await settings_cache.get_bot_settings()
        logger.info("Settings cache warmed up")
    except Exception as e:
        logger.error(f"Settings cache warm-up failed: {e}")
    
    while True:
        try:
            await settings_cache.refresh_cache()
            logger.debug("Settings cache refreshed")
        except Exception as e:
            logger.error(f"Settings cache refresh error: {e}")
        
        # Refresh every 2 minutes (cache TTL is 5 minutes)
        await asyncio.sleep(2 * 60)


async def cryptocloud_payment_scheduler(bot_instance):
    """Background task for CryptoCloud payment polling"""
    cryptocloud_service = CryptoCloudPollingService()
    try:
        await cryptocloud_service.poll_cryptocloud_payments(bot_instance)
    except Exception as e:
        logger.error(f"Error in CryptoCloud payment scheduler: {e}")


async def main():
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis
    await init_redis()
    logger.info("Redis initialized")
    
    # Initialize default settings
    async with async_session() as session:
        admin_service = AdminSettingsService(session)
        await admin_service.initialize_default_settings()
    logger.info("Settings initialized")
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Register middlewares
    dp.message.middleware(ConsentMiddleware())
    dp.callback_query.middleware(ConsentMiddleware())
    dp.message.middleware(CrisisMiddleware())
    dp.callback_query.middleware(CrisisMiddleware())
    logger.info("Middlewares registered")
    
    # Register handlers
    register_handlers(dp)
    
    # Start background schedulers
    ping_task = asyncio.create_task(ping_scheduler(bot))
    reminder_task = asyncio.create_task(subscription_reminder_scheduler(bot))
    cryptocloud_task = asyncio.create_task(cryptocloud_payment_scheduler(bot))
    settings_cache_task = asyncio.create_task(settings_cache_refresh_scheduler())
    logger.info("Background schedulers started")
    
    # Start polling
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    finally:
        ping_task.cancel()
        reminder_task.cancel()
        cryptocloud_task.cancel()
        settings_cache_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")