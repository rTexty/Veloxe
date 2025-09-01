"""
CryptoCloud payment polling service
"""
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional
from aiogram import Bot

import sys
sys.path.append('../../../')

from shared.config.database import async_session
from shared.config.settings import settings
from shared.models.subscription import Subscription
from shared.models.user import User
from services.settings_service import SettingsService
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


class CryptoCloudPollingService:
    def __init__(self):
        self.running = False
    
    async def poll_cryptocloud_payments(self, bot: Bot):
        """
        Background task to check pending CryptoCloud payments every 20 seconds
        """
        self.running = True
        logger.info("Started CryptoCloud payment polling")
        
        while self.running:
            try:
                async with async_session() as session:
                    settings_service = SettingsService(session)
                    
                    # Get API credentials
                    api_key = await settings_service.get_setting("cryptocloud_api_key", "")
                    
                    if not api_key:
                        logger.warning("CryptoCloud API key not configured")
                        await asyncio.sleep(60)  # Wait longer if not configured
                        continue
                    
                    # Get pending CryptoCloud subscriptions
                    result = await session.execute(
                        select(Subscription)
                        .where(Subscription.payment_provider == "cryptocloud")
                        .where(Subscription.is_active == False)
                        .where(Subscription.payment_id.isnot(None))
                    )
                    pending_subscriptions = result.scalars().all()
                    
                    logger.debug(f"Checking {len(pending_subscriptions)} pending CryptoCloud payments")
                    
                    for subscription in pending_subscriptions:
                        try:
                            await self._check_payment_status(session, subscription, bot, api_key)
                        except Exception as e:
                            logger.error(f"Error checking payment {subscription.payment_id}: {e}")
                            continue
                
                await asyncio.sleep(20)  # Check every 20 seconds
                
            except Exception as e:
                logger.error(f"Error in CryptoCloud polling: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _check_payment_status(
        self, 
        session, 
        subscription: Subscription, 
        bot: Bot, 
        api_key: str
    ):
        """Check individual payment status"""
        try:
            invoice_id = subscription.payment_id
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.cryptocloud.plus/v2/invoice/merchant/info",
                    headers={"Authorization": f"Token {api_key}"},
                    json={"uuids": [invoice_id]}
                )
                
                data = response.json()
                
                if (
                    data.get("status") == "success"
                    and data.get("result")
                    and isinstance(data["result"], list)
                    and len(data["result"]) > 0
                    and data["result"][0].get("status") in ["paid", "overpaid"]
                ):
                    # Payment successful - activate subscription
                    await self._activate_subscription(session, subscription, bot)
                    logger.info(f"Activated subscription {subscription.id} for payment {invoice_id}")
                    
        except httpx.RequestError as e:
            logger.error(f"Network error checking payment {subscription.payment_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking payment {subscription.payment_id}: {e}")
    
    async def _activate_subscription(
        self, 
        session, 
        subscription: Subscription, 
        bot: Bot
    ):
        """Activate a paid subscription"""
        try:
            # Update subscription to active
            await session.execute(
                update(Subscription)
                .where(Subscription.id == subscription.id)
                .values(
                    is_active=True,
                    starts_at=datetime.utcnow()
                )
            )
            
            # Get user for notification
            user_result = await session.execute(
                select(User).where(User.id == subscription.user_id)
            )
            user = user_result.scalar_one_or_none()
            
            await session.commit()
            
            if user and user.telegram_id:
                # Send success notification
                try:
                    message = "✅ Оплата прошла успешно!\n\nВаша подписка активирована. Теперь у вас безлимитное общение с ботом. Приятного использования! 🎉",
                    
                    await bot.send_message(
                        chat_id=int(user.telegram_id),
                        text=message,
                        parse_mode="HTML"
                    )
                    logger.info(f"Sent payment confirmation to user {user.telegram_id}")
                    
                except Exception as e:
                    logger.warning(f"Could not send notification to user {user.telegram_id}: {e}")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error activating subscription {subscription.id}: {e}")
            raise
    
    def stop_polling(self):
        """Stop the polling loop"""
        self.running = False
        logger.info("Stopped CryptoCloud payment polling")