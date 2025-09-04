from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import sys
sys.path.append('../../../')

from shared.config.database import async_session
from services.user_service import UserService
from services.settings_service import SettingsService
from utils.ux_helper import UXHelper, OnboardingUX


class ConsentMiddleware(BaseMiddleware):
    """Middleware to ensure user has accepted terms before accessing bot features"""
    
    def __init__(self):
        super().__init__()
        # Commands that are always allowed (even without consent)
        self.allowed_commands = {
            '/start', 
            'consent_accept', 'consent_decline', 
            'show_full_policy', 'back_to_consent'
        }
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Skip middleware for allowed commands
        if isinstance(event, Message):
            if event.text and event.text in self.allowed_commands:
                return await handler(event, data)
        elif isinstance(event, CallbackQuery):
            if event.data in self.allowed_commands:
                return await handler(event, data)
        
        telegram_id = str(event.from_user.id)
        user_name = event.from_user.first_name or "друг"
        
        async with async_session() as session:
            user_service = UserService(session)
            settings_service = SettingsService(session)
            
            # Get user
            user = await user_service.get_or_create_user(telegram_id)
            
            # Check consent status
            current_policy_version = await settings_service.get_setting("policy_version", "v1")
            
            if not user.terms_accepted or user.policy_version != current_policy_version:
                # User hasn't accepted terms - redirect to consent
                consent_text = "🔒 <b>Сначала подтвердите согласие</b>\n\nЧтобы продолжить пользоваться ботом, нужно принять условия использования.\n\n👆 Нажмите /start"
                
                if isinstance(event, Message):
                    await UXHelper.smooth_answer(
                        event,
                        consent_text,
                        typing_delay=0.3
                    )
                elif isinstance(event, CallbackQuery):
                    await UXHelper.smooth_edit_text(
                        event.message,
                        consent_text,
                        typing_delay=0.3
                    )
                
                return  # Block further processing
        
        # User has consent - proceed normally
        return await handler(event, data)