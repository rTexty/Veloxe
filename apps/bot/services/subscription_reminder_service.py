"""
Subscription expiration reminder service
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List
import sys
import pytz
sys.path.append('../../../')

from shared.config.database import async_session
from shared.models.user import User
from shared.models.subscription import Subscription
from .settings_service import SettingsService
from .user_service import UserService
from utils.ux_helper import UXHelper
from utils.timezone_helper import TimezoneHelper
import logging

logger = logging.getLogger(__name__)


class SubscriptionReminderService:
    def __init__(self):
        self.timezone_helper = TimezoneHelper()
    
    async def check_and_send_reminders(self, bot):
        """Check for users with expiring subscriptions and send reminders"""
        try:
            async with async_session() as session:
                settings_service = SettingsService(session)
                
                # Check if reminders are enabled
                reminders_enabled = await settings_service.get_setting('subscription_reminders_enabled', True)
                if not reminders_enabled:
                    return
                
                # Get users with active subscriptions
                result = await session.execute(
                    select(User, Subscription)
                    .join(Subscription, User.id == Subscription.user_id)
                    .where(Subscription.is_active == True)
                    .where(Subscription.ends_at > datetime.utcnow())
                )
                
                users_with_subscriptions = result.all()
                
                for user, subscription in users_with_subscriptions:
                    await self._process_user_reminder(bot, user, subscription, settings_service)
                    
        except Exception as e:
            logger.error(f"Error in subscription reminder service: {e}")
    
    async def _process_user_reminder(self, bot, user: User, subscription: Subscription, settings_service: SettingsService):
        """Process reminder for a single user"""
        try:
            # Check if user is within allowed notification hours
            if not await self._is_within_allowed_hours(user, settings_service):
                logger.info(f"Skipping reminder for user {user.telegram_id} - outside allowed hours")
                return
            
            now = datetime.utcnow()
            time_until_expiration = subscription.ends_at - now
            
            # 24-hour reminder
            if timedelta(hours=23) <= time_until_expiration <= timedelta(hours=25):
                if not user.last_reminder_24h or (now - user.last_reminder_24h) >= timedelta(hours=20):
                    await self._send_24h_reminder(bot, user, subscription, settings_service)
                    return
            
            # Expiration day reminder
            if timedelta(hours=0) <= time_until_expiration <= timedelta(hours=12):
                if not user.last_reminder_expiry or user.last_reminder_expiry.date() != now.date():
                    await self._send_expiry_reminder(bot, user, subscription, settings_service)
                    return
                    
        except Exception as e:
            logger.error(f"Error processing reminder for user {user.telegram_id}: {e}")
    
    async def _send_24h_reminder(self, bot, user: User, subscription: Subscription, settings_service: SettingsService):
        """Send 24-hour reminder"""
        try:
            # Get reminder template
            template = await settings_service.get_setting(
                'subscription_reminder_24h_template',
                "🔔 {name}, ваша подписка истекает через 24 часа!\n\nХотите продлить для продолжения безлимитного общения?"
            )
            
            # Format template
            reminder_text = template.replace("{name}", user.name or "пользователь")
            reminder_text = reminder_text.replace("{days}", str(subscription.ends_at - datetime.utcnow()).split(",")[0])
            
            # Send reminder with subscription button
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Продлить подписку", callback_data="show_subscription")],
                [InlineKeyboardButton(text="⏰ Напомнить позже", callback_data="remind_later")]
            ])
            
            await UXHelper.smooth_send_message(
                bot,
                user.telegram_id,
                reminder_text,
                reply_markup=keyboard,
                typing_delay=1.0
            )
            
            # Update reminder timestamp
            async with async_session() as session:
                user_service = UserService(session)
                user_obj = await user_service.get_user_by_telegram_id(user.telegram_id)
                if user_obj:
                    user_obj.last_reminder_24h = datetime.utcnow()
                    await session.commit()
            
            # Log reminder event
            async with async_session() as session:
                user_service = UserService(session)
                await user_service.log_event(user.id, "reminder_24h", {
                    'subscription_ends': subscription.ends_at.isoformat(),
                    'plan': subscription.plan_name
                })
            
            logger.info(f"Sent 24h reminder to user {user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error sending 24h reminder to user {user.telegram_id}: {e}")
    
    async def _send_expiry_reminder(self, bot, user: User, subscription: Subscription, settings_service: SettingsService):
        """Send expiration day reminder"""
        try:
            # Get reminder template
            template = await settings_service.get_setting(
                'subscription_reminder_expiry_template',
                "⚠️ {name}, ваша подписка истекает сегодня!\n\nПродлите сейчас, чтобы сохранить безлимитное общение."
            )
            
            # Format template
            reminder_text = template.replace("{name}", user.name or "пользователь")
            hours_left = int((subscription.ends_at - datetime.utcnow()).total_seconds() / 3600)
            reminder_text = reminder_text.replace("{hours_left}", str(max(0, hours_left)))
            
            # Send urgent reminder with subscription button
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚨 Продлить сейчас", callback_data="show_subscription")]
            ])
            
            await UXHelper.smooth_send_message(
                bot,
                user.telegram_id,
                reminder_text,
                reply_markup=keyboard,
                typing_delay=0.8
            )
            
            # Update reminder timestamp
            async with async_session() as session:
                user_service = UserService(session)
                user_obj = await user_service.get_user_by_telegram_id(user.telegram_id)
                if user_obj:
                    user_obj.last_reminder_expiry = datetime.utcnow()
                    await session.commit()
            
            # Log reminder event
            async with async_session() as session:
                user_service = UserService(session)
                await user_service.log_event(user.id, "reminder_expiry", {
                    'subscription_ends': subscription.ends_at.isoformat(),
                    'plan': subscription.plan_name
                })
            
            logger.info(f"Sent expiry reminder to user {user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error sending expiry reminder to user {user.telegram_id}: {e}")
    
    async def _is_within_allowed_hours(self, user: User, settings_service: SettingsService) -> bool:
        """Check if current time is within user's allowed notification hours"""
        try:
            # Get default allowed hours
            default_start = await settings_service.get_setting('allowed_ping_hours_start', 10)
            default_end = await settings_service.get_setting('allowed_ping_hours_end', 22)
            
            # Use user's ping hours if available, otherwise defaults
            hours_start = getattr(user, 'ping_hours_start', default_start) or default_start
            hours_end = getattr(user, 'ping_hours_end', default_end) or default_end
            
            # Get user's timezone
            user_timezone = user.timezone or 'Europe/Moscow'
            
            try:
                tz = pytz.timezone(user_timezone)
            except:
                tz = pytz.timezone('Europe/Moscow')  # Fallback
            
            # Get current time in user's timezone
            now_utc = datetime.now(pytz.UTC)
            now_user_tz = now_utc.astimezone(tz)
            
            current_hour = now_user_tz.hour
            
            # Handle cases where end hour is less than start hour (crosses midnight)
            if hours_end <= hours_start:
                return current_hour >= hours_start or current_hour < hours_end
            else:
                return hours_start <= current_hour < hours_end
                
        except Exception as e:
            logger.error(f"Error checking allowed hours for user {user.telegram_id}: {e}")
            return True  # Default to allowing notifications on error
    
    async def run_reminder_scheduler(self, bot):
        """Run the reminder scheduler continuously"""
        while True:
            try:
                await self.check_and_send_reminders(bot)
                # Check every 30 minutes
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"Error in reminder scheduler: {e}")
                # Wait 5 minutes before retrying on error
                await asyncio.sleep(300)