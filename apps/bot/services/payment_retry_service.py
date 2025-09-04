"""
Payment retry and failure handling service
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from shared.models.user import User
from shared.models.analytics import Event
from .settings_service import SettingsService
from .user_service import UserService
from utils.ux_helper import UXHelper
import logging

logger = logging.getLogger(__name__)


class PaymentRetryService:
    def __init__(self):
        pass
    
    async def handle_payment_failure(self, telegram_user_id: int, plan_name: str, payment_method: str, error_message: str = None) -> bool:
        """Handle payment failure with retry logic"""
        try:
            async with async_session() as session:
                settings_service = SettingsService(session)
                user_service = UserService(session)
                
                # Get internal user ID
                user = await user_service.get_or_create_user(str(telegram_user_id))
                
                # Get retry settings
                max_attempts = await settings_service.get_setting('payment_retry_attempts', 3)
                
                # Get current attempt count from events
                result = await session.execute(
                    select(Event)
                    .where(Event.user_id == user.id)
                    .where(Event.event_type == 'payment_failed')
                    .where(Event.created_at >= datetime.utcnow() - timedelta(hours=24))
                )
                recent_failures = result.fetchall()
                attempt_count = len(recent_failures) + 1
                
                # Log the failure
                await user_service.log_event(user.id, 'payment_failed', {
                    'plan': plan_name,
                    'method': payment_method,
                    'attempt': attempt_count,
                    'max_attempts': max_attempts,
                    'error': error_message
                })
                
                if attempt_count >= max_attempts:
                    # Max attempts reached - offer support contact
                    await self._send_max_attempts_message(user_id, settings_service)
                    return False
                else:
                    # Send retry suggestions
                    await self._send_retry_message(user_id, plan_name, payment_method, attempt_count, max_attempts, settings_service)
                    return True
                    
        except Exception as e:
            logger.error(f"Error handling payment failure for user {user_id}: {e}")
            return False
    
    async def _send_retry_message(self, user_id: int, plan_name: str, payment_method: str, attempt: int, max_attempts: int, settings_service: SettingsService):
        """Send retry message with alternative payment options"""
        try:
            from aiogram import Bot
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get retry message template
            template = await settings_service.get_setting(
                'payment_retry_template',
                "❌ Оплата не прошла (попытка {attempt} из {max_attempts})\n\nПопробуйте:\n• Другой способ оплаты\n• Проверить данные карты\n• Повторить через несколько минут"
            )
            
            retry_text = template.replace("{attempt}", str(attempt))
            retry_text = retry_text.replace("{max_attempts}", str(max_attempts))
            
            # Create retry buttons
            keyboard_buttons = []
            
            if payment_method == 'cryptocloud':
                keyboard_buttons.append([InlineKeyboardButton(text="⭐ Попробовать Telegram Stars", callback_data=f"pay_stars_{plan_name}")])
                keyboard_buttons.append([InlineKeyboardButton(text="💳 Повторить оплату картой", callback_data=f"pay_card_{plan_name}")])
            elif payment_method == 'stars':
                keyboard_buttons.append([InlineKeyboardButton(text="💳 Попробовать банковскую карту", callback_data=f"pay_card_{plan_name}")])
                keyboard_buttons.append([InlineKeyboardButton(text="⭐ Повторить Telegram Stars", callback_data=f"pay_stars_{plan_name}")])
            
            keyboard_buttons.append([InlineKeyboardButton(text="◀️ К выбору тарифов", callback_data="show_subscription")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            # Send retry message
            bot = Bot.get_current()
            await UXHelper.smooth_send_message(
                bot,
                user_id,
                retry_text,
                reply_markup=keyboard,
                typing_delay=0.3
            )
            
            logger.info(f"Sent retry message to user {user_id}, attempt {attempt}")
            
        except Exception as e:
            logger.error(f"Error sending retry message to user {user_id}: {e}")
    
    async def _send_max_attempts_message(self, user_id: int, settings_service: SettingsService):
        """Send message when max payment attempts reached"""
        try:
            from aiogram import Bot
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            # Get support contact
            support_contact = await settings_service.get_setting('support_contact', '@support')
            
            # Get max attempts message template
            template = await settings_service.get_setting(
                'payment_max_attempts_template',
                "😔 К сожалению, платеж не прошел после нескольких попыток.\n\nДля помощи с оплатой обратитесь в поддержку: {support_contact}\n\nМы поможем решить любые проблемы!"
            )
            
            message_text = template.replace("{support_contact}", support_contact)
            
            # Create support contact button
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{support_contact.replace('@', '')}")],
                [InlineKeyboardButton(text="🔄 Попробовать позже", callback_data="show_subscription")]
            ])
            
            # Send message
            bot = Bot.get_current()
            await UXHelper.smooth_send_message(
                bot,
                user_id,
                message_text,
                reply_markup=keyboard,
                typing_delay=0.4
            )
            
            # Log max attempts reached
            async with async_session() as session:
                user_service = UserService(session)
                await user_service.log_event(user_id, 'payment_max_attempts', {
                    'support_contacted': True
                })
            
            logger.info(f"Sent max attempts message to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending max attempts message to user {user_id}: {e}")
    
    async def reset_payment_attempts(self, telegram_user_id: int):
        """Reset payment attempts for a user (called after successful payment or manual reset)"""
        try:
            async with async_session() as session:
                user_service = UserService(session)
                user = await user_service.get_or_create_user(str(telegram_user_id))
                await user_service.log_event(user.id, 'payment_attempts_reset', {
                    'reset_by': 'system',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            logger.info(f"Reset payment attempts for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error resetting payment attempts for user {user_id}: {e}")
    
    async def get_payment_attempt_count(self, telegram_user_id: int) -> int:
        """Get current payment attempt count for user in last 24 hours"""
        try:
            async with async_session() as session:
                user_service = UserService(session)
                user = await user_service.get_or_create_user(str(telegram_user_id))
                
                result = await session.execute(
                    select(Event)
                    .where(Event.user_id == user.id)
                    .where(Event.event_type == 'payment_failed')
                    .where(Event.created_at >= datetime.utcnow() - timedelta(hours=24))
                )
                failures = result.fetchall()
                return len(failures)
                
        except Exception as e:
            logger.error(f"Error getting payment attempt count for user {user_id}: {e}")
            return 0